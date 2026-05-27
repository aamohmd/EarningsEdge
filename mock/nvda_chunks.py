"""
mock/nvda_chunks.py

Simulates what RAG + Web Fetch nodes will return in production.
Stress-test version — includes 5 types of tricky contradictions and edge cases.
"""

NVDA_CHUNKS = [
    # -------------------------------------------------------------------------
    # ORIGINAL CHUNKS (1-8)
    # -------------------------------------------------------------------------

    # --- BULL SIGNALS ---
    {
        "id": "chunk_1",
        "chunk": "NVIDIA data center revenue reached $18.4B this quarter, up 409% year-over-year, driven by surging demand for H100 and A100 GPUs from hyperscalers and cloud providers.",
        "source": "NVIDIA 10-Q Filing",
        "url": "https://sec.gov/nvda-10q-2024",
        "date": "2024-10-15",
        "source_type": "filing",
        "authority": 1.0
    },
    {
        "id": "chunk_2",
        "chunk": "CEO Jensen Huang stated on the earnings call: 'Blackwell is in full production. Demand is staggering — we are sold out for the next 12 months across every configuration.'",
        "source": "NVIDIA Q3 2024 Earnings Transcript",
        "url": "https://seekingalpha.com/nvda-q3-transcript",
        "date": "2024-10-20",
        "source_type": "transcript",
        "authority": 0.95
    },
    {
        "id": "chunk_3",
        "chunk": "Sovereign AI demand is emerging as a new revenue driver, with governments in Japan, India, and the EU committing to build domestic AI infrastructure using NVIDIA hardware.",
        "source": "NVIDIA Q3 2024 Earnings Transcript",
        "url": "https://seekingalpha.com/nvda-q3-transcript",
        "date": "2024-10-20",
        "source_type": "transcript",
        "authority": 0.95
    },

    # --- BEAR SIGNALS ---
    {
        "id": "chunk_4",
        "chunk": "Gross margins declined slightly to 74.1% from 74.6% last quarter due to higher component costs associated with the Blackwell architecture ramp.",
        "source": "NVIDIA Q3 2024 Earnings Transcript",
        "url": "https://seekingalpha.com/nvda-q3-transcript",
        "date": "2024-10-20",
        "source_type": "transcript",
        "authority": 0.95
    },

    # --- CONTRADICTION PAIR 1 (obvious) ---
    # chunk_5 contradicts chunk_2 on Blackwell production status
    {
        "id": "chunk_5",
        "chunk": "Sources close to TSMC indicate that Blackwell chip production has encountered CoWoS packaging bottlenecks, with volume shipments likely delayed by one to two quarters.",
        "source": "Reuters",
        "url": "https://reuters.com/nvda-blackwell-delay",
        "date": "2024-11-01",
        "source_type": "news",
        "authority": 0.70
    },

    # --- CONTRADICTION PAIR 2 (current vs forward-looking) ---
    # chunk_6 contradicts chunk_4 on margin direction
    {
        "id": "chunk_6",
        "chunk": "Several Wall Street analysts raised price targets following NVIDIA's earnings, citing margin expansion potential as Blackwell volumes scale and per-unit production costs fall.",
        "source": "Bloomberg",
        "url": "https://bloomberg.com/nvda-analyst-upgrades",
        "date": "2024-10-22",
        "source_type": "news",
        "authority": 0.80
    },

    # --- RISK FLAGS ---
    {
        "id": "chunk_7",
        "chunk": "The US Department of Commerce is considering further restrictions on AI chip exports to China, which currently accounts for approximately 10-15% of NVIDIA's total revenue.",
        "source": "Financial Times",
        "url": "https://ft.com/nvda-china-export-risk",
        "date": "2024-11-03",
        "source_type": "news",
        "authority": 0.85
    },
    {
        "id": "chunk_8",
        "chunk": "AMD's MI300X GPU is gaining traction with several cloud providers as an alternative to NVIDIA's H100, with Microsoft and Meta confirming expanded MI300X deployments in 2025.",
        "source": "The Information",
        "url": "https://theinformation.com/amd-mi300x-wins",
        "date": "2024-10-28",
        "source_type": "news",
        "authority": 0.75
    },

    # -------------------------------------------------------------------------
    # STRESS TEST CHUNKS (9-14)
    # Five new challenge types — see STRESS_TEST_SCENARIOS below for what each tests
    # -------------------------------------------------------------------------

    # --- STRESS TEST 1: Same number, opposite framing (chunk_9 vs chunk_1) ---
    # Both cite $18.4B data center revenue but draw opposite conclusions from it.
    # Tests: does Call 1 catch a contradiction when the raw fact is identical
    # but the interpretation is opposite? Most LLMs miss this.
    {
        "id": "chunk_9",
        "chunk": "Despite reporting $18.4B in data center revenue, NVIDIA missed the buy-side whisper number of $19.2B, suggesting demand growth is decelerating faster than the headline figure implies.",
        "source": "Goldman Sachs Research Note",
        "url": "https://goldmansachs.com/nvda-note-q3",
        "date": "2024-10-21",
        "source_type": "news",
        "authority": 0.85
    },

    # --- STRESS TEST 2: Stale data that looks current (chunk_10) ---
    # This chunk is 14 months old. It looks like a bear signal but the data
    # is so outdated it should be discarded by recency filters, not used.
    # Tests: does recency weighting prevent old data from polluting the brief?
    {
        "id": "chunk_10",
        "chunk": "NVIDIA gaming segment revenue fell 46% year-over-year in Q3 2023 as consumer GPU demand collapsed post-pandemic, raising questions about the company's ability to sustain growth outside data center.",
        "source": "Wall Street Journal",
        "url": "https://wsj.com/nvda-gaming-decline-2023",
        "date": "2023-08-10",
        "source_type": "news",
        "authority": 0.85
    },

    # --- STRESS TEST 3: Bull signal disguised as neutral language (chunk_11) ---
    # No explicit positive words. Reads like a dry operational update.
    # Tests: does Call 1 classify this as bull_signal or neutral?
    # A good analyst knows "NRE revenue" and design wins are strongly bullish.
    {
        "id": "chunk_11",
        "chunk": "NVIDIA disclosed that non-recurring engineering (NRE) agreements with three unnamed hyperscalers totaling approximately $2.1B were signed this quarter for custom silicon development based on Blackwell derivatives.",
        "source": "NVIDIA Q3 2024 Earnings Transcript",
        "url": "https://seekingalpha.com/nvda-q3-transcript",
        "date": "2024-10-20",
        "source_type": "transcript",
        "authority": 0.95
    },

    # --- STRESS TEST 4: High-authority source saying something negative (chunk_12) ---
    # This is a CFO quote — almost as authoritative as the CEO.
    # It contradicts the bullish sentiment without using obvious bear language.
    # Tests: does the pipeline treat a CFO cautionary statement with appropriate weight?
    {
        "id": "chunk_12",
        "chunk": "CFO Colette Kress noted during the Q&A: 'We expect Q4 gross margins to be in the range of 73.0% to 73.5%, reflecting continued Blackwell ramp costs and a richer mix of systems revenue versus chip-only sales.'",
        "source": "NVIDIA Q3 2024 Earnings Transcript",
        "url": "https://seekingalpha.com/nvda-q3-transcript",
        "date": "2024-10-20",
        "source_type": "transcript",
        "authority": 0.95
    },

    # --- STRESS TEST 5: Subtle contradiction via different % figures (chunk_13 vs chunk_7) ---
    # chunk_7 says China is 10-15% of revenue. chunk_13 says 24%.
    # Both are plausible numbers that have been cited at different points in time.
    # Tests: does Call 1 catch a contradiction when it's just two different numbers,
    # not two opposite claims? This is the hardest type to detect.
    {
        "id": "chunk_13",
        "chunk": "Prior to the October 2023 export restrictions, China represented approximately 24% of NVIDIA's data center revenue. The Commerce Department's new rules are expected to reduce this materially.",
        "source": "Bernstein Research",
        "url": "https://bernstein.com/nvda-china-exposure",
        "date": "2024-10-25",
        "source_type": "news",
        "authority": 0.80
    },

    # --- STRESS TEST 6: Near-duplicate with different conclusion (chunk_14 vs chunk_3) ---
    # Covers the same sovereign AI topic as chunk_3 but draws a skeptical conclusion.
    # Tests: deduplication logic — does pre_synthesis treat these as duplicates
    # (and keep only one) or as a genuine contradiction to resolve?
    {
        "id": "chunk_14",
        "chunk": "While NVIDIA highlighted sovereign AI commitments from Japan, India, and the EU, analysts note these deals are early-stage MOUs rather than binding purchase orders, and actual revenue recognition could be 12-18 months away.",
        "source": "Barclays Equity Research",
        "url": "https://barclays.com/nvda-sovereign-ai-caution",
        "date": "2024-10-23",
        "source_type": "news",
        "authority": 0.80
    },

    {
        "id": "chunk_15",
        "chunk": "NVIDIA's 10-K filing disclosed that total operating expenses increased 44% year-over-year to $4.1B, driven by a 61% surge in R&D spend as the company accelerates Blackwell and next-generation architecture development.",
        "source": "NVIDIA 10-K Annual Filing",
        "url": "https://sec.gov/nvda-10k-2024",
        "date": "2024-10-18",
        "source_type": "filing",
        "authority": 1.0
    },

    {
        "id": "chunk_16",
        "chunk": "NVIDIA's investor relations page updated its Q4 2024 revenue guidance to $37.5B plus or minus 2%, a downward revision from the $38-39B range communicated informally to analysts during the roadshow two weeks prior to earnings.",
        "source": "Bernstein Research — Post-Earnings Note",
        "url": "https://bernstein.com/nvda-guidance-cut-note",
        "date": "2024-10-21",
        "source_type": "news",
        "authority": 0.80
    },
]

