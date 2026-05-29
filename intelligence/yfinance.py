"""
intelligence/yfinance.py

Fetches quantitative financial context for a ticker using yfinance.
Returns a formatted string to be injected into the LLM context.
"""
import sys
if sys.path[0].endswith('intelligence'):
    _removed = sys.path.pop(0)
import yfinance as yf
if '_removed' in locals():
    sys.path.insert(0, _removed)

def format_large_number(num):
    if num is None: return "N/A"
    try:
        num = float(num)
    except:
        return num
    if num >= 1e12: return f"${num/1e12:.2f}T"
    if num >= 1e9: return f"${num/1e9:.2f}B"
    if num >= 1e6: return f"${num/1e6:.2f}M"
    return f"${num:,.2f}"

def get_financial_context(ticker: str) -> dict:
    try:
        t = yf.Ticker(ticker)
        info = t.info
        
        current_price = info.get("currentPrice") or info.get("regularMarketPrice") or "N/A"
        fifty_two_low = info.get("fiftyTwoWeekLow", "N/A")
        fifty_two_high = info.get("fiftyTwoWeekHigh", "N/A")
        market_cap = format_large_number(info.get("marketCap"))
        
        forward_pe = info.get("forwardPE", "N/A")
        if forward_pe != "N/A": forward_pe = f"{forward_pe:.1f}x"
        
        peg_ratio = info.get("pegRatio", "N/A")
        price_to_sales = info.get("priceToSalesTrailing12Months", "N/A")
        if price_to_sales != "N/A": price_to_sales = f"{price_to_sales:.1f}x"
        
        target_mean = info.get("targetMeanPrice", "N/A")
        target_low = info.get("targetLowPrice", "N/A")
        target_high = info.get("targetHighPrice", "N/A")
        recommendation = str(info.get("recommendationKey", "N/A")).upper()
        num_analysts = info.get("numberOfAnalystOpinions", "N/A")
        
        short_percent = info.get("shortPercentOfFloat", "N/A")
        if short_percent != "N/A": short_percent = f"{short_percent * 100:.1f}%"
        short_ratio = info.get("shortRatio", "N/A")
        
        # Estimates
        try:
            earn_est = t.earnings_estimate.iloc[0]
            eps_avg = f"${earn_est['avg']:.2f}"
            eps_low = f"${earn_est['low']:.2f}"
            eps_high = f"${earn_est['high']:.2f}"
            eps_analysts = int(earn_est['numberOfAnalysts'])
        except:
            eps_avg, eps_low, eps_high, eps_analysts = "N/A", "N/A", "N/A", "N/A"
            
        try:
            rev_est = t.revenue_estimate.iloc[0]
            rev_avg = format_large_number(rev_est['avg'])
            rev_growth = f"{rev_est['growth'] * 100:.1f}%" if rev_est.get('growth') else "N/A"
        except:
            rev_avg, rev_growth = "N/A", "N/A"

        context_str = f"=== QUANTITATIVE CONTEXT: {ticker} ===\n"
        context_str += f"Current Price: ${current_price} | 52W Range: ${fifty_two_low} - ${fifty_two_high} | Market Cap: {market_cap}\n"
        context_str += f"Consensus EPS Estimate (next Q): {eps_avg} (range: {eps_low}-{eps_high}) | {eps_analysts} analysts\n"
        context_str += f"Consensus Revenue Estimate (next Q): {rev_avg} | YoY growth est: {rev_growth}\n"
        context_str += f"Forward P/E: {forward_pe} | PEG: {peg_ratio} | P/S: {price_to_sales}\n"
        context_str += f"Analyst Price Target: ${target_mean} (${target_low}-${target_high}) | Consensus: {recommendation} | {num_analysts} analysts\n"
        
        # History
        try:
            hist = t.earnings_history
            context_str += "Earnings Surprise History (last 4Q):\n"
            for date, row in hist.tail(4).iterrows():
                dt_str = date.strftime("%Y-%m-%d") if hasattr(date, 'strftime') else str(date)
                eps = row.get("epsActual", "N/A")
                est = row.get("epsEstimate", "N/A")
                surp = row.get("surprisePercent", "N/A")
                if surp != "N/A": surp = f"{surp * 100:+.1f}%"
                context_str += f"  {dt_str}: EPS ${eps} vs est ${est} ({surp} surprise)\n"
        except:
            pass

        context_str += f"Short Interest: {short_percent} of float | Short Ratio: {short_ratio} days\n"
        context_str += "========================================"
        
        return {
            "ticker": ticker,
            "context_string": context_str
        }
    except Exception as e:
        return {
            "ticker": ticker,
            "context_string": f"=== QUANTITATIVE CONTEXT: {ticker} ===\nError fetching financial data: {e}\n========================================"
        }

