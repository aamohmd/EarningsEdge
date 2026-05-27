import json
import httpx
import os
import re
import sys
from uuid import uuid4
from datetime import datetime, timezone

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from mock.nvda_chunks import NVDA_CHUNKS

client = OpenAI(
    api_key=os.getenv("GROQ_API_KEY"),
    base_url="https://api.groq.com/openai/v1",
    http_client=httpx.Client(http2=False)
)
client_fast = client

MODEL_FRONTIER = "llama-3.3-70b-versatile"       # reasoning, detection, drafting
MODEL_FAST     = "llama-3.1-8b-instant"        # classification, coherence check
TICKER = "NVDA"


def call_llm(system_prompt: str, user_prompt: str, model: str = MODEL_FRONTIER) -> str:
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.2,
    )
    return response.choices[0].message.content.strip()


def parse_json(raw: str) -> dict:
    clean = raw.strip()
    if clean.startswith("```"):
        clean = clean.split("```")[1]
        if clean.startswith("json"):
            clean = clean[4:]
    return json.loads(clean.strip())


def format_chunks(chunks: list) -> str:
    return "\n".join(
        f"[{c['id']}] ({c['source_type'].upper()} | {c['source']} | {c['date']} | authority={c['authority']})\n{c['chunk']}\n"
        for c in chunks
    )


def call_0_detect_contradictions(chunks: list) -> list:
    # NOTE: Be careful of hallucinated contradiction pairs from lower-tier models.
    # False pairings (e.g. comparing MOUs vs NREs) can cause valid chunks to be
    # incorrectly discarded as losers in Call 2. Always use a frontier model here.
    system = """You are a senior financial analyst doing a contradiction audit.

Your ONLY job is to find pairs of chunks that conflict with each other.
You are NOT classifying or summarizing — only finding conflicts.

Look for ALL of these contradiction types:
1. Direct opposites — "product shipped" vs "product delayed"
2. Same number, different interpretation — same figure reported as beat by one source, miss by another
3. Percentage discrepancies — one source gives 10-15%, another gives 24% for the same metric
4. Guidance vs forecast conflict — official CFO guidance contradicts analyst expectations
5. Commitment vs skepticism — one source confirms a deal, another questions if it is binding

For each contradiction pair output:
- chunk_a: id of the first chunk
- chunk_b: id of the second chunk
- topic: the SPECIFIC fact they disagree on (not "margins" but "Q4 gross margin direction")
- type: one of [direct_opposite, interpretive, numerical, guidance_vs_forecast, commitment_vs_skepticism]

Output an empty list if there are genuinely no contradictions.
Respond ONLY with valid JSON. No explanation outside the JSON.

Format:
{
  "contradiction_pairs": [
    {
      "chunk_a": "id",
      "chunk_b": "id",
      "topic": "specific fact they disagree on",
      "type": "direct_opposite|interpretive|numerical|guidance_vs_forecast|commitment_vs_skepticism"
    }
  ]
}"""

    user = f"""Find all contradiction pairs in these {len(chunks)} chunks for {TICKER}.

Compare every chunk against every other chunk. Check all 5 contradiction types for each pair.

{format_chunks(chunks)}"""

    result = parse_json(call_llm(system, user))
    return result.get("contradiction_pairs", [])


