"""
US RS Scanner — Part A (First half of symbols)
Saves results to docs/data_a.json
"""
import yfinance as yf
import pandas as pd
import requests
import json
import io
import os
import time
from datetime import datetime, timedelta

def get_us_symbols():
    print("Fetching US stock list...")
    all_symbols = set()
    try:
        urls = [
            "https://www.nasdaqtrader.com/dynamic/SymDir/nasdaqlisted.txt",
            "https://www.nasdaqtrader.com/dynamic/SymDir/otherlisted.txt",
        ]
        for url in urls:
            r = requests.get(url, timeout=15)
            r.raise_for_status()
            lines = r.text.strip().split("\n")
            is_nasdaq = "nasdaq" in url
            for line in lines[1:]:
                parts = line.split("|")
                if len(parts) < 2:
                    continue
                sym = parts[0].strip()
                if not sym or len(sym) > 5:
                    continue
                if any(c in sym for c in ["^",".","/","$","+"]):
                    continue
                etf_col = 6 if is_nasdaq else 4
                if len(parts) > etf_col and parts[etf_col].strip().upper() == "Y":
                    continue
                all_symbols.add(sym)
        print(f"  Total symbols: {len(all_symbols)}")
    except Exception as e:
        print(f"  NASDAQ fetch failed: {e} — using fallback")
        all_symbols = set([
            "AAPL","MSFT","NVDA","AMZN","GOOGL","META","TSLA","JPM","LLY","V",
            "UNH","XOM","MA","JNJ","PG","HD","AVGO","MRK","COST","ABBV","CVX",
            "CRM","BAC","NFLX","AMD","PEP","KO","TMO","ACN","ADBE","WMT","MCD",
            "ABT","CSCO","LIN","DHR","TXN","NKE","PM","NEE","ORCL","INTC","RTX",
            "UNP","HON","BMY","AMGN","QCOM","LOW","CAT","GS","BA","IBM","SBUX",
            "INTU","SPGI","BLK","AXP","DE","ISRG","ADI","MDLZ","GILD","VRTX",
            "REGN","TJX","SYK","CI","TMUS","AMAT","MMC","ZTS","MO","CB","BDX",
            "EOG","BSX","SO","DUK","ITW","AON","CME","WM","PNC","CL","FCX",
            "PANW","KLAC","LRCX","SNPS","CDNS","ORLY","ADP","CTAS","MNST","FTNT",
            "MELI","CRWD","SNOW","PLTR","UBER","ABNB","NET","DDOG","MDB","COIN",
        ])
    symbols = sorted(list(all_symbols))
    # PART A = first half
    mid = len(symbols) // 2
    part_a = symbols[:mid]
    print(f"  Part A: {len(part_a)} symbols (of {len(symbols)} total)")
    return part_a

def calc_rs(sym, start, end):
    try:
        ticker = yf.Ticker(sym)
        hist   = ticker.history(start=start, end=end, auto_adjust=True)
        if hist.empty or len(hist) < 150:
            return None
        p = hist["Close"].squeeze()
        if len(p) < 63:
            return None
        c_now = float(p.iloc[-1])
        c_3m  = float(p.iloc[-63])
        c_6m  = float(p.iloc[-126]) if len(p) >= 126 else float(p.iloc[0])
        c_9m  = float(p.iloc[-189]) if len(p) >= 189 else float(p.iloc[0])
        c_12m = float(p.iloc[-252]) if len(p) >= 252 else float(p.iloc[0])
        q4 = (c_now - c_3m)  / c_3m
        q3 = (c_3m  - c_6m)  / c_6m
        q2 = (c_6m  - c_9m)  / c_9m
        q1 = (c_9m  - c_12m) / c_12m
        score     = 0.40*q4 + 0.20*q3 + 0.20*q2 + 0.20*q1
        high_52w  = float(p.iloc[-252:].max()) if len(p) >= 252 else float(p.max())
        ret_1m    = round(((c_now - float(p.iloc[-21])) / float(p.iloc[-21]))*100, 1) if len(p) >= 21 else 0
        ret_3m    = round(((c_now - c_3m) / c_3m)*100, 1)
        ret_12m   = round(((c_now - c_12m) / c_12m)*100, 1)
        from_high = round(((c_now - high_52w) / high_52w)*100, 1)
        try:
            info     = ticker.info
            mktcap   = round(info.get("marketCap", 0) / 1e6, 0) if info.get("marketCap") else None
            sector   = info.get("sector",   "N/A")
            industry = info.get("industry", "N/A")
        except Exception:
            mktcap   = None
            sector   = "N/A"
            industry = "N/A"
        return {
            "sym": sym, "score": score, "price": round(c_now, 2),
            "mktcap": mktcap, "sector": sector, "industry": industry,
            "r1m": ret_1m, "r3m": ret_3m, "r12m": ret_12m,
            "h52": round(high_52w, 2), "fh": from_high,
        }
    except Exception:
        return None

def main():
    t0       = time.time()
    date_str = datetime.now().strftime("%d %b %Y")
    print(f"US RS Scan PART A — {date_str}")
    symbols  = get_us_symbols()
    end      = datetime.today()
    start    = end - timedelta(days=420)
    results  = []
    for i, sym in enumerate(symbols):
        if (time.time() - t0) > 4800:
            print(f"  Time limit — stopping at {i}")
            break
        r = calc_rs(sym, start, end)
        if r:
            results.append(r)
        if (i + 1) % 100 == 0:
            elapsed = time.time() - t0
            rem     = (elapsed / (i + 1)) * (len(symbols) - i - 1) / 60
            print(f"  [{i+1}/{len(symbols)}] {len(results)} ok | ~{rem:.0f} min left")
        time.sleep(0.25)
    print(f"\n  Part A complete: {len(results)} stocks")
    os.makedirs("docs", exist_ok=True)
    payload = {
        "updated": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "part":    "A",
        "total":   len(results),
        "stocks":  results,
    }
    with open("docs/data_a.json", "w") as f:
        json.dump(payload, f, separators=(",", ":"))
    print(f"  Saved: docs/data_a.json")
    print(f"  Time: {round((time.time()-t0)/60,1)} min")

if __name__ == "__main__":
    main()
