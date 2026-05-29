"""
agent/scratch_phase2.py

Phase 2 integration test — runs the full pre_synthesis → synthesis pipeline
on mock NVDA chunks and validates the output against Contract D.

Run: python agent/scratch_phase2.py
Output saved to: mock/nvda_brief_output.json
"""

import json
import time
import sys
import os
from datetime import datetime

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from mock.nvda_chunks import NVDA_CHUNKS
from agent.nodes.pre_synthesis import run_pre_synthesis
from agent.nodes.synthesis import run_synthesis

if __name__ == "__main__":
    REF_DATE = datetime(2024, 11, 10)
    
    pre_result = run_pre_synthesis(NVDA_CHUNKS, reference_date=REF_DATE)
    brief = run_synthesis(pre_result, ticker="NVDA")
    
    assert brief["analyst_sentiment"] == "bullish"
    
    emitted_ids = {s.get("source_id") for s in brief.get("bull_signals", []) + brief.get("bear_signals", []) + brief.get("risk_flags", []) if isinstance(s, dict)}
    
    # User's logic snippet adapted for the object-based schema
    ghost = [
        s["id"] for s in brief.get("sources", []) 
        if s["id"] not in emitted_ids 
        and s["id"] not in [r.get("chunk_a") for r in brief.get("contradictions_resolved", [])]
        and s["id"] not in [r.get("chunk_b") for r in brief.get("contradictions_resolved", [])]
    ]
    assert not ghost, f"Ghost sources (in sources but not in signals): {ghost}"
    
    output_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "mock", "nvda_brief_output.json")
    with open(output_path, "w") as f:
        json.dump(brief, f, indent=2)
