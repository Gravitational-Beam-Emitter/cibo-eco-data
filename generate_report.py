#!/usr/bin/env python3
"""Generate report.html — macro data inventory for fund managers."""
import duckdb, json
from datetime import date, datetime
from collections import defaultdict

con = duckdb.connect("eco_data.duckdb", read_only=True)

sql = """
SELECT i.id, i.source, i.name, i.method, i.description, i.frequency,
       COUNT(o.date) as obs_count, MIN(o.date) as first_date,
       MAX(o.date) as last_date, MAX(o.fetched_at) as last_fetched
FROM indicators i
LEFT JOIN observations o ON i.id = o.indicator_id
GROUP BY i.id, i.source, i.name, i.method, i.description, i.frequency
ORDER BY i.source, i.name
"""
rows = con.execute(sql).fetchall()
cols = ['id','source','name','method','description','frequency','obs_count','first_date','last_date','last_fetched']
indicators = []
for r in rows:
    d = dict(zip(cols, r))
    for k in ('first_date','last_date','last_fetched'):
        d[k] = str(d[k]) if d[k] else None
    indicators.append(d)

total_obs = con.execute("SELECT COUNT(*) FROM observations").fetchone()[0]
last_update = str(con.execute("SELECT MAX(fetched_at) FROM observations").fetchone()[0])

SOURCE_META = {
    "us":   ("FRED",           "Federal Reserve Economic Data (FRED)",        "API Key 必需",  "https://fred.stlouisfed.org/"),
    "cn":   ("AKShare",        "AKShare — 中国宏观数据 (东方财富/新浪等)",     "无需 API Key",   "https://akshare.akfamily.xyz/"),
    "hk":   ("AKShare",        "AKShare — 香港宏观数据",                      "无需 API Key",   "https://akshare.akfamily.xyz/"),
    "euro": ("AKShare/Jin10",  "AKShare — 欧元区宏观数据 (Jin10财经日历)",    "无需 API Key",   "https://akshare.akfamily.xyz/"),
    "uk":   ("AKShare/Jin10",  "AKShare — 英国宏观数据 (Jin10财经日历)",      "无需 API Key",   "https://akshare.akfamily.xyz/"),
    "de":   ("AKShare/Jin10",  "AKShare — 德国宏观数据 (Jin10财经日历)",      "无需 API Key",   "https://akshare.akfamily.xyz/"),
    "au":   ("AKShare/Jin10",  "AKShare — 澳大利亚宏观数据 (Jin10财经日历)",  "无需 API Key",   "https://akshare.akfamily.xyz/"),
    "ca":   ("AKShare/Jin10",  "AKShare — 加拿大宏观数据 (Jin10财经日历)",    "无需 API Key",   "https://akshare.akfamily.xyz/"),
    "ch":   ("AKShare/Jin10",  "AKShare — 瑞士宏观数据 (Jin10财经日历)",      "无需 API Key",   "https://akshare.akfamily.xyz/"),
    "shipping": ("AKShare/Sina","AKShare — 全球航运指数 (BDI/BCI/BPI/BCTI)",   "无需 API Key",   "https://finance.sina.com.cn/"),
    "banks": ("AKShare/Jin10", "AKShare — 全球央行政策利率 (Jin10财经日历)",  "无需 API Key",   "https://akshare.akfamily.xyz/"),
    "alt":  ("AKShare",        "AKShare — 另类前瞻指标 (半导体/航运/商品/ETF)", "无需 API Key",   "https://akshare.akfamily.xyz/"),
    "llm":  ("GitHub/HF",      "GitHub + HuggingFace + PyPI — LLM生态代理指标", "GitHub限60次/小时", "https://github.com/"),
    "defi": ("PolyMarket/DeFi","Polymarket + DeFi Llama + CoinGecko — 链上金融指标", "无需 API Key", "https://polymarket.com/"),
    "bond": ("AKShare",        "AKShare — 中美债券收益率及可转债",            "无需 API Key",   "https://akshare.akfamily.xyz/"),
    "futures": ("AKShare/Sina", "Sina 新浪财经 — 期货主力连续合约",            "无需 API Key",   "https://finance.sina.com.cn/"),
    "global_": ("World Bank",   "World Bank API — 全球宏观经济指标",           "无需 API Key",   "https://data.worldbank.org/"),
    "jp":    ("BoJ + AKShare",  "Bank of Japan + AKShare — 日本宏观数据",      "无需 API Key",   "https://www.boj.or.jp/en/"),
    "energy":("EIA",            "U.S. Energy Information Administration",      "API Key 必需",   "https://www.eia.gov/opendata/"),
}

