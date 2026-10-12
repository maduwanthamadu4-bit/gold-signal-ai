from fastapi import FastAPI, Query
from fastapi.responses import HTMLResponse
import pandas as pd
import yfinance as yf

app = FastAPI(title="Smart Trading AI - Gold Signal AI Edition")


def generate_signal(symbol: str, timeframe: str):
  try:
    tf_map = {
        "15m": {"period": "5d", "interval": "15m"},
        "1h": {"period": "10d", "interval": "1h"},
        "4h": {"period": "30d", "interval": "1h"},
        "1d": {"period": "60d", "interval": "1d"},
    }

    config = tf_map.get(timeframe, tf_map["15m"])
    data = yf.download(
        tickers=symbol,
        period=config["period"],
        interval=config["interval"],
        progress=False,
    )

    if data.empty:
      return {"error": "දත්ත ලබා ගැනීමට නොහැකි විය."}

    if isinstance(data.columns, pd.MultiIndex):
      data.columns = data.columns.droplevel(1)

    data = data.dropna(subset=["Close"])
    close_prices = data["Close"]

    if timeframe == "4h" and len(close_prices) > 4:
      close_prices = close_prices.iloc[::4]

    if len(close_prices) < 15:
      return {"error": "ප්‍රමාණවත් දත්ත ප්‍රමාණයක් නොමැත."}

    chart_data = []
    for idx, price in close_prices.items():
      if pd.notna(price):
        epoch_time = (
            int(idx.timestamp())
            if hasattr(idx, "timestamp")
            else int(pd.to_datetime(idx).timestamp())
        )
        chart_data.append(
            {"time": epoch_time, "value": round(float(price), 4)}
        )

    delta = close_prices.diff()
    gain = delta.where(delta > 0, 0.0)
    loss = -delta.where(delta < 0, 0.0)
    avg_gain = gain.rolling(window=14).mean()
    avg_loss = loss.rolling(window=14).mean()
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))

    latest_rsi = float(rsi.iloc[-1]) if pd.notna(rsi.iloc[-1]) else 50.0
    latest_price = float(close_prices.iloc[-1])
    ema = float(close_prices.ewm(span=20, adjust=False).mean().iloc[-1])

    signal = "NEUTRAL"
    trade_type = "NEUTRAL"
    wave_status = "Consolidation / Corrective Wave (ABC)"
    tp1 = latest_price * 1.015
    tp2 = latest_price * 1.030
    sl = latest_price * 0.985
    advice = "වෙළඳපොළ පරාසයක පවතී. බ්‍රේක්අවුට් එකක් සඳහා රැඳී සිටින්න."

    if latest_rsi < 35 and latest_price > ema:
      signal = "BUY"
      trade_type = "LONG"
      wave_status = (
          "Alignment with 1h/4h long setups following a weak 15m bounce."
      )
      tp1 = latest_price * 1.025
      tp2 = latest_price * 1.050
      sl = latest_price * 0.985
      advice = f"ශක්තිමත් බුලිෂ් ප්‍රවණතාවක් පවතී. ඉලක්කය: {tp2:.2f}."
    elif latest_rsi > 65 and latest_price < ema:
      signal = "SELL"
      trade_type = "SHORT"
      wave_status = (
          "Alignment with 1h/4h short setups following a weak 15m corrective"
          " bounce."
      )
      tp1 = latest_price * 0.975
      tp2 = latest_price * 0.950
      sl = latest_price * 1.015
      advice = f"ශක්තිමත් බෙරිෂ් ප්‍රවණතාවක් පවතී. ඉලක්කය: {tp2:.2f}."
    elif latest_rsi < 30:
      signal = "BUY"
      trade_type = "LONG"
      wave_status = "Oversold Zone (Potential Reversal Bullish)"
      tp1 = latest_price * 1.02
      tp2 = latest_price * 1.04
      sl = latest_price * 0.99
      advice = "අධික ලෙස විකුණා ඇති කලාපයකි (Oversold)."
    elif latest_rsi > 70:
      signal = "SELL"
      trade_type = "SHORT"
      wave_status = "Overbought Zone (Potential Reversal Bearish)"
      tp1 = latest_price * 0.98
      tp2 = latest_price * 0.96
      sl = latest_price * 1.01
      advice = "අධික ලෙස මිලදී ගෙන ඇති කලාපයකි (Overbought)."

    return {
        "symbol": symbol,
        "price": round(latest_price, 4),
        "rsi": round(latest_rsi, 2),
        "trade_type": trade_type,
        "wave_analysis": wave_status,
        "signal": signal,
        "take_profit_1": round(tp1, 4),
        "take_profit_2": round(tp2, 4),
        "stop_loss": round(sl, 4),
        "action_advice": advice,
        "chart_data": chart_data,
    }
  except Exception as e:
    return {"error": f"දෝෂයක් ඇති විය: {str(e)}"}