# -------------------------------------------------------------------------
# STRESS TEST SCENARIOS
# Reference guide — what each new chunk is testing
# -------------------------------------------------------------------------
STRESS_TEST_SCENARIOS = [
    {
        "id": "ST-1",
        "chunks": ["chunk_1", "chunk_9"],
        "type": "Same fact, opposite interpretation",
        "challenge": "Both cite $18.4B revenue. chunk_9 frames it as a miss vs whisper number.",
        "expected": "Contradiction detected. chunk_1 (10-Q filing, authority 1.0) wins over Goldman note.",
        "what_breaks": "LLM sees same number and assumes agreement, misses interpretive contradiction."
    },
    {
        "id": "ST-2",
        "chunks": ["chunk_10"],
        "type": "Stale data",
        "challenge": "14-month-old gaming decline data. Should be filtered by recency, not synthesized.",
        "expected": "Filtered out by recency.py before reaching synthesis. If it reaches synthesis, label as neutral/outdated.",
        "what_breaks": "Synthesis treats old bear signal as current, weakens the bull case unfairly."
    },
    {
        "id": "ST-3",
        "chunks": ["chunk_11"],
        "type": "Bull signal in neutral language",
        "challenge": "$2.1B NRE agreements — hugely bullish but described in dry operational language.",
        "expected": "Classified as bull_signal. NRE deals signal deep hyperscaler commitment.",
        "what_breaks": "LLM classifies as neutral because there are no positive adjectives."
    },
    {
        "id": "ST-4",
        "chunks": ["chunk_12", "chunk_6"],
        "type": "High-authority bear contradicting analyst bullishness",
        "challenge": "CFO guiding margins to 73-73.5% contradicts analysts expecting margin expansion.",
        "expected": "Contradiction detected. CFO guidance (transcript, 0.95) beats analyst forecast (news, 0.80).",
        "what_breaks": "LLM misses contradiction because one is guidance and one is an opinion."
    },
    {
        "id": "ST-5",
        "chunks": ["chunk_7", "chunk_13"],
        "type": "Numerical contradiction",
        "challenge": "chunk_7 says China = 10-15% revenue. chunk_13 says 24%. Different numbers, same topic.",
        "expected": "Contradiction detected. chunk_13 clarifies these are different time periods — both partially valid.",
        "what_breaks": "LLM treats different numbers as additive info rather than a conflict."
    },
    {
        "id": "ST-6",
        "chunks": ["chunk_3", "chunk_14"],
        "type": "Near-duplicate with skeptical framing",
        "challenge": "Same sovereign AI topic. chunk_14 reframes chunk_3's positive as unrecognized revenue.",
        "expected": "Detected as contradiction (not duplicate). Both survive but with resolution noting MOU vs PO distinction.",
        "what_breaks": "Dedup treats them as the same topic and drops chunk_14, hiding a real bear signal."
    },
    {
        "id": "ST-7",
        "chunks": ["chunk_15"],
        "type": "Filing-sourced bear signal",
        "challenge": "10-K shows 44% opex surge and 61% R&D increase. Bullish (R&D investment) or bearish (cost pressure) depends on framing.",
        "expected": "Classified as bear_signal or neutral — NOT bull_signal. High R&D is an investment but it's not a revenue signal.",
        "what_breaks": "LLM over-rotates to bull framing because R&D sounds like innovation."
    },
    {
        "id": "ST-8",
        "chunks": ["chunk_2", "chunk_16"],
        "type": "Guidance reversal",
        "challenge": "chunk_2 is bullish (sold out 12 months). chunk_16 reports a quiet downward guidance revision. Contradiction on forward outlook.",
        "expected": "Contradiction detected. chunk_2 (transcript, 0.95) wins over second-hand analyst note (0.80) but both must appear.",
        "what_breaks": "LLM misses contradiction because one is production status and one is revenue guidance — different topics on the surface."
    },
]