SOURCE_LABEL = {"us":"US / FRED","cn":"China / AKShare","hk":"Hong Kong / AKShare",
                "euro":"Eurozone / AKShare","uk":"UK / AKShare","de":"Germany / AKShare",
                "au":"Australia / AKShare","ca":"Canada / AKShare","ch":"Switzerland / AKShare",
                "shipping":"Global Shipping","banks":"Central Bank Rates","alt":"Alternative / Leading",
                "llm":"LLM Ecosystem","defi":"DeFi & Prediction Markets",
                "bond":"Bond Market","futures":"Futures Market","global_":"Global / World Bank",
                "jp":"Japan / BoJ+AKShare","energy":"Energy / EIA","sdmx":"SDMX / OECD+ECB"}

FREQ_LABEL = {"daily":"日度","weekly":"周度","monthly":"月度","quarterly":"季度","yearly":"年度"}

# Sort sources
src_order = ["us","cn","euro","uk","de","jp","au","ca","ch","hk","bond","futures","shipping","banks","alt","llm","defi","global_","energy"]
by_source = defaultdict(list)
for ind in indicators:
    by_source[ind['source']].append(ind)

# Flag stale: last_date older than 2025-12-01 for sub-annual data
STALE_CUTOFF = "2025-12-01"
for ind in indicators:
    if ind['last_date'] and ind['frequency'] != 'yearly':
        ind['stale'] = ind['last_date'] < STALE_CUTOFF
    else:
        ind['stale'] = False

today = date.today().strftime("%Y-%m-%d")

# ── Render helpers ──
def fmt_num(n):
    if n >= 1_000_000:
        return f"{n/1_000_000:.1f}M"
    if n >= 1000:
        return f"{n/1000:.0f}K"
    return str(n)

def fmt_date(s):
    if not s: return "—"
    try:
        dt = datetime.fromisoformat(s)
        return dt.strftime("%Y-%m-%d")
    except:
        return s[:10]

def stale_badge(ind):
    if ind.get('stale'):
        return ' <span class="badge badge-stale">数据滞后</span>'
    return ''

def _stale_days(ind):
    """Calculate days since last data point."""
    if not ind.get('last_date'):
        return "? 天"
    try:
        last = datetime.fromisoformat(ind['last_date']).date()
        days = (date.today() - last).days
        return f"{days} 天"
    except:
        return "? 天"

