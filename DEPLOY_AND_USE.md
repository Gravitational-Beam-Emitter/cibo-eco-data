# Eco Data Platform — 部署与使用指南

## 概述

全球经济情报平台，涵盖 **3 大类 24 个数据源**（宏观经济 21 个、国家风险 2 个、名称筛查 1 个），支持 MCP / REST API / Python SDK 三种接入方式。

### 数据覆盖

| 类别 | 数据源 | 指标数 | 需要 API Key |
|---|---|---|---|
| **宏观经济** | | | |
| US / FRED | Federal Reserve Economic Data | 58 | **是** |
| China / AKShare | 东方财富 / 新浪 / Jin10 | 33 | 否 |
| Global / World Bank | World Bank WDI API | 21 | 否 |
| Eurozone / AKShare | Jin10 财经日历 | 12 | 否 |
| UK / AKShare | Jin10 财经日历 | 10 | 否 |
| Alternative / Leading | AKShare (半导体、航运、商品、ETF) | 10 | 否 |
| DeFi & Prediction Markets | Polymarket + DeFi Llama + CoinGecko | 10 | 否 |
| Bond Market / AKShare | 中美债券收益率、可转债 | 9 | 否 |
| Central Bank Rates | Jin10 财经日历 | 9 | 否 |
| Hong Kong / AKShare | 香港宏观数据 | 8 | 否 |
| Japan / BoJ+AKShare | Bank of Japan + Jin10 | 7 | 否 |
| Canada / AKShare | Jin10 财经日历 | 7 | 否 |
| Futures / AKShare | 新浪财经主力合约 | 6 | 否 |
| Germany / AKShare | Jin10 财经日历 | 6 | 否 |
| Australia / AKShare | Jin10 财经日历 | 6 | 否 |
| Switzerland / AKShare | Jin10 财经日历 | 5 | 否 |
| Shipping / AKShare | 波罗的海指数 BDI/BCI/BPI/BCTI | 4 | 否 |
| LLM Ecosystem | GitHub + HuggingFace + PyPI | 19 | 否 |
| Energy / EIA | U.S. EIA Open Data | 2 | **是** |
| AI Infrastructure | FRED (NASDAQ, PPI, IP, Employment, Energy) | 21 | **是** |
| AI Company Financials | Yahoo Finance (yfinance) | 17 | 否 |
| **国家风险评级** | | | |
| AML/CFT Ratings | FATF + US State Dept + Basel Institute | 6 | 否 |
| Sanctions & Corruption | OFAC + Transparency International | 8 | 否 |
| **名称筛查** | | | |
| Name Screening | OpenSanctions + GDELT + HK/TW enforcement | 383K 实体 | 否 |

---

## 1. 部署

### 1.1 环境要求

```
Python 3.9+
DuckDB
```

### 1.2 安装依赖

```bash
cd "cibo eco data"
pip install -r requirements.txt
# requirements 至少包含:
#   duckdb, pandas, requests, fastapi, uvicorn, apscheduler
#   fredapi         (FRED 数据必需)
#   akshare         (中国/国际数据必需)
#   eiapy           (EIA 能源数据可选)
#   pypistats       (PyPI 下载量必需)
#   python-dotenv   (环境变量)
```

### 1.3 配置 API Keys

创建 `.env` 文件在项目根目录：

```bash
# 必需 — 58 个 US 指标
FRED_API_KEY=your_fred_api_key_here
# 获取: https://fred.stlouisfed.org/docs/api/api_key.html

# 可选 — 2 个 EIA 能源指标
EIA_API_KEY=your_eia_api_key_here
# 获取: https://www.eia.gov/opendata/

# 数据库路径（默认项目根目录）
ECO_DATA_DB=eco_data.duckdb
```

无 FRED Key 时其余 180+ 指标仍可正常使用。

### 1.4 首次数据拉取

```bash
# 拉取全部 287 指标（约 15-25 分钟，取决于网络）
python3 -c "
from app.pipeline import run_once
summary = run_once()
print(summary)
"

# 或按数据源拉取
python3 -c "
from app.pipeline import run_once
# 中国数据
run_once(sources=['cn'])
# DeFi 数据
run_once(sources=['defi'])
"
```

### 1.5 启动服务

```bash
# REST API (端口 8000)
uvicorn app.api:app --host 0.0.0.0 --port 8000
# OpenAPI docs 自动生成在 http://localhost:8000/docs
```

MCP Server 无需单独启动——在 `.mcp.json` 中配置后 Claude Code 自动管理：