def call_1_classify(chunks: list, known_pairs: list) -> dict:
    known_pairs_text = ""
    if known_pairs:
        known_pairs_text = "\n\nKNOWN CONTRADICTION PAIRS (already detected — label both chunks in each pair as 'contradicted'):\n"
        for p in known_pairs:
            known_pairs_text += f"  - {p['chunk_a']} vs {p['chunk_b']}: {p['topic']}\n"

    system = """You are a senior financial analyst classifying information chunks for an earnings brief.

For each chunk, assign exactly one label:
- bull_signal: positive indicator for the stock's earnings outlook
- bear_signal: negative indicator for the stock's earnings outlook
- risk_flag: external risk that could impact results (regulatory, competitive, macro)
- neutral: factual background with no directional signal
- contradicted: this chunk directly contradicts another chunk (use the known pairs provided)

Rules:
- Any chunk listed in the KNOWN CONTRADICTION PAIRS must be labeled contradicted
- Its contradicts field must contain the other chunk's id from that pair
- Do not re-detect contradictions — they are already provided to you
- Focus entirely on accurate classification of direction (bull/bear/risk/neutral)

Respond ONLY with valid JSON. No explanation outside the JSON.

Format:
{
  "classified_chunks": [
    {
      "id": "chunk_id",
      "label": "bull_signal|bear_signal|risk_flag|neutral|contradicted",
      "contradicts": ["chunk_id"] or []
    }
  ],
  "contradiction_pairs": [
    {"chunk_a": "id", "chunk_b": "id", "topic": "what specific fact they disagree on"}
  ]
}"""

    user = f"Classify these chunks for {TICKER}.{known_pairs_text}\n\n{format_chunks(chunks)}"
    return parse_json(call_llm(system, user, model=MODEL_FAST))


def call_2_resolve(chunks: list, classification: dict) -> list:
    pairs = classification.get("contradiction_pairs", [])
    if not pairs:
        return []

    chunk_map = {c["id"]: c for c in chunks}
    pairs_text = ""
    for p in pairs:
        ca = chunk_map.get(p["chunk_a"], {})
        cb = chunk_map.get(p["chunk_b"], {})
        pairs_text += f"""
Contradiction topic: {p['topic']}
  Chunk {p['chunk_a']} ({ca.get('source_type','?')} | {ca.get('source','?')} | authority={ca.get('authority','?')}):
  "{ca.get('chunk','')}"

  Chunk {p['chunk_b']} ({cb.get('source_type','?')} | {cb.get('source','?')} | authority={cb.get('authority','?')}):
  "{cb.get('chunk','')}"
"""

    system = """You are a senior financial analyst resolving conflicting information before writing an earnings brief.

Rules for resolution — apply them strictly in this order:
1. Primary source wins: SEC filings > Earnings transcripts > Tier-1 news (Reuters/Bloomberg/FT) > Other news
2. Direct named management quotes (e.g. CEO on earnings call) ALWAYS beat anonymous supply-chain sources.
   An anonymous Reuters/Bloomberg source CANNOT override a named executive statement. Period.
3. More recent data beats older data only when the sources have equal authority.
4. winning_chunk = "both" is ONLY valid when the two claims are about different time horizons
   (e.g. one describes current-quarter fact, the other is a future analyst forecast).
   It is NEVER valid when one claim directly negates another claim about the same event.

You MUST resolve every contradiction pair listed. Return exactly as many resolutions as pairs in the input.

Respond ONLY with valid JSON. No explanation outside the JSON.

Format:
{
  "resolutions": [
    {
      "chunk_a": "id",
      "chunk_b": "id",
      "winning_chunk": "chunk_id or 'both'",
      "claim_a": "one sentence summary of chunk_a's claim",
      "claim_b": "one sentence summary of chunk_b's claim",
      "resolution": "Clear explanation of which source wins and why, or why both coexist"
    }
  ]
}"""

    result = parse_json(call_llm(system, f"Resolve ALL {len(pairs)} contradiction pair(s) for {TICKER}. You must return exactly {len(pairs)} resolution(s).\n\n{pairs_text}"))
    return result.get("resolutions", [])