# ── Build HTML ──
html = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Eco Data — 宏观数据看板</title>
<style>
:root {{
  --bg: #0c0e12;
  --card: #141820;
  --border: #1e2430;
  --text: #c8cdd4;
  --dim: #6b7280;
  --accent: #3b82f6;
  --green: #22c55e;
  --amber: #f59e0b;
  --red: #ef4444;
  --teal: #14b8a6;
}}
* {{ margin:0; padding:0; box-sizing:border-box; }}
body {{
  background: var(--bg); color: var(--text);
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Noto Sans SC', sans-serif;
  line-height: 1.5; padding: 24px; max-width: 1200px; margin: 0 auto;
}}
h1 {{ font-size: 24px; font-weight: 700; letter-spacing: -0.5px; }}
h2 {{ font-size: 16px; font-weight: 600; color: #e5e7eb; margin: 28px 0 12px; padding-bottom: 6px; border-bottom: 1px solid var(--border); }}
h3 {{ font-size: 14px; font-weight: 600; color: #d1d5db; margin: 8px 0; }}

.cards {{ display:grid; grid-template-columns: repeat(auto-fit, minmax(160px,1fr)); gap:12px; margin: 20px 0; }}
.card {{
  background: var(--card); border: 1px solid var(--border); border-radius: 8px;
  padding: 16px 20px;
}}
.card .label {{ font-size: 12px; color: var(--dim); text-transform: uppercase; letter-spacing: 0.5px; }}
.card .value {{ font-size: 28px; font-weight: 700; margin-top: 4px; }}
.card .sub {{ font-size: 11px; color: var(--dim); margin-top: 2px; }}

.section {{ margin: 16px 0; }}

.toolbar {{
  display:flex; gap:8px; margin: 16px 0; flex-wrap:wrap;
}}
.toolbar button {{
  background: var(--card); border: 1px solid var(--border); color: var(--text);
  padding: 6px 14px; border-radius: 6px; cursor: pointer; font-size: 13px;
  transition: all .15s;
}}
.toolbar button:hover {{ border-color: var(--accent); color: #fff; }}
.toolbar button.expand-all {{ border-color: var(--teal); color: var(--teal); }}

table {{ width:100%; border-collapse: collapse; font-size: 13px; }}
thead th {{
  text-align: left; padding: 8px 10px; font-size: 11px; text-transform: uppercase;
  color: var(--dim); letter-spacing: 0.5px; border-bottom: 1px solid var(--border);
  position: sticky; top: 0; background: var(--card); z-index: 1;
}}
tbody td {{ padding: 7px 10px; border-bottom: 1px solid #1a1d25; }}
tbody tr:hover {{ background: rgba(255,255,255,0.02); }}
td.num {{ text-align: right; font-variant-numeric: tabular-nums; }}
td.range {{ color: var(--dim); font-size: 12px; white-space: nowrap; }}

.source-group {{
  background: var(--card); border: 1px solid var(--border); border-radius: 8px;
  margin-bottom: 12px; overflow: hidden;
}}
.source-header {{
  display:flex; align-items:center; justify-content:space-between;
  padding: 12px 16px; cursor: pointer; user-select: none;
  transition: background .1s;
}}
.source-header:hover {{ background: rgba(255,255,255,0.03); }}
.source-header .src-label {{ font-weight: 600; font-size: 14px; }}
.source-header .src-count {{ font-size: 12px; color: var(--dim); }}
.source-header .src-arrow {{ color: var(--dim); transition: transform .2s; font-size: 12px; }}
.source-group.collapsed .source-header .src-arrow {{ transform: rotate(-90deg); }}
.source-group.collapsed table {{ display: none; }}
.source-body {{ overflow-x: auto; }}

.badge {{
  display:inline-block; font-size: 10px; padding: 1px 6px; border-radius: 10px;
  font-weight: 600; margin-left: 4px; vertical-align: middle;
}}
.badge-stale {{ background: rgba(239,68,68,0.15); color: var(--red); }}
.badge-daily {{ background: rgba(59,130,246,0.12); color: var(--accent); }}
.badge-monthly {{ background: rgba(20,184,166,0.12); color: var(--teal); }}
.badge-quarterly {{ background: rgba(245,158,11,0.12); color: var(--amber); }}

.cron-table td {{ padding: 6px 12px; }}
.cron-table .cron {{ font-family: 'SF Mono', 'Fira Code', monospace; color: var(--accent); }}

.note {{ font-size: 12px; color: var(--dim); padding: 8px 0; line-height: 1.7; }}
.note a {{ color: var(--accent); text-decoration: none; }}
.note a:hover {{ text-decoration: underline; }}
.note code {{
  background: rgba(255,255,255,0.06); padding: 1px 5px; border-radius: 3px;
  font-size: 11px; font-family: 'SF Mono', 'Fira Code', monospace;
}}

.footer {{ margin-top: 32px; padding-top: 16px; border-top: 1px solid var(--border); font-size: 11px; color: var(--dim); }}
.row {{ display:flex; gap:24px; flex-wrap:wrap; }}
.col {{ flex:1; min-width: 260px; }}

.warn {{ background: rgba(239,68,68,0.08); border-left: 3px solid var(--red); padding: 8px 12px; border-radius: 4px; font-size: 13px; margin: 8px 0; }}
.info {{ background: rgba(59,130,246,0.08); border-left: 3px solid var(--accent); padding: 8px 12px; border-radius: 4px; font-size: 13px; margin: 8px 0; }}
</style>
</head>
<body>

<h1>宏观数据看板</h1>
<p style="color:var(--dim);font-size:13px;margin-top:4px;">
  数据平台概况 &middot; 生成时间 {today}
</p>

<!-- Overview Cards -->
<div class="cards">
  <div class="card">
    <div class="label">指标总数</div>
    <div class="value" style="color:var(--accent)">{len(indicators)}</div>
    <div class="sub">{len(by_source)} 个数据源</div>
  </div>
  <div class="card">
    <div class="label">总观测值</div>
    <div class="value" style="color:var(--teal)">{fmt_num(total_obs)}</div>
    <div class="sub">条时间序列数据点</div>
  </div>
  <div class="card">
    <div class="label">数据源</div>
    <div class="value" style="color:var(--amber)">{len(by_source)}</div>
    <div class="sub">FRED · AKShare · Jin10 · World Bank · EIA · BoJ · GitHub · HuggingFace</div>
  </div>
  <div class="card">
    <div class="label">最后更新</div>
    <div class="value" style="font-size:22px;color:var(--green)">{fmt_date(last_update)}</div>
    <div class="sub">全部数据刷新时间</div>
  </div>
</div>

<!-- Data Catalog -->
<h2>数据目录</h2>
<div class="toolbar">
  <button class="expand-all" onclick="expandAll()">展开全部</button>
  <button onclick="collapseAll()">折叠全部</button>
</div>
'''

# Indicator table per source
for src in src_order:
    if src not in by_source:
        continue
    items = by_source[src]
    meta = SOURCE_META.get(src, ("","","",""))
    src_label = SOURCE_LABEL.get(src, src)
    stale_n = sum(1 for i in items if i.get('stale'))
    stale_warn = f' <span class="badge badge-stale">{stale_n} 个指标数据滞后</span>' if stale_n else ''

    html += f'''
<div class="source-group collapsed">
  <div class="source-header" onclick="toggleSource(this)">
    <span>
      <span class="src-label">{src_label}</span>
      <span class="src-count"> — {len(items)} 个指标</span>{stale_warn}
    </span>
    <span class="src-arrow">▼</span>
  </div>
  <div class="source-body">
    <table>
      <thead><tr>
        <th>指标</th><th>描述</th><th>频率</th><th>数据量</th><th>时间范围</th><th>更新时间</th><th>状态</th>
      </tr></thead>
      <tbody>'''
    for ind in items:
        freq = FREQ_LABEL.get(ind.get('frequency',''), ind.get('frequency',''))
        range_str = f"{fmt_date(ind['first_date'])} ~ {fmt_date(ind['last_date'])}"
        stale_flag = ' ⚠ 滞后' if ind.get('stale') else ' ✓ 正常'
        stale_cls = ' style="color:var(--red)"' if ind.get('stale') else ' style="color:var(--green)"'
        html += f'''
        <tr>
          <td><strong>{ind['name']}</strong></td>
          <td style="color:var(--dim)">{ind.get('description','')}</td>
          <td><span class="badge badge-{ind.get('frequency','monthly')}">{freq}</span></td>
          <td class="num">{fmt_num(ind['obs_count'])}</td>
          <td class="range">{range_str}</td>
          <td class="range">{fmt_date(ind['last_fetched'])}</td>
          <td{stale_cls}>{stale_flag}</td>
        </tr>'''
    html += '''
      </tbody>
    </table>
  </div>
</div>'''

# Update Schedule
html += '''
<h2>更新调度</h2>
<table class="cron-table">
  <thead><tr><th>层级</th><th>Cron 表达式</th><th>触发时间</th><th>覆盖范围</th></tr></thead>
  <tbody>
    <tr>
      <td><span class="badge badge-daily">日度</span></td>
      <td class="cron">7 8 * * *</td>
      <td>每天 08:07 (北京时间)</td>
      <td>日频指标 (收益率、汇率、期货、北向资金、HIBOR等)</td>
    </tr>
    <tr>
      <td><span class="badge badge-monthly">周度</span></td>
      <td class="cron">13 8 * * 1</td>
      <td>每周一 08:13 (北京时间)</td>
      <td>日频 + 周频指标 (EIA原油、天然气等)</td>
    </tr>
    <tr>
      <td><span class="badge badge-quarterly">月度</span></td>
      <td class="cron">21 8 15 * *</td>
      <td>每月15日 08:21 (北京时间)</td>
      <td>全部指标 (含月度/季度/年度宏观数据)</td>
    </tr>
  </tbody>
</table>
<p class="note">
  采用 <strong>三级递增</strong> 策略：日频数据每天更新，周/月频数据按需触发。中国宏观数据通常在次月中旬发布，美国数据滞后约 2-4 周。World Bank 年度数据年末更新。
</p>
'''

# Source details
html += '''
<h2>数据源详情</h2>
<div class="row">
'''
for src in src_order:
    if src not in by_source:
        continue
    meta = SOURCE_META.get(src, ("","","",""))
    items = by_source[src]
    stale_items = [i for i in items if i.get('stale')]
    html += f'''
  <div class="col">
    <h3>{SOURCE_LABEL.get(src, src)}</h3>
    <p class="note">
      <strong>提供方：</strong>{meta[1]}<br>
      <strong>访问方式：</strong>{meta[2]}<br>
      <strong>官网：</strong><a href="{meta[3]}" target="_blank">{meta[3]}</a><br>
      <strong>指标数：</strong>{len(items)}<br>
      <strong>最早数据：</strong>{min((i['first_date'] for i in items if i['first_date']), default='—')[:10]}<br>'''
    if stale_items:
        html += f'<strong style="color:var(--red)">⚠ 滞后指标：</strong>'
        for si in stale_items:
            html += f'{si["name"]} (最新: {si["last_date"][:10]}), '
        html = html.rstrip(', ')
    html += '</p></div>\n'
html += '</div>'

# Known Issues
stale_all = [i for i in indicators if i.get('stale')]
html += '''
<h2>数据质量说明</h2>
'''
if stale_all:
    html += f'''
<div class="warn">
  <strong>⚠ 以下 {len(stale_all)} 个指标数据存在滞后，可能由于上游数据源接口变更或延迟发布：</strong>
</div>
<ul class="note" style="margin-left:20px;">'''
    for si in stale_all:
        html += f'<li><strong>{si["source"]}/{si["name"]}</strong> — 最新数据 {si["last_date"][:10]}（滞后约 {_stale_days(si)} 天）</li>'
    html += '</ul>'
html += '''
<div class="info">
  <strong>已知问题：</strong><br>
  • AKShare 上游 (东方财富/Sina/中国统计局) 部分接口可能变更，导致数据停在特定时间点<br>
  • EastMoney API (<code>*_em</code>) 限频严格，高并发请求返回 502 Bad Gateway<br>
  • World Bank API 数据仅覆盖 2020-2024 年，因 wbdata 包的数据更新延迟<br>
  • EIA 数据需要 API Key，天然气数据可能在月初更新滞后
</div>
'''

# Access methods
html += f'''
<h2>访问方式</h2>
<div class="row">
  <div class="col">
    <h3>REST API</h3>
    <p class="note">
      <code>GET /api/v1/indicators</code> — 获取所有指标列表<br>
      <code>GET /api/v1/data/{{indicator_id}}</code> — 获取指标数据<br>
      <code>GET /api/v1/latest</code> — 获取最新观测值<br>
      <strong>服务地址：</strong><code>http://localhost:8000</code><br>
      <strong>文档：</strong><code>http://localhost:8000/docs</code> (Swagger UI)
    </p>
  </div>
  <div class="col">
    <h3>MCP Tool (Claude Code)</h3>
    <p class="note">
      <strong>配置：</strong>项目根目录 <code>.mcp.json</code>，启动时自动注册<br>
      <code>list_indicators</code> — 列出所有指标<br>
      <code>query_data</code> — 查询指定指标时间序列<br>
      <code>get_latest</code> — 获取最新值<br>
      <code>search_indicators</code> — 按关键词搜索指标<br>
      <code>data_summary</code> — 数据总览统计<br>
      <code>cn_stock_status</code> — 中国股市状态
    </p>
  </div>
  <div class="col">
    <h3>Web 前端</h3>
    <p class="note">
      <strong>地址：</strong><code>http://localhost:3000/zt</code><br>
      <strong>页面：</strong>跨资产对比图 (Cross Charts)<br>
      显示 PMI、M2、LPR、房价、原油、联邦基金利率等核心宏观指标
    </p>
  </div>
</div>
'''

html += f'''
<div class="footer">
  Eco Data Platform &middot; 生成时间 {today} &middot; 数据最后更新 {fmt_date(last_update)} &middot;
  <span style="color:var(--accent)">{len(indicators)}</span> 指标 ·
  <span style="color:var(--teal)">{fmt_num(total_obs)}</span> 观测值
</div>

<script>
function toggleSource(el) {{
  el.closest('.source-group').classList.toggle('collapsed');
}}
function expandAll() {{
  document.querySelectorAll('.source-group').forEach(g => g.classList.remove('collapsed'));
}}
function collapseAll() {{
  document.querySelectorAll('.source-group').forEach(g => g.classList.add('collapsed'));
}}
</script>
</body>
</html>
'''

def _stale_days(ind):
    """Calculate days since last data point."""
    if not ind.get('last_date'):
        return "? 天"
    try:
        last = datetime.fromisoformat(ind['last_date']).date()
        days = (date.today() - last).days
        return f"{days} 天"
    except:
        return "? 天"

with open("report.html", "w", encoding="utf-8") as f:
    f.write(html)

print(f"Wrote report.html — {len(indicators)} indicators, {total_obs} observations")
con.close()