```json
{
  "mcpServers": {
    "eco-data": {
      "command": "python3",
      "args": ["mcp/eco_data_server.py"],
      "cwd": "/path/to/cibo eco data"
    }
  }
}
```

---

## 2. 三种接入方式

### 2.1 MCP (给 AI Agent)

Agent 调用 `tools/list` 看到 12 个工具：

| 工具 | 用途 |
|---|---|
| `data_sources_by_category` | **第一步** — 三层分类概览（宏观/风险/筛查） |
| `data_sources` | 浏览全部 24 个数据源及其描述 |
| `data_summary` | 概况：总指标数、观测数、按数据源分布 |
| `list_indicators` | 列出全部指标（可按 source 筛选） |
| `search_indicators` | 按关键词搜索（如 "CPI"、"credit spread"） |
| `get_latest` | 获取某个指标的最新值 |
| `query_data` | 查询时间序列（支持日期范围、limit） |
| `list_risk_indicators` | 列出国家风险指标（AML、制裁、腐败感知） |
| `search_name` | **名称筛查** — 中英文模糊匹配制裁/PEP名单 |
| `name_screening_stats` | 名称筛查数据库统计 |
| `cn_stock_status` | 查看 A 股涨停数据状态 |
| `list_tags` | 浏览所有标签及覆盖数 |

**推荐 Agent 使用流程：**

```
1. data_sources_by_category → 了解三层分类结构
2. search_indicators        → 按主题搜索（如 "CPI"、"Polymarket"、"AML"）
3. query_data               → 获取具体指标的时间序列
4. search_name              → 制裁/PEP名单筛查（中英文）
```

### 2.2 REST API

Base URL: `http://localhost:8000`

**宏观数据：**

```
GET  /api/v1/categories              # 三层分类概览
GET  /api/v1/indicators              # 列出所有指标（?source=cn 筛选）
GET  /api/v1/indicators/search?q=    # 搜索指标
GET  /api/v1/indicators/{id}         # 单个指标详情
GET  /api/v1/data/{id}               # 时间序列（?start=&end=&limit=）
GET  /api/v1/data/{id}/latest        # 最新值
POST /api/v1/data/batch              # 批量查询时间序列
POST /api/v1/fetch?source=           # 触发数据刷新
GET  /api/v1/tags                    # 标签浏览
```

**国家风险评级：**

```
GET  /api/v1/risk/indicators         # 风险指标列表
GET  /api/v1/risk/indicators/{id}    # 单个风险指标详情
GET  /api/v1/risk/data/{id}          # 风险指标时间序列
GET  /api/v1/risk/data/{id}/latest   # 风险指标最新值
POST /api/v1/risk/fetch              # 刷新风险数据
```

**名称筛查：**

```
POST /api/v1/name-screening/search   # 单名称筛查（中英文）
POST /api/v1/name-screening/batch    # 批量名称筛查
GET  /api/v1/name-screening/stats    # 筛查数据库统计
POST /api/v1/name-screening/load-opensanctions  # 加载OpenSanctions
```

**系统：**

```
GET  /api/v1/health                  # 健康检查
```

OpenAPI 交互文档: `http://localhost:8000/docs` (按 Macros / Risk Ratings / Name Screening 分组)

### 2.3 Python SDK

```python
from eco_data_sdk import EcoDataClient

client = EcoDataClient("http://localhost:8000")

# 搜索
indicators = client.search("credit spread")

# 查数据
data = client.query_data(224, start="2024-01-01")  # BAA 10Y Spread
print(data["indicator"]["name"], data["count"], "obs")

# 最新值
latest = client.latest(224)
```

---

## 3. 新数据类型速查

### 信用利差 (Credit Spreads)

```
search: "spread" 或 "BAA" 或 "HY"
指标: BAA 10Y Spread, AAA 10Y Spread, HY OAS Spread, TED Spread
用途: 信用风险定价、市场压力检测
```

### 房地产 (Housing)

```
search: "housing" 或 "Case-Shiller"
指标: Housing Starts, Building Permits, Case-Shiller HPI
用途: 房地产周期、建筑活动先行指标
```

### 劳动力市场明细

```
search: "JOLTS" 或 "U6" 或 "participation"
指标: Labor Force Participation, JOLTS Job Openings, U6 Unemployment, Avg Hourly Earnings
用途: 劳动力市场松紧、工资通胀压力
```

### PCE 通胀 (Fed 首选)

```
search: "PCE"
指标: PCE, Core PCE, PPI All Commodities
用途: Fed 货币政策决策依据
```

