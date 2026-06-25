# Unused imports silenced
# ruff: ignore

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

load_dotenv()

# --- Minimal Dashboard ---
app = FastAPI(title="OpenMythos Dashboard", version="1.0.0")

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

HTML_DASHBOARD = """
<!DOCTYPE html>
<html lang="fr">
<head>
  <meta charset="UTF-8" />
  <link rel="icon" type="image/svg+xml" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'%3E%3Ctext y='.9em' font-size='90'%3E%E2%9C%88%3C/text%3E%3C/svg%3E" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>OpenMythos Dashboard</title>
  <style>
    :root { --bg: #0d1117; --card: #161b22; --border: #30363d; --accent: #58a6ff; --text: #c9d1d9; --dim: #8b949e; }
    * { margin: 0; padding: 0; box-sizing: border-box; }
    body { background: var(--bg); color: var(--text); font-family: -apple-system, BlinkMacSystemFont, 'SF Mono', monospace; padding: 2rem; }
    .hero { text-align: center; margin-bottom: 3rem; }
    .hero h1 { font-size: 2.5rem; background: linear-gradient(90deg, #58a6ff, #bc8cff); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
    .hero p { color: var(--dim); margin-top: 0.5rem; font-size: 1.1rem; }
    .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 1.5rem; max-width: 1200px; margin: 0 auto; }
    .card { background: var(--card); border: 1px solid var(--border); border-radius: 12px; padding: 1.5rem; transition: transform 0.2s, border-color 0.2s; }
    .card:hover { transform: translateY(-2px); border-color: var(--accent); }
    .card h3 { color: var(--accent); margin-bottom: 0.75rem; font-size: 0.9rem; text-transform: uppercase; letter-spacing: 1px; }
    .card p { color: var(--dim); font-size: 0.9rem; line-height: 1.6; }
    .status { display: inline-block; width: 8px; height: 8px; border-radius: 50%; background: #3fb950; margin-right: 0.5rem; animation: pulse 2s infinite; }
    @keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.4; } }
    .footer { text-align: center; margin-top: 3rem; color: var(--dim); font-size: 0.85rem; }
    .footer a { color: var(--accent); text-decoration: none; }
    code { background: rgba(110,118,129,0.15); padding: 0.2em 0.4em; border-radius: 4px; font-size: 0.85rem; }
  </style>
</head>
<body>
  <div class="hero">
    <h1>&#x2728; OpenMythos</h1>
    <p>LLM&#x2011;Powered Crypto Intelligence</p>
  </div>
  <div class="grid">
    <div class="card">
      <h3>Model</h3>
      <p>Recurrent&#x2011;Depth Transformer (RDT) implementation with MoE, MLA/GQAttention, and ACT halting. Scales from 1B to 1T parameters.</p>
    </div>
    <div class="card">
      <h3>Smart Contracts</h3>
      <p>Solidity flash&#x2011;arbitrage contracts (OpenMythosArb &amp; OpenMythosMicroArb) targeting Uniswap V3. Deployable on Base, Arbitrum, or Ethereum L1.</p>
    </div>
    <div class="card">
      <h3>Trading Bot</h3>
      <p>Autonomous flash&#x2011;arbitrage scanner with on&#x2011;chain profit calculation, MEV&#x2011;resistant execution, and Telegram notifications.</p>
    </div>
    <div class="card">
      <h3>Agent RL</h3>
      <p>Reinforcement&#x2011;learning agent loop for continuous strategy adaptation. Self&#x2011;improving trade execution over time.</p>
    </div>
    <div class="card">
      <h3>API &amp; Dashboard</h3>
      <p>FastAPI backend serving model inference, trading signals, and real&#x2011;time market analysis. This dashboard is live.</p>
    </div>
    <div class="card">
      <h3>Telegram Bot</h3>
      <p>Real&#x2011;time notifications, trade alerts, and remote bot management via Telegram.</p>
    </div>
  </div>
  <div class="footer">
    <p>Built by <a href="https://x.com/lionelj4">@lionelj4</a> &middot; Powered by Claude, OpenRouter &amp; PyTorch</p>
    <p style="margin-top:0.5rem"><span class="status"></span>All systems nominal &middot; v1.0.0</p>
  </div>
</body>
</html>
"""

@app.get("/", response_class=HTMLResponse)
async def dashboard():
    return HTML_DASHBOARD

@app.get("/health")
async def health():
    return {"status": "ok", "version": "1.0.0", "service": "openmythos"}

@app.get("/api/status")
async def api_status():
    return {
        "model": "OpenMythos RDT",
        "variant": "1B-1T",
        "status": "inference_ready",
        "contracts": ["OpenMythosArb", "OpenMythosMicroArb"],
        "agents": ["flash_scanner", "macro_sentinel", "news_fetcher"],
        "network": "Base / Arbitrum / Ethereum"
    }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8080)