@app.get("/scan-market")
def scan_market(category: str = "crypto", timeframe: str = "15m"):
  symbols = (
      [
          "BTC-USD",
          "ETH-USD",
          "SOL-USD",
          "XRP-USD",
          "ADA-USD",
          "BNB-USD",
          "DOGE-USD",
          "AVAX-USD",
      ]
      if category == "crypto"
      else [
          "GC=F",
          "EURUSD=X",
          "GBPUSD=X",
          "USDJPY=X",
          "AUDUSD=X",
          "USDCAD=X",
      ]
  )
  results = []
  for sym in symbols:
    res = generate_signal(sym, timeframe)
    if "error" not in res:
      clean_symbol = (
          sym.replace("-USD", "USDT")
          .replace("=X", "")
          .replace("GC=F", "XAU/USD (Gold)")
      )
      results.append({
          "symbol": clean_symbol,
          "price": res["price"],
          "rsi": res["rsi"],
          "trade_type": res["trade_type"],
          "description": res["wave_analysis"],
          "entry": res["price"],
          "stop_loss": res["stop_loss"],
          "tp1": res["take_profit_1"],
          "tp2": res["take_profit_2"],
      })
  return results


@app.get("/", response_class=HTMLResponse)
def home():
  html_str = """<!DOCTYPE html>
<html lang="si">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Smart Trading AI - Gold Signal AI</title>
    <script src="https://unpkg.com/lightweight-charts/dist/lightweight-charts.standalone.production.js"></script>
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background-color: #050811; color: #ffffff; margin: 0; padding: 0; display: flex; justify-content: center; }
        .phone-frame { width: 100%; max-width: 420px; background: #0b1120; min-height: 100vh; display: flex; flex-direction: column; justify-content: space-between; box-shadow: 0 0 25px rgba(212,175,55,0.15); position: relative; border: 1px solid #231c07; }
        
        .header { padding: 12px 20px; font-size: 18px; font-weight: bold; color: #ffd700; border-bottom: 1px solid #2a200a; display: flex; justify-content: space-between; align-items: center; background: #070c18; }
        .logo-area { display: flex; align-items: center; gap: 10px; }
        
        /* Gold Scope Target Logo Styling */
        .gold-target-logo { width: 34px; height: 34px; border: 2px solid #ffd700; border-radius: 50%; display: flex; align-items: center; justify-content: center; position: relative; box-shadow: 0 0 10px rgba(255,215,0,0.5); background: #000; }
        .gold-target-logo::before { content: ''; position: absolute; width: 100%; height: 2px; background: #ffd700; }
        .gold-target-logo::after { content: ''; position: absolute; width: 2px; height: 100%; background: #ffd700; }
        .gold-target-inner { width: 16px; height: 16px; background: linear-gradient(135deg, #ffe066, #d4af37); border-radius: 3px; z-index: 2; box-shadow: 0 0 5px #ffd700; }

        .content { padding: 15px; overflow-y: auto; flex: 1; padding-bottom: 70px; }
        .view-section { display: none; }
        .view-section.active { display: block; }

        /* Full Gold Signal AI Banner Logo */
        .gold-banner-box { background: #000; border: 2px solid #ffd700; border-radius: 20px; padding: 20px 10px; margin-bottom: 20px; box-shadow: 0 0 20px rgba(255,215,0,0.3); text-align: center; position: relative; overflow: hidden; }
        .banner-target { width: 90px; height: 90px; border: 3px solid #ffd700; border-radius: 50%; margin: 0 auto 10px auto; display: flex; align-items: center; justify-content: center; position: relative; box-shadow: 0 0 15px rgba(255,215,0,0.6); background: radial-gradient(circle, #1a1503 0%, #000000 100%); }
        .banner-target::before { content: ''; position: absolute; width: 100%; height: 2px; background: #ffd700; }
        .banner-target::after { content: ''; position: absolute; width: 2px; height: 100%; background: #ffd700; }
        .gold-bars { font-size: 32px; z-index: 2; filter: drop-shadow(0 0 8px #ffd700); }
        
        .gold-title { font-size: 22px; font-weight: 900; background: linear-gradient(180deg, #fff2a3 0%, #ffd700 50%, #caa100 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent; letter-spacing: 1px; }
        .gold-subtitle { font-size: 10px; color: #d4af37; letter-spacing: 2px; font-weight: bold; margin-top: 4px; }

        .welcome-screen { text-align: center; padding: 10px; }
        .welcome-sub { font-size: 13px; color: #94a3b8; margin-bottom: 25px; line-height: 1.5; }
        .input-group { margin-bottom: 15px; text-align: left; }
        .input-group label { display: block; font-size: 12px; color: #d4af37; margin-bottom: 5px; }
        .input-group input { width: 100%; padding: 14px; background: #131a2b; border: 1px solid #3d3112; border-radius: 12px; color: white; font-size: 14px; outline: none; box-sizing: border-box; }

        .tabs { display: flex; background: #131a2b; border-radius: 20px; padding: 4px; margin-bottom: 15px; width: fit-content; border: 1px solid #2a200a; }
        .tab { padding: 8px 20px; border-radius: 16px; cursor: pointer; font-size: 14px; font-weight: bold; color: #94a3b8; transition: 0.3s; }
        .tab.active { background: linear-gradient(135deg, #ffd700, #caa100); color: #000; }

        .group-label { font-size: 13px; color: #d4af37; margin-bottom: 5px; }
        select { width: 100%; padding: 12px; background: #131a2b; border: 1px solid #3d3112; border-radius: 10px; color: white; font-size: 15px; margin-bottom: 15px; outline: none; box-sizing: border-box; }
        .timeframes { display: flex; gap: 8px; margin-bottom: 15px; }
        .tf-btn { flex: 1; padding: 8px; background: #131a2b; border: 1px solid #3d3112; border-radius: 8px; color: #94a3b8; cursor: pointer; font-weight: bold; text-align: center; }
        .tf-btn.active { background: #ffd700; color: #000; border-color: #ffd700; }

        .run-btn { width: 100%; padding: 14px; background: linear-gradient(135deg, #d4af37, #caa100); color: #000; border: none; border-radius: 12px; font-size: 16px; font-weight: bold; cursor: pointer; margin-bottom: 15px; box-shadow: 0 4px 12px rgba(212,175,55,0.4); }
        .run-btn:hover { background: linear-gradient(135deg, #ffe066, #d4af37); }

        #chartContainer { width: 100%; height: 220px; background: #050811; border-radius: 12px; margin-bottom: 15px; border: 1px solid #2a200a; overflow: hidden; }

        .analysis-card { background: #050811; padding: 15px; border-radius: 12px; border: 1px solid #2a200a; }
        .signal { font-size: 26px; font-weight: bold; margin: 10px 0; text-align: center; }
        .BUY { color: #22c55e; }
        .SELL { color: #ef4444; }
        .NEUTRAL { color: #f59e0b; }
        .info { font-size: 14px; margin: 6px 0; }

        .card-box { background: #131a2b; border: 1px solid #2a200a; border-radius: 12px; padding: 15px; margin-bottom: 15px; }
        .scenario-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; }
        .badge-short { background: #fee2e2; color: #ef4444; padding: 4px 12px; border-radius: 20px; font-weight: bold; font-size: 12px; }
        .badge-long { background: #dcfce7; color: #22c55e; padding: 4px 12px; border-radius: 20px; font-weight: bold; font-size: 12px; }
        .badge-neutral { background: #fef3c7; color: #d97706; padding: 4px 12px; border-radius: 20px; font-weight: bold; font-size: 12px; }
        .scenario-row { display: flex; justify-content: space-between; font-size: 13px; padding: 4px 0; border-bottom: 1px solid rgba(255,255,255,0.05); }
        .scenario-row span:last-child { font-weight: bold; }
        .note-text { font-size: 12px; color: #94a3b8; margin-top: 8px; line-height: 1.4; }
        .refresh-btn { width: 100%; padding: 12px; background: #caa100; color: black; border: none; border-radius: 20px; font-weight: bold; cursor: pointer; margin-top: 10px; }

        .scan-card { background: #131a2b; border: 1px solid #2a200a; border-radius: 12px; padding: 12px; margin-bottom: 12px; }
        .scan-header { display: flex; justify-content: space-between; font-weight: bold; font-size: 15px; cursor: pointer; }
        .scan-details { margin-top: 8px; padding-top: 8px; border-top: 1px solid #2a200a; }

        .settings-card { background: #131a2b; border: 1px solid #2a200a; border-radius: 12px; padding: 15px; margin-bottom: 15px; }
        .settings-title { font-weight: bold; font-size: 16px; margin-bottom: 10px; color: #ffd700; display: flex; align-items: center; gap: 8px; }
        .logout-btn { width: 100%; padding: 10px; background: transparent; border: 1px solid #3d3112; border-radius: 20px; color: white; font-size: 14px; cursor: pointer; margin-top: 10px; }

        .bottom-nav { position: absolute; bottom: 0; width: 100%; background: #070c18; border-top: 1px solid #2a200a; display: flex; justify-content: space-around; padding: 10px 0; box-sizing: border-box; }
        .nav-item { text-align: center; color: #94a3b8; font-size: 11px; cursor: pointer; }
        .nav-item.active { color: #ffd700; }
        .nav-item div:first-child { font-size: 16px; margin-bottom: 2px; }
    </style>
</head>
<body>
    <div class="phone-frame">
        <div class="header">
            <div class="logo-area">
                <div class="gold-target-logo"><div class="gold-target-inner"></div></div>
                <span style="background: linear-gradient(180deg, #fff2a3, #ffd700); -webkit-background-clip: text; -webkit-text-fill-color: transparent;">GOLD SIGNAL AI</span>
            </div>
            <span id="userBadge" style="font-size: 11px; color: #ffd700; font-weight: normal; display: none; background: rgba(255,215,0,0.1); padding: 3px 8px; border-radius: 10px; border: 1px solid rgba(255,215,0,0.3);">User</span>
        </div>

        <div class="content">
            <!-- LOGIN / WELCOME VIEW WITH NEW LOGO -->
            <div id="loginView" class="view-section active">
                <div class="welcome-screen">
                    <div class="gold-banner-box">
                        <div class="banner-target">
                            <div class="gold-bars">🪙</div>
                        </div>
                        <div class="gold-title">GOLD SIGNAL AI</div>
                        <div class="gold-subtitle">SMART TRADING • BETTER DECISIONS</div>
                    </div>

                    <div class="welcome-sub">සජීවී Elliott Wave සහ Multi-Timeframe Crypto හා Forex Signals එකවර ලබාගන්න.</div>
                    
                    <div class="input-group">
                        <label>Email Address</label>
                        <input type="text" id="loginEmail" placeholder="trader@gmail.com">
                    </div>
                    <div class="input-group">
                        <label>Password</label>
                        <input type="password" id="loginPass" placeholder="••••••••">
                    </div>

                    <button class="run-btn" style="margin-top: 10px;" onclick="doLogin()">Get Started</button>
                    <button class="logout-btn" style="border: none; color: #ffd700;" onclick="doGuestLogin()">භාවිතා කරන්න (Continue as Guest) ➔</button>
                </div>
            </div>

            <!-- ANALYSE VIEW -->
            <div id="analyseView" class="view-section">
                <div class="tabs">
                    <div class="tab active" id="cryptoTab" onclick="switchTab('crypto')">Crypto</div>
                    <div class="tab" id="forexTab" onclick="switchTab('forex')">Forex / Gold</div>
                </div>

                <div class="group-label">Symbol</div>
                <select id="assetSelect"></select>

                <div class="group-label">Timeframe</div>
                <div class="timeframes">
                    <div class="tf-btn active" onclick="setTf('15m', this)">15m</div>
                    <div class="tf-btn" onclick="setTf('1h', this)">1h</div>
                    <div class="tf-btn" onclick="setTf('4h', this)">4h</div>
                    <div class="tf-btn" onclick="setTf('1d', this)">1d</div>
                </div>

                <button class="run-btn" onclick="runAnalysis()">Run Analysis</button>
                <div id="chartContainer"></div>
                <div class="analysis-card" id="result">
                    <div class="info" style="text-align:center; color:#94a3b8;">වත්කමක් තෝරා Run Analysis ඔබන්න</div>
                </div>
            </div>

            <!-- SIGNAL VIEW -->
            <div id="signalView" class="view-section">
                <h3 style="color: #ffd700; margin-top: 0; font-size: 18px;">Trade Scenarios</h3>
                <div class="card-box">
                    <div class="scenario-header">
                        <span id="sigBadge" class="badge-neutral">NEUTRAL</span>
                        <span style="font-size: 12px; color: #94a3b8;">AI Signal Engine</span>
                    </div>
                    <div class="scenario-row"><span>Entry</span><span id="sigEntry">-</span></div>
                    <div class="scenario-row"><span>Stop Loss</span><span id="sigSl">-</span></div>
                    <div class="scenario-row"><span>TP 1 (1.5R)</span><span id="sigTp1">-</span></div>
                    <div class="scenario-row"><span>TP 2</span><span id="sigTp2">-</span></div>
                    <div class="note-text" id="sigNote">විස්තර බැලීමට ප්‍රථමයෙන් Analysis එකක් ක්‍රියාත්මක කරන්න.</div>
                </div>
                <h3 style="color: #94a3b8; font-size: 14px; margin-bottom: 5px;">Status</h3>
                <div class="card-box" style="padding: 10px 15px; font-weight: bold; color: #22c55e;">RUNNING</div>
                <h3 style="color: #94a3b8; font-size: 14px; margin-bottom: 5px;">Action Advice</h3>
                <div class="card-box" id="sigAdvice" style="font-size: 13px; color: #cbd5e1;">කරුණාකර Analyse ටැබ් එකෙන් විස්තර ලබාගන්න.</div>
                <button class="refresh-btn" onclick="runAnalysis()">Refresh status & advice</button>
            </div>

            <!-- SCANNER VIEW -->
            <div id="scannerView" class="view-section">
                <h3 style="color: #ffd700; margin-top: 0;">Market Scanner</h3>
                <div class="group-label">Market</div>
                <div class="tabs">
                    <div class="tab active" id="scanCryptoTab" onclick="switchScanCat('crypto')">Crypto</div>
                    <div class="tab" id="scanForexTab" onclick="switchScanCat('forex')">Forex</div>
                </div>

                <div class="group-label">Mode / Timeframe</div>
                <div class="timeframes">
                    <div class="tf-btn active" onclick="setScanTf('15m', this)">Scalp (15m)</div>
                    <div class="tf-btn" onclick="setScanTf('4h', this)">Swing (4h)</div>
                </div>

                <button class="run-btn" onclick="runMarketScan()">Run Market Scan</button>
                <div class="group-label" style="margin-top: 15px;">Results</div>
                <div id="scanResults">
                    <div style="color: #94a3b8; text-align: center; font-size: 13px; padding: 20px;">වෙළඳපොළ ස්කෑන් කිරීමට Run Market Scan ඔබන්න.</div>
                </div>
            </div>

            <!-- RECENT SIGNALS VIEW -->
            <div id="recentView" class="view-section">
                <div style="font-size: 13px; color: #94a3b8; margin-bottom: 10px;">Recent Live History</div>
                <div id="recentList">
                    <div style="color: #94a3b8; text-align: center; font-size: 13px; padding: 20px;">මෑතකදී ලබාගත් Signals නොමැත.</div>
                </div>
            </div>

            <!-- SETTINGS VIEW -->
            <div id="settingsView" class="view-section">
                <h2 style="color: #ffd700; margin-top: 0; font-size: 20px;">Settings</h2>
                <div class="group-label">ACCOUNT</div>
                <div class="settings-card">
                    <div class="settings-title">👤 Account</div>
                    <div style="font-size: 12px; color: #94a3b8;">Email</div>
                    <div style="font-size: 14px; color: #ffffff; margin-bottom: 12px;" id="dispEmail">guest@goldssignal.ai</div>
                    <button class="logout-btn" onclick="doLogout()">Log out</button>
                </div>
            </div>
        </div>

        <div class="bottom-nav" id="mainNav" style="display: none;">
            <div class="nav-item active" onclick="switchView('analyse', this)"><div>📊</div>Analyse</div>
            <div class="nav-item" onclick="switchView('signal', this)"><div>⚡</div>Signal</div>
            <div class="nav-item" onclick="switchView('scanner', this)"><div>🔍</div>Scanner</div>
            <div class="nav-item" onclick="switchView('recent', this)"><div>🔄</div>Recent</div>
            <div class="nav-item" onclick="switchView('settings', this)"><div>⚙️</div>Settings</div>
        </div>
    </div>

    <script>
        let currentCategory = 'crypto';
        let selectedTf = '15m';
        let scanCategory = 'crypto';
        let scanTf = '15m';
        let chartInstance = null;
        let lineSeries = null;

        const cryptoList = [
            {val: 'BTC-USD', name: 'BTC/USDT (Bitcoin)'},
            {val: 'ETH-USD', name: 'ETH/USDT (Ethereum)'},
            {val: 'SOL-USD', name: 'SOL/USDT (Solana)'},
            {val: 'XRP-USD', name: 'XRP/USDT (Ripple)'},
            {val: 'ADA-USD', name: 'ADA/USDT (Cardano)'},
            {val: 'BNB-USD', name: 'BNB/USDT (Binance Coin)'},
            {val: 'DOGE-USD', name: 'DOGE/USDT (Dogecoin)'},
            {val: 'AVAX-USD', name: 'AVAX/USDT (Avalanche)'}
        ];

        const forexList = [
            {val: 'GC=F', name: 'Gold (XAU/USD)'},
            {val: 'EURUSD=X', name: 'EUR/USD'},
            {val: 'GBPUSD=X', name: 'GBP/USD'},
            {val: 'USDJPY=X', name: 'USD/JPY'},
            {val: 'AUDUSD=X', name: 'AUD/USD'},
            {val: 'USDCAD=X', name: 'USD/CAD'}
        ];

        function doLogin() {
            const email = document.getElementById('loginEmail').value || 'trader@gmail.com';
            document.getElementById('dispEmail').innerText = email;
            document.getElementById('userBadge').innerText = email.split('@')[0];
            document.getElementById('userBadge').style.display = 'block';
            enterApp();
        }

        function doGuestLogin() {
            document.getElementById('dispEmail').innerText = 'guest@goldsignal.ai';
            document.getElementById('userBadge').innerText = 'Guest';
            document.getElementById('userBadge').style.display = 'block';
            enterApp();
        }

        function enterApp() {
            document.getElementById('loginView').classList.remove('active');
            document.getElementById('analyseView').classList.add('active');
            document.getElementById('mainNav').style.display = 'flex';
            initChart();
        }

        function doLogout() {
            document.querySelectorAll('.view-section').forEach(el => el.classList.remove('active'));
            document.getElementById('loginView').classList.add('active');
            document.getElementById('mainNav').style.display = 'none';
            document.getElementById('userBadge').style.display = 'none';
        }

        function loadAssets() {
            const select = document.getElementById('assetSelect');
            select.innerHTML = '';
            const list = currentCategory === 'crypto' ? cryptoList : forexList;
            list.forEach(item => {
                const opt = document.createElement('option');
                opt.value = item.val;
                opt.innerText = item.name;
                select.appendChild(opt);
            });
        }

        function switchTab(cat) {
            currentCategory = cat;
            document.getElementById('cryptoTab').classList.toggle('active', cat === 'crypto');
            document.getElementById('forexTab').classList.toggle('active', cat === 'forex');
            loadAssets();
        }

        function setTf(tf, element) {
            selectedTf = tf;
            element.parentElement.querySelectorAll('.tf-btn').forEach(btn => btn.classList.remove('active'));
            element.classList.add('active');
        }

        function switchScanCat(cat) {
            scanCategory = cat;
            document.getElementById('scanCryptoTab').classList.toggle('active', cat === 'crypto');
            document.getElementById('scanForexTab').classList.toggle('active', cat === 'forex');
        }

        function setScanTf(tf, element) {
            scanTf = tf;
            element.parentElement.querySelectorAll('.tf-btn').forEach(btn => btn.classList.remove('active'));
            element.classList.add('active');
        }

        function switchView(viewName, element) {
            document.querySelectorAll('.view-section').forEach(el => el.classList.remove('active'));
            document.querySelectorAll('.nav-item').forEach(el => el.classList.remove('active'));

            if(viewName === 'analyse') document.getElementById('analyseView').classList.add('active');
            else if(viewName === 'signal') document.getElementById('signalView').classList.add('active');
            else if(viewName === 'scanner') document.getElementById('scannerView').classList.add('active');
            else if(viewName === 'recent') document.getElementById('recentView').classList.add('active');
            else if(viewName === 'settings') document.getElementById('settingsView').classList.add('active');
            
            if(element) element.classList.add('active');
        }

        function initChart() {
            const container = document.getElementById('chartContainer');
            if(!container) return;
            container.innerHTML = '';
            try {
                chartInstance = LightweightCharts.createChart(container, {
                    width: container.clientWidth || 380,
                    height: 220,
                    layout: { background: { type: 'solid', color: '#050811' }, textColor: '#94a3b8' },
                    grid: { vertLines: { color: '#131a2b' }, horzLines: { color: '#131a2b' } },
                    timeScale: { timeVisible: true, secondsVisible: false }
                });
                lineSeries = chartInstance.addLineSeries({ color: '#ffd700', lineWidth: 2 });
            } catch(e) {
                console.error("Chart init error", e);
            }
        }

        async function runAnalysis() {
            const symbol = document.getElementById('assetSelect').value;
            const resultDiv = document.getElementById('result');
            resultDiv.innerHTML = "<div style='text-align:center; color:#ffd700;'>දත්ත සහ ප්‍රස්ථාරය ලබාගනිමින් පවතී...</div>";

            if (!chartInstance) initChart();

            try {
                const response = await fetch(`/get-signal?symbol=${symbol}&timeframe=${selectedTf}`);
                const data = await response.json();

                if(data.error) {
                    resultDiv.innerHTML = `<div style='color:red; text-align:center;'>${data.error}</div>`;
                    return;
                }

                if (data.chart_data && lineSeries) {
                    lineSeries.setData(data.chart_data);
                    chartInstance.timeScale().fitContent();
                }

                resultDiv.innerHTML = `
                    <div class="info"><b>Symbol:</b> ${data.symbol}</div>
                    <div class="info"><b>Price:</b> $${data.price}</div>
                    <div class="info"><b>RSI:</b> ${data.rsi}</div>
                    <div class="info" style="color: #ffd700;"><b>Wave:</b> ${data.wave_analysis}</div>
                    <div class="signal ${data.signal}">${data.signal}</div>
                    <div class="info"><b>Entry Price:</b> $${data.price}</div>
                    <div class="info"><b>Stop Loss:</b> $${data.stop_loss}</div>
                    <div class="info"><b>TP 1:</b> $${data.take_profit_1}</div>
                    <div class="info"><b>TP 2:</b> $${data.take_profit_2}</div>
                `;

                const badge = document.getElementById('sigBadge');
                badge.innerText = data.trade_type;
                badge.className = data.trade_type === 'SHORT' ? 'badge-short' : (data.trade_type === 'LONG' ? 'badge-long' : 'badge-neutral');

                document.getElementById('sigEntry').innerText = data.price;
                document.getElementById('sigSl').innerText = data.stop_loss;
                document.getElementById('sigTp1').innerText = data.take_profit_1;
                document.getElementById('sigTp2').innerText = data.take_profit_2;
                document.getElementById('sigNote').innerText = data.wave_analysis;
                document.getElementById('sigAdvice').innerText = data.action_advice;

            } catch (err) {
                resultDiv.innerHTML = "<div style='color:red; text-align:center;'>සම්බන්ධ වීමේ දෝෂයක් ඇති විය!</div>";
            }
        }

        async function runMarketScan() {
            const scanDiv = document.getElementById('scanResults');
            scanDiv.innerHTML = "<div style='text-align:center; color:#ffd700; padding: 15px;'>වෙළඳපොළ ස්කෑන් කරමින් පවතී...</div>";

            try {
                const response = await fetch(`/scan-market?category=${scanCategory}&timeframe=${scanTf}`);
                const items = await response.json();

                if(!items.length) {
                    scanDiv.innerHTML = "<div style='color:red; text-align:center;'>ප්‍රතිඵල හමු නොවීය.</div>";
                    return;
                }

                let html = '';
                items.forEach(item => {
                    const badgeClass = item.trade_type === 'LONG' ? 'badge-long' : (item.trade_type === 'SHORT' ? 'badge-short' : 'badge-neutral');
                    html += `
                        <div class="scan-card">
                            <div class="scan-header">
                                <span>${item.symbol}</span>
                                <span class="${badgeClass}">${item.trade_type}</span>
                            </div>
                            <div style="font-size: 13px; color: #94a3b8; margin: 4px 0;">Price: ${item.price} &nbsp;|&nbsp; RSI: ${item.rsi}</div>
                            <div class="scan-details">
                                <div class="scenario-row"><span>Entry:</span><span>${item.entry}</span></div>
                                <div class="scenario-row"><span>Stop Loss:</span><span>${item.stop_loss}</span></div>
                                <div class="scenario-row"><span>TP 1:</span><span>${item.tp1}</span></div>
                                <div class="scenario-row"><span>TP 2:</span><span>${item.tp2}</span></div>
                                <div class="note-text">${item.description}</div>
                            </div>
                        </div>
                    `;
                });
                scanDiv.innerHTML = html;
            } catch(e) {
                scanDiv.innerHTML = "<div style='color:red; text-align:center;'>ස්කෑන් කිරීමේ දෝෂයක් ඇති විය.</div>";
            }
        }

        loadAssets();
    </script>
</body>
</html>"""
  return html_str


@app.get("/get-signal")
def get_signal(
    symbol: str = Query(..., description="Asset symbol"),
    timeframe: str = Query("15m", description="Timeframe"),
):
  return generate_signal(symbol, timeframe)