### 金融条件 (Financial Conditions)

```
search: "financial" 或 "NFCI" 或 "stress"
指标: St. Louis Fed Financial Stress Index, Chicago Fed NFCI
用途: 系统性风险监测（负值=宽松，正值=紧缩）
```

### 全球主权债收益率

```
search: "10Y Yield"
指标: US, Germany, France, Italy, UK, Spain, Canada, Australia, Korea 10Y 国债
用途: 全球利率联动、利差交易、避险流动
```

### 领先指标

```
search: "leading" 或 "Empire" 或 "Chicago Fed"
指标: Leading Index, Chicago Fed Activity, Empire State Mfg, Global EPU
用途: 经济周期拐点预测
```

### DXY 美元指数

```
search: "DXY" 或 "Trade Weighted"
指标: Trade Weighted USD Index: Broad
用途: 美元强弱对全球流动性的影响
```

### DeFi & 预测市场

```
search: "Polymarket" 或 "DeFi" 或 "RWA"
指标: Polymarket 交易量、DEX TVL、DEX 24h 交易量、衍生品 TVL、RWA TVL、CEX 交易量
用途: 链上风险偏好、预测市场 crowd wisdom、TradFi 上链规模
```

### LLM 生态指标

```
search: "GitHub Stars" 或 "HF Downloads" 或 "PyPI"
指标: 9 个 LLM repo 的 GitHub Stars、5 个模型的 HuggingFace 下载量、5 个 SDK 的 PyPI 月下载
用途: AI 行业开发者心智份额、模型采用速度（token 消费的代理指标）
```

### AML/CFT 国家风险评级

```
search: "AML" 或 "FATF" 或 "INCSR" 或 "Basel"
指标: FATF 黑/灰名单国家数、主要洗钱关注国数（INCSR）、Basel AML 指数综合评分
API:  GET /api/v1/risk/indicators（列出全部风险指标）
      GET /api/v1/risk/data/{id}（时间序列，按国家/年份）
用途: CDD/AML 合规风险评估、国家洗钱风险分级、监管合规报告支撑
```

### 制裁与腐败数据

```
search: "sanctions" 或 "OFAC" 或 "CPI" 或 "corruption"
指标: OFAC SDN 按国家聚合制裁数量、TI 腐败感知指数（180 国评分排名）
API:  同上 risk/ 端点
用途: 制裁风险评估、腐败指数跟踪、合规筛查
```

### 名称筛查（中英文）

```
API:  POST /api/v1/name-screening/search  {"query":"习近平","include_news":false}
      POST /api/v1/name-screening/batch   {"queries":["name1","name2"]}
SDK:  client.screen_name("习近平") 或 client.screen_name_batch(["name1","name2"])
MCP:  search_name {"query":"习近平"}
用途: 制裁名单 + PEP 数据库模糊匹配（383K 实体，含中文名 + 粤拼）
      支持普通话拼音、广东话粤拼（Jyutping）、繁体→简体自动转换
      数据源：OpenSanctions + 台湾 FSC 执法 + 香港 SFC/HKMA 执法
```

---

## 4. 定时调度

内置三层 cron 调度（`app/pipeline.py` 的 `Scheduler` 类）：

| 层级 | Cron | 说明 |
|---|---|---|
| 日度 | `7 8 * * *` | 每天 08:07 — 日频指标 |
| 周度 | `13 8 * * 1` | 周一 08:13 — 日频 + 周频 |
| 月度 | `21 8 15 * *` | 每月 15 日 08:21 — 全部包括月/季/年 |

启动调度器：

```python
from app.pipeline import start_scheduler
scheduler = start_scheduler()
# 后台自动运行，Ctrl+C 停止
```

---

## 5. 常见问题

**Q: FRED API 限流？**
FRED 免费 tier 120 req/min。Pipeline 每次拉取约 60 个 FRED 指标，远低于限额。

**Q: Jin10 数据不更新？**
Eurozone/UK/德国/澳洲/加拿大/瑞士/banks 数据源来自 Jin10 财经日历，上游在 2025 年 8-9 月停止更新。这些指标在 report.html 中用红色 stale 标记。FRED 的对应指标更可靠（如 sovereign_yield 系列）。

**Q: PyPI 下载量超时？**
已切换到 `pypistats` 库（httpx-based），带 3 次重试 + 退避。首次调用可能触发 429，会自动重试。

**Q: 如何查看全部指标？**
打开 `report.html`（浏览器直接打开），或调用 API 的 `GET /api/v1/indicators`。
