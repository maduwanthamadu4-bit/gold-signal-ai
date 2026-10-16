from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import yfinance as yf
import pandas as pd
import numpy as np

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

def calculate_indicators(df):
    # 1. RSI (14)
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    df['RSI'] = 100 - (100 / (1 + rs))

    # 2. EMA 50 & EMA 200 (Trend Filters)
    df['EMA_50'] = df['Close'].ewm(span=50, adjust=False).mean()
    df['EMA_200'] = df['Close'].ewm(span=200, adjust=False).mean()

    # 3. MACD
    ema12 = df['Close'].ewm(span=12, adjust=False).mean()
    ema26 = df['Close'].ewm(span=26, adjust=False).mean()
    df['MACD'] = ema12 - ema26
    df['MACD_Signal'] = df['MACD'].ewm(span=9, adjust=False).mean()

    # 4. ATR (Volatility for Dynamic SL/TP)
    high_low = df['High'] - df['Low']
    high_close = np.abs(df['High'] - df['Close'].shift())
    low_close = np.abs(df['Low'] - df['Close'].shift())
    ranges = pd.concat([high_low, high_close, low_close], axis=1)
    true_range = np.max(ranges, axis=1)
    df['ATR'] = true_range.rolling(14).mean()

    return df

@app.get("/analyze")
def analyze_market(symbol: str = "GC=F", interval: str = "15m", balance: float = 1000.0, risk_pct: float = 1.0, leverage: int = 100):
    try:
        data = yf.download(tickers=symbol, period="5d", interval=interval)
        if data.empty:
            return {"error": "No data found"}

        if isinstance(data.columns, pd.MultiIndex):
            data.columns = data.columns.get_level_values(0)

        df = calculate_indicators(data)
        latest = df.iloc[-1]
        
        price = float(latest['Close'])
        rsi = float(latest['RSI'])
        ema_50 = float(latest['EMA_50'])
        ema_200 = float(latest['EMA_200'])
        macd = float(latest['MACD'])
        macd_sig = float(latest['MACD_Signal'])
        atr = float(latest['ATR']) if not np.isnan(latest['ATR']) else price * 0.005

        # Multi-Indicator AI Signal Engine
        signal = "NEUTRAL"
        
        # BUY Condition: Price above EMA200 AND RSI Oversold/Turning UP AND MACD Bullish
        if price > ema_200 and rsi < 45 and macd > macd_sig:
            signal = "STRONG BUY"
        elif price > ema_50 and rsi < 35:
            signal = "BUY"
        # SELL Condition: Price below EMA200 AND RSI Overbought/Turning DOWN AND MACD Bearish
        elif price < ema_200 and rsi > 55 and macd < macd_sig:
            signal = "STRONG SELL"
        elif price < ema_50 and rsi > 65:
            signal = "SELL"

        # Dynamic ATR-based Risk Calculation
        sl_distance = atr * 1.5
        tp1_distance = atr * 2.0
        tp2_distance = atr * 3.5

        if "BUY" in signal:
            sl = price - sl_distance
            tp1 = price + tp1_distance
            tp2 = price + tp2_distance
        elif "SELL" in signal:
            sl = price + sl_distance
            tp1 = price - tp1_distance
            tp2 = price - tp2_distance
        else:
            sl = price - sl_distance
            tp1 = price + tp1_distance
            tp2 = price + tp2_distance

        # Risk & Lot Size Management Calculations
        risk_amount = balance * (risk_pct / 100.0)
        risk_per_point = abs(price - sl)
        
        # Gold Futures Contract Size = 100 oz per lot (Forex Gold XAUUSD = 100)
        lot_size = round(risk_amount / (risk_per_point * 100), 2) if risk_per_point > 0 else 0.01
        if lot_size < 0.01:
            lot_size = 0.01

        required_margin = round((price * lot_size * 100) / leverage, 2)

        return {
            "symbol": symbol,
            "price": round(price, 2),
            "rsi": round(rsi, 2),
            "trend": "BULLISH" if price > ema_200 else "BEARISH",
            "signal": signal,
            "entry": round(price, 2),
            "sl": round(sl, 2),
            "tp1": round(tp1, 2),
            "tp2": round(tp2, 2),
            "risk_management": {
                "balance": balance,
                "risk_amount_usd": round(risk_amount, 2),
                "recommended_lot": lot_size,
                "required_margin": required_margin
            }
        }
    except Exception as e:
        return {"error": str(e)} 
        <!-- Run Analysis Button එක -->
<button onclick="runAnalysis()">Run Analysis</button>


<!-- 💥 මෙන්න මෙතැනට (Button එකට පහළින්) අර Code එක Paste කරන්න 💥 -->
<div style="background: #1e222d; padding: 15px; border-radius: 10px; margin-top: 15px; color: white;">
  <h4 style="color: #f0b90b; margin-bottom: 10px;">🛡️ Risk & Lot Size Calculator</h4>
  
  <div style="display: flex; gap: 10px; margin-bottom: 10px;">
    <div style="flex: 1;">
      <label style="font-size: 12px;">Account Balance ($):</label>
      <input type="number" id="balance" value="1000" style="width: 100%; padding: 8px; background: #2a2e39; color: white; border: 1px solid #444; border-radius: 5px;">
    </div>
    <div style="flex: 1;">
      <label style="font-size: 12px;">Risk (%):</label>
      <select id="risk_pct" style="width: 100%; padding: 8px; background: #2a2e39; color: white; border: 1px solid #444; border-radius: 5px;">
        <option value="1">1% (Safe)</option>
        <option value="2" selected>2% (Moderate)</option>
        <option value="5">5% (High)</option>
      </select>
    </div>
  </div>

  <!-- Output Display -->
  <div style="background: #131722; padding: 10px; border-radius: 5px; font-size: 14px; line-height: 1.6;">
    📊 Recommended Lot Size: <b id="lot_disp" style="color: #00f2fe;">0.01 Lot</b><br>
    💵 Max Risk Amount: <b id="risk_usd_disp" style="color: #ff4a4a;">$20.00</b><br>
    🔒 Required Margin: <b id="margin_disp" style="color: #f0b90b;">$41.50</b>
  </div>
</div>


<!-- Signal Display වෙන කොටස (Symbol, Price, Entry, SL, TP) -->
<div id="signal-results">
   ...
</div>

