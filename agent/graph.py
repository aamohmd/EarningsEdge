"""
agent/graph.py

Full LangGraph pipeline — wires all nodes into a single callable graph.

Pipeline:
    router → web_fetch → pre_synthesis → synthesis → enrich → done

Input:  ticker string e.g. "NVDA"
Output: enriched brief dict (schema [D] + schema [E] merged)

Usage:
    from agent.graph import run_pipeline
    result = await run_pipeline("NVDA")
"""

import asyncio
import logging
from datetime import datetime
from typing import Optional, TypedDict, Annotated
import operator

from langgraph.graph import StateGraph, END

from agent.nodes.router       import run_router
from agent.nodes.web_fetch    import run_web_fetch
from agent.nodes.pre_synthesis import run_pre_synthesis
from agent.nodes.synthesis    import run_synthesis
from intelligence.yfinance    import get_financial_context

try:
    from scenarios_historicalPattern.enricher import enrich as _enrich_real
    ENRICHER_AVAILABLE = True
except ImportError:
    ENRICHER_AVAILABLE = False

logger = logging.getLogger(__name__)



class PipelineState(TypedDict):
    ticker:             str
    days_to_earnings:   Optional[int]

    recency_mode:       str
    source_priority:    list[str]
    search_query:       str

    raw_chunks:         list[dict]
    financial_context:  Optional[dict]

    clean_chunks:       list[dict]
    discarded_chunks:   list[dict]
    analyst_sentiment:  str
    pre_synthesis_stats: dict

    raw_brief:          Optional[dict]
    synthesis_error:    Optional[str]

    enriched_brief:     Optional[dict]
    enrich_error:       Optional[str]

    started_at:         str
    completed_at:       Optional[str]
    elapsed_seconds:    Optional[float]



async def node_router(state: PipelineState) -> PipelineState:
    config = run_router(
        ticker=state["ticker"],
        days_to_earnings=state.get("days_to_earnings"),
    )

    return {
        **state,
        "days_to_earnings": config["days_to_earnings"],
        "recency_mode":     config["recency_mode"],
        "source_priority":  config["source_priority"],
        "search_query":     config["search_query"],
    }



async def node_web_fetch(state: PipelineState) -> PipelineState:
    try:
        chunks_task = run_web_fetch(
            ticker=state["ticker"],
            days_to_earnings=state.get("days_to_earnings", 14),
            recency_mode=state["recency_mode"],
        )
        yfinance_task = asyncio.to_thread(get_financial_context, state["ticker"])
        
        chunks, fin_context = await asyncio.gather(
            chunks_task, yfinance_task,
            return_exceptions=True
        )
        if isinstance(chunks, Exception):
            chunks = []
        if isinstance(fin_context, Exception):
            fin_context = None
    except Exception as e:
        chunks = []
        fin_context = None

    return {
        **state,
        "raw_chunks": chunks,
        "financial_context": fin_context,
    }



async def node_pre_synthesis(state: PipelineState) -> PipelineState:
    result = await asyncio.to_thread(
        run_pre_synthesis,
        state["raw_chunks"]
    )

    return {
        **state,
        "clean_chunks":       result["chunks"],
        "discarded_chunks":   result["discarded"],
        "analyst_sentiment":  result["analyst_sentiment"],
        "pre_synthesis_stats": result["stats"],
    }



async def node_synthesis(state: PipelineState) -> PipelineState:
    if not state["clean_chunks"]:
        return {
            **state,
            "raw_brief":      None,
            "synthesis_error": "no chunks after pre_synthesis",
        }

    try:
        chunks_input = {
            "chunks": state["clean_chunks"],
            "analyst_sentiment": state["analyst_sentiment"]
        }
        
        fin_context_str = ""
        if state.get("financial_context") and state["financial_context"].get("context_string"):
            fin_context_str = state["financial_context"]["context_string"]
            
        raw_brief = await asyncio.to_thread(
            run_synthesis,
            chunks_input,
            state["ticker"],
            financial_context=fin_context_str
        )

        return {
            **state,
            "raw_brief":       raw_brief,
            "synthesis_error": None,
        }

    except Exception as e:
        return {
            **state,
            "raw_brief":       None,
            "synthesis_error": str(e),
        }



