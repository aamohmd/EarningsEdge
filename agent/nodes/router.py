"""
agent/nodes/router.py

Hits yfinance to get the actual earnings date, computes days remaining,
maps that to a recency mode, and builds the right search query.
"""

import yfinance as yf
from datetime import datetime, timezone, date

def get_next_earnings_date(ticker: str) -> date:
    try:
        ticker_obj = yf.Ticker(ticker)
        calendar = ticker_obj.calendar
        
        if isinstance(calendar, dict):
            earnings_dates = calendar.get('Earnings Date', [])
            if earnings_dates:
                return earnings_dates[0]
        elif calendar is not None and not calendar.empty:
            if 'Earnings Date' in calendar.index:
                dates = calendar.loc['Earnings Date'].values
                if len(dates) > 0:
                    return dates[0].date()
    except Exception:
        pass
        
    return datetime.now(timezone.utc).date()


def run_router(ticker: str, days_to_earnings: int = None) -> dict:
    today = datetime.now(timezone.utc).date()
    if days_to_earnings is None:
        try:
            earnings_date = get_next_earnings_date(ticker)
            days_to_earnings = (earnings_date - today).days
        except Exception:
            days_to_earnings = 14

    if days_to_earnings < 0:
        days_to_earnings = 90 + days_to_earnings

    if days_to_earnings <= 7:
        recency_mode = "aggressive"
        priority = ["news", "transcript", "filings"]
    elif days_to_earnings <= 21:
        recency_mode = "standard"
        priority = ["balanced", "news", "transcript"]
    else:
        recency_mode = "historical"
        priority = ["filings", "news", "transcript"]

    query = f"{ticker} stock earnings news analysis"

    return {
        "ticker": ticker,
        "days_to_earnings": days_to_earnings,
        "recency_mode": recency_mode,
        "source_priority": priority,
        "search_query": query
    }

if __name__ == "__main__":
    for t in ["NVDA", "TSLA", "AMD"]:
        res = run_router(t)
        print(f"{t}: {res['days_to_earnings']} days to earnings -> {res['recency_mode']} mode ({res['source_priority'][0]} priority)")