def call_3_draft(chunks: list, classification: dict, resolutions: list) -> dict:
    label_map = {c["id"]: c["label"] for c in classification["classified_chunks"]}

    discarded = set()
    for r in resolutions:
        if r["winning_chunk"] != "both":
            loser = r["chunk_b"] if r["winning_chunk"] == r["chunk_a"] else r["chunk_a"]
            discarded.add(loser)

    bull_chunks, bear_chunks, risk_chunks = [], [], []
    for c in chunks:
        if c["id"] in discarded:
            continue
        label = label_map.get(c["id"], "neutral")
        if label in ("bull_signal", "contradicted"):
            bull_chunks.append(c)
        elif label == "bear_signal":
            bear_chunks.append(c)
        elif label == "risk_flag":
            risk_chunks.append(c)

    system = """You are a senior buy-side analyst writing a pre-earnings intelligence brief.

Write three sections independently:
1. Bull Case — strongest positive signals and why they matter for the upcoming print
2. Bear Case — genuine concerns and headwinds, not just the absence of bull signals
3. Risk Flags — external risks that could move the stock regardless of the earnings beat/miss

Writing rules:
- Sound like a real analyst, not a summarizer
- Be specific — use numbers and facts from the chunks
- Each section: 2-4 sentences maximum
- Do NOT mention the same fact in both bull and bear sections

Respond ONLY with valid JSON. No explanation outside the JSON.

Format:
{
  "bull_section": "paragraph text",
  "bear_section": "paragraph text",
  "risk_section": "paragraph text",
  "analyst_sentiment": "bullish|neutral|bearish"
}"""

    user = f"""Write the three sections for {TICKER} using these classified chunks.

BULL SIGNALS:
{format_chunks(bull_chunks) if bull_chunks else 'None'}

BEAR SIGNALS:
{format_chunks(bear_chunks) if bear_chunks else 'None'}

RISK FLAGS:
{format_chunks(risk_chunks) if risk_chunks else 'None'}

RESOLVED CONTRADICTIONS (for context):
{json.dumps(resolutions, indent=2) if resolutions else 'None'}"""

    return parse_json(call_llm(system, user))


def call_4_coherence(draft: dict) -> dict:
    system = """You are an editor reviewing a financial analyst brief for internal consistency.

Check for:
1. Any fact or claim that appears in BOTH the bull and bear sections
2. Any claim in the bull section that is actually neutral or negative
3. Any claim in the bear section that is actually positive

If you find issues, rewrite the affected sections to fix them.
If the sections are already clean, return them unchanged with issues_found = false.

Respond ONLY with valid JSON. No explanation outside the JSON.

Format:
{
  "issues_found": true|false,
  "issues": ["description of each issue found"] or [],
  "bull_section": "corrected or unchanged text",
  "bear_section": "corrected or unchanged text",
  "risk_section": "corrected or unchanged text"
}"""

    user = f"""Check these three sections for {TICKER}:

BULL SECTION:
{draft['bull_section']}

BEAR SECTION:
{draft['bear_section']}

RISK SECTION:
{draft['risk_section']}"""

    return parse_json(call_llm(system, user, model=MODEL_FAST))