def _enrich_stub(raw_brief: dict) -> dict:
    return {
        "scenarios": {
            "bull": {"summary": "Enricher not available", "confidence": 0.0, "drivers": []},
            "base": {"summary": "Enricher not available", "confidence": 0.0, "drivers": []},
            "bear": {"summary": "Enricher not available", "confidence": 0.0, "risks":   []},
        },
        "historical_matches": [],
    }


async def node_enrich(state: PipelineState) -> PipelineState:
    if state.get("raw_brief") is None:
        return {
            **state,
            "enriched_brief": None,
            "enrich_error":   "no raw brief to enrich",
        }

    try:
        enrich_fn = _enrich_real if ENRICHER_AVAILABLE else _enrich_stub

        enriched = await asyncio.to_thread(enrich_fn, state["raw_brief"])

        full_brief = {
            **state["raw_brief"],
            "scenarios":          enriched.get("scenarios", {}),
            "historical_matches": enriched.get("historical_matches", []),
        }

        return {
            **state,
            "enriched_brief": full_brief,
            "enrich_error":   None,
        }

    except Exception as e:
        return {
            **state,
            "enriched_brief": state["raw_brief"],
            "enrich_error":   str(e),
        }



def should_synthesize(state: PipelineState) -> str:
    if not state.get("clean_chunks"):
        return "end"
    return "synthesize"


def should_enrich(state: PipelineState) -> str:
    if state.get("synthesis_error") or state.get("raw_brief") is None:
        return "end"
    return "enrich"



def build_graph() -> StateGraph:
    graph = StateGraph(PipelineState)

    graph.add_node("router",        node_router)
    graph.add_node("web_fetch",     node_web_fetch)
    graph.add_node("pre_synthesis", node_pre_synthesis)
    graph.add_node("synthesis",     node_synthesis)
    graph.add_node("enrich",        node_enrich)

    graph.set_entry_point("router")
    graph.add_edge("router",        "web_fetch")
    graph.add_edge("web_fetch",     "pre_synthesis")

    graph.add_conditional_edges(
        "pre_synthesis",
        should_synthesize,
        {"synthesize": "synthesis", "end": END},
    )

    graph.add_conditional_edges(
        "synthesis",
        should_enrich,
        {"enrich": "enrich", "end": END},
    )

    graph.add_edge("enrich", END)

    return graph.compile()


_compiled_graph = None

def get_graph():
    global _compiled_graph
    if _compiled_graph is None:
        _compiled_graph = build_graph()
    return _compiled_graph



async def run_pipeline(
    ticker: str,
    days_to_earnings: Optional[int] = None,
) -> dict:
    started_at = datetime.utcnow()

    initial_state: PipelineState = {
        "ticker":             ticker.upper(),
        "days_to_earnings":   days_to_earnings,
        "recency_mode":       "standard",
        "source_priority":    ["news", "transcript", "filing"],
        "search_query":       "",
        "raw_chunks":         [],
        "financial_context":  None,
        "clean_chunks":       [],
        "discarded_chunks":   [],
        "analyst_sentiment":  "neutral",
        "pre_synthesis_stats": {},
        "raw_brief":          None,
        "synthesis_error":    None,
        "enriched_brief":     None,
        "enrich_error":       None,
        "started_at":         started_at.isoformat(),
        "completed_at":       None,
        "elapsed_seconds":    None,
    }

    graph = get_graph()
    try:
        final_state = await graph.ainvoke(initial_state)

        completed_at   = datetime.utcnow()
        elapsed        = (completed_at - started_at).total_seconds()

        result = final_state.get("enriched_brief") or final_state.get("raw_brief")

        if result:
            return result
        else:
            return {
                "error": "pipeline produced no output",
                "ticker": ticker,
                "synthesis_error": final_state.get("synthesis_error"),
            }

    except Exception as e:
        return {
            "error": str(e),
            "ticker": ticker,
        }



if __name__ == "__main__":
    import json
    import os
    logging.basicConfig(level=logging.INFO)

    async def test():
        ticker = "NVDA"
        result = await run_pipeline(ticker)

        print("\nFINAL OUTPUT:")
        print(json.dumps(result, indent=2, default=str))

        os.makedirs("mock", exist_ok=True)
        with open(f"mock/{ticker}_pipeline_output.json", "w") as f:
            json.dump(result, f, indent=2, default=str)

        print(f"\n✓ Saved to mock/{ticker}_pipeline_output.json")

    asyncio.run(test())