# Original known contradictions (kept for reference)
KNOWN_CONTRADICTIONS = [
    {
        "chunk_a": "chunk_2",
        "chunk_b": "chunk_5",
        "topic": "Blackwell production status",
        "expected_resolution": "chunk_2 wins — CEO direct quote outranks anonymous supply chain source"
    },
    {
        "chunk_a": "chunk_4",
        "chunk_b": "chunk_6",
        "topic": "Gross margin direction",
        "expected_resolution": "Both coexist — chunk_4 is current-quarter fact, chunk_6 is forward-looking analyst forecast"
    },
    {
        "chunk_a": "chunk_1",
        "chunk_b": "chunk_9",
        "topic": "Revenue beat vs whisper miss",
        "expected_resolution": "chunk_1 wins — 10-Q filing beats Goldman research note; same number, filing is authoritative"
    },
    {
        "chunk_a": "chunk_12",
        "chunk_b": "chunk_6",
        "topic": "Q4 gross margin direction",
        "expected_resolution": "chunk_12 wins — CFO official guidance beats analyst forecast"
    },
    {
        "chunk_a": "chunk_7",
        "chunk_b": "chunk_13",
        "topic": "China revenue exposure percentage",
        "expected_resolution": "Both coexist — different time periods (pre vs post export restrictions)"
    },
    {
        "chunk_a": "chunk_3",
        "chunk_b": "chunk_14",
        "topic": "Sovereign AI revenue certainty",
        "expected_resolution": "Both coexist — chunk_3 reports commitments, chunk_14 flags MOUs are not binding POs"
    },
    {
        "chunk_a": "chunk_2",
        "chunk_b": "chunk_16",
        "topic": "Forward revenue outlook",
        "expected_resolution": "chunk_2 wins on production status; chunk_16 adds guidance cut context — both relevant"
    },
]