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

if __name__ == "__main__":
    import sys
    ticker = sys.argv[1] if len(sys.argv) > 1 else "NVDA"
    result = get_financial_context(ticker)
    print(result["context_string"])