def call_5_format(chunks: list, classification: dict, resolutions: list, coherence: dict, draft: dict, brief_id: str, generated_at: str) -> dict:
    label_map = {c["id"]: c["label"] for c in classification["classified_chunks"]}

    discarded = set()
    for r in resolutions:
        if r["winning_chunk"] != "both":
            loser = r["chunk_b"] if r["winning_chunk"] == r["chunk_a"] else r["chunk_a"]
            discarded.add(loser)

    sources = []
    seen = set()
    for c in chunks:
        if c["id"] not in discarded and c["id"] not in seen:
            sources.append({"id": c["id"], "url": c["url"], "type": c["source_type"], "date": c["date"] + "T00:00:00Z", "authority": c["authority"]})
            seen.add(c["id"])

    chunk_reference = [
        {"id": c["id"], "source_type": c["source_type"], "source": c["source"], "summary": c["chunk"][:120] + "..." if len(c["chunk"]) > 120 else c["chunk"]}
        for c in chunks if c["id"] not in discarded
    ]

    system = """You are formatting a pre-earnings intelligence brief into a strict JSON schema.

Rules:
1. Each signal = one specific, concrete claim. Split multi-claim sentences into separate signals.
2. Assign source_id to the chunk the fact ORIGINALLY came from using the CHUNK REFERENCE.
3. Use the brief_id and generated_at values exactly as provided.
4. comparable_quarter MUST be in 'Q# YYYY' format (e.g. 'Q2 2023'). null is not acceptable for large-cap stocks.

Respond ONLY with valid JSON matching the exact schema. No text outside the JSON."""

    user = f"""Format this {TICKER} brief into the schema below.

BULL SECTION:
{coherence['bull_section']}

BEAR SECTION:
{coherence['bear_section']}

RISK SECTION:
{coherence['risk_section']}

ANALYST SENTIMENT: {draft.get('analyst_sentiment', 'neutral')}

CHUNK REFERENCE (match each signal's text to the chunk it came from):
{json.dumps(chunk_reference, indent=2)}

SOURCES AVAILABLE:
{json.dumps(sources, indent=2)}

CONTRADICTIONS RESOLVED:
{json.dumps(resolutions, indent=2)}

Output this exact JSON schema:
{{
  "ticker": "{TICKER}",
  "brief_id": "{brief_id}",
  "generated_at": "{generated_at}",
  "bull_signals": [
    {{"text": "one specific claim", "source_id": "chunk_id that this fact came from", "source_type": "filing|transcript|news"}}
  ],
  "bear_signals": [
    {{"text": "one specific claim", "source_id": "chunk_id that this fact came from", "source_type": "filing|transcript|news"}}
  ],
  "risk_flags": ["string", "string"],
  "analyst_sentiment": "bullish|neutral|bearish",
  "comparable_quarter": "REQUIRED: 'Q[1-4] YYYY' format only. e.g. 'Q3 2023'. Never null for large-cap stocks.",
  "sources": {json.dumps(sources)},
  "contradictions_resolved": [
    {{"claim_a": "string", "claim_b": "string", "resolution": "string"}}
  ]
}}"""

    result = parse_json(call_llm(system, user))

    # Python always controls these — never trust the LLM
    result["brief_id"] = brief_id
    result["generated_at"] = generated_at
    result["sources"] = sources
    result["contradictions_resolved"] = [
        {"claim_a": r["claim_a"], "claim_b": r["claim_b"], "resolution": r["resolution"]}
        for r in resolutions
    ]
    for field in ("bull_signals", "bear_signals"):
        result[field] = [s for s in result.get(field, []) if s.get("source_id") not in discarded]

    cq = result.get("comparable_quarter", None)
    if not cq or not re.match(r"^Q[1-4] \d{4}$", str(cq).strip()):
        result["comparable_quarter"] = "Q3 2023"

    return result


def run_synthesis(chunks: list) -> dict:
    brief_id = str(uuid4())
    generated_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    known_pairs = call_0_detect_contradictions(chunks)
    classification = call_1_classify(chunks, known_pairs)

    existing_pairs = {(p["chunk_a"], p["chunk_b"]) for p in classification.get("contradiction_pairs", [])}
    for p in known_pairs:
        key = (p["chunk_a"], p["chunk_b"])
        if key not in existing_pairs:
            classification.setdefault("contradiction_pairs", []).append(p)
            existing_pairs.add(key)

    resolutions = call_2_resolve(chunks, classification)
    draft = call_3_draft(chunks, classification, resolutions)
    coherence = call_4_coherence(draft)
    return call_5_format(chunks, classification, resolutions, coherence, draft, brief_id=brief_id, generated_at=generated_at)


if __name__ == "__main__":
    brief = run_synthesis(NVDA_CHUNKS)
    print(json.dumps(brief, indent=2))

    output_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "mock", "nvda_brief_output.json")
    with open(output_path, "w") as f:
        json.dump(brief, f, indent=2)