def get_yfinance_chunks(ticker: str) -> list[dict]:
    """
    Converts key yfinance metrics into pre-labeled chunks.
    These bypass Call 1 classification — already labeled bull/bear/risk.
    Authority 0.90 — analyst consensus data, highly reliable.
    """
    from datetime import date
    today = date.today().strftime("%Y-%m-%d")

    data = get_financial_context(ticker)
    if not data.get("context_string") or "Error fetching" in data.get("context_string", ""):
        return []

    chunks = []
    try:
        t = yf.Ticker(ticker)
        info = t.info
    except:
        return []

    # EPS estimate
    try:
        earn_est = t.earnings_estimate.iloc[0]
        eps_avg = earn_est['avg']
        eps_low = earn_est['low']
        eps_high = earn_est['high']
        eps_analysts = int(earn_est['numberOfAnalysts'])
        chunks.append({
            "id": f"yf_eps_{ticker}",
            "chunk": f"Analyst consensus EPS estimate for {ticker} next quarter: ${eps_avg:.2f} (range ${eps_low:.2f}-${eps_high:.2f}) from {eps_analysts} analysts.",
            "source": "yfinance/analyst consensus",
            "url": f"https://finance.yahoo.com/quote/{ticker}",
            "date": today,
            "source_type": "filing",
            "authority": 0.90,
            "pre_label": "bull_signal",
        })
    except:
        pass

    # Revenue estimate
    try:
        rev_est = t.revenue_estimate.iloc[0]
        rev_avg = format_large_number(rev_est['avg'])
        rev_growth = f"{rev_est['growth'] * 100:.1f}%" if rev_est.get('growth') else "N/A"
        chunks.append({
            "id": f"yf_rev_{ticker}",
            "chunk": f"Consensus revenue estimate for {ticker} next quarter: {rev_avg} representing {rev_growth} YoY growth.",
            "source": "yfinance/analyst consensus",
            "url": f"https://finance.yahoo.com/quote/{ticker}",
            "date": today,
            "source_type": "filing",
            "authority": 0.90,
            "pre_label": "bull_signal",
        })
    except:
        pass

    # Valuation
    forward_pe = info.get("forwardPE")
    peg = info.get("pegRatio")
    if forward_pe and peg:
        label = "bull_signal" if peg < 1.0 else "neutral"
        chunks.append({
            "id": f"yf_val_{ticker}",
            "chunk": f"{ticker} trades at {forward_pe:.1f}x forward P/E with a PEG ratio of {peg:.2f} — {'undervalued relative to growth rate' if peg < 1.0 else 'fairly valued'}.",
            "source": "yfinance/valuation",
            "url": f"https://finance.yahoo.com/quote/{ticker}",
            "date": today,
            "source_type": "filing",
            "authority": 0.90,
            "pre_label": label,
        })

    # Price target
    pt_mean = info.get("targetMeanPrice")
    rec = info.get("recommendationKey")
    analysts = info.get("numberOfAnalystOpinions")
    current_price = info.get("currentPrice") or info.get("regularMarketPrice")
    if pt_mean and current_price:
        upside = ((pt_mean / current_price) - 1) * 100
        chunks.append({
            "id": f"yf_pt_{ticker}",
            "chunk": f"Analyst consensus price target for {ticker}: ${pt_mean:.2f} ({upside:+.1f}% upside) — consensus {str(rec).upper()} from {analysts} analysts.",
            "source": "yfinance/price targets",
            "url": f"https://finance.yahoo.com/quote/{ticker}",
            "date": today,
            "source_type": "filing",
            "authority": 0.90,
            "pre_label": "bull_signal" if upside > 10 else "neutral",
        })

    # Short interest
    short_pct = info.get("shortPercentOfFloat")
    if short_pct is not None:
        short_num = short_pct * 100
        label = "bull_signal" if short_num < 5 else ("bear_signal" if short_num > 20 else "neutral")
        chunks.append({
            "id": f"yf_si_{ticker}",
            "chunk": f"{ticker} short interest is {short_num:.1f}% of float — {'minimal bearish positioning, limited downside pressure' if short_num < 5 else 'elevated short interest'}.",
            "source": "yfinance/short interest",
            "url": f"https://finance.yahoo.com/quote/{ticker}",
            "date": today,
            "source_type": "filing",
            "authority": 0.90,
            "pre_label": label,
        })

    # Earnings beat streak
    try:
        hist = t.earnings_history
        if hist is not None and not hist.empty:
            surprises = [row.get("surprisePercent", 0) * 100 for _, row in hist.tail(4).iterrows() if row.get("surprisePercent") is not None]
            if len(surprises) >= 3 and all(s > 0 for s in surprises):
                trend = "accelerating" if surprises[-1] > surprises[-2] > surprises[-3] else "consistent"
                surp_strs = [f"{s:+.1f}%" for s in surprises[-3:]]
                chunks.append({
                    "id": f"yf_beats_{ticker}",
                    "chunk": f"{ticker} has beaten EPS estimates for {len(surprises)} consecutive quarters with {trend} positive surprises: {', '.join(surp_strs)}.",
                    "source": "yfinance/earnings history",
                    "url": f"https://finance.yahoo.com/quote/{ticker}",
                    "date": today,
                    "source_type": "filing",
                    "authority": 0.90,
                    "pre_label": "bull_signal",
                })
    except:
        pass

    return chunks

if __name__ == "__main__":
    import sys
    ticker = sys.argv[1] if len(sys.argv) > 1 else "NVDA"
    result = get_financial_context(ticker)
    print(result["context_string"])
