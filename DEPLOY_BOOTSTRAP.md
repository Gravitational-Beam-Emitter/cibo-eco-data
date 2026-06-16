# 部署 Eco Data 到新机器 — 给另一个 Claude 的执行清单

## 前置条件
- Python 3.9+
- Docker（如果需要部署 WeWe RSS 公众号抓取）
- 项目文件已复制到目标机器（含 `eco_data.duckdb`）
- FRED API Key（https://fred.stlouisfed.org/docs/api/api_key.html）

---

## 步骤 1：安装依赖

```bash
cd "cibo eco data"
pip install duckdb pandas requests fastapi uvicorn apscheduler fredapi akshare pypistats python-dotenv
```

---

## 步骤 2：配置 API Key

```bash
echo 'FRED_API_KEY=你的key' > .env
# 可选：echo 'EIA_API_KEY=你的key' >> .env
```

无 FRED Key 时，180+ 指标仍可使用（FRED 的 58+21 个指标会跳过）。

---

## 步骤 3：验证数据就绪

```bash
python3 -c "
import duckdb
con = duckdb.connect('eco_data.duckdb', read_only=True)
total = con.execute('SELECT COUNT(*) FROM indicators').fetchone()[0]
obs = con.execute('SELECT COUNT(*) FROM observations').fetchone()[0]
tags = con.execute(\"SELECT COUNT(DISTINCT tag) FROM (SELECT UNNEST(string_split(tags,',')) AS tag FROM indicators WHERE tags != '')\").fetchone()[0]
print(f'OK: {total} indicators, {obs} observations, {tags} tags')
# 预期输出: OK: 287 indicators, 491000+ observations, 28 tags
con.close()
"
```

如果 DB 为空或缺失，拉取数据：

```bash
python3 -c "
from app.pipeline import run_once
print(run_once())
"
# 首次全量拉取需 15-25 分钟
```

---

## 步骤 4：启动服务（二选一或全开）

### 方式 A：MCP Server（给 Claude Code 用）

`.mcp.json` 已配置好，重启 Claude Code 即可。如果没有，创建：

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

MCP 提供 8 个工具：`data_sources`、`data_summary`、`list_indicators`、`search_indicators`、`list_tags`、`query_data`、`get_latest`、`cn_stock_status`。

### 方式 B：REST API（给其他程序/SDK 调用）

```bash
uvicorn app.api:app --host 0.0.0.0 --port 8000
# OpenAPI docs: http://localhost:8000/docs
```

API 提供 9 个端点：

| 端点 | 说明 |
|---|---|
| `GET /api/v1/health` | 健康检查 |
| `GET /api/v1/indicators?source=&tag=` | 列出指标（可筛选数据源+标签） |
| `GET /api/v1/indicators/search?q=` | 关键词搜索（搜名称+描述+标签） |
| `GET /api/v1/indicators/{id}` | 单个指标详情 |
| `GET /api/v1/tags` | 28 个分类标签及覆盖数 |
| `GET /api/v1/data/{id}?start=&end=&limit=` | 时间序列 |
| `GET /api/v1/data/{id}/latest` | 最新值 |
| `POST /api/v1/fetch?source=` | 触发数据刷新 |

---

## 步骤 5：数据发现指南

### 数据覆盖

| 类别 | 数据源 | 指标数 |
|---|---|---|
| US / FRED | Federal Reserve | 58 |
| China / AKShare | 东方财富/新浪/Jin10 | 32 |
| Global / World Bank | World Bank WDI | 31 |
| AI Infrastructure / FRED | 半导体→数据中心→电力全链 | 21 |
| LLM Ecosystem | GitHub+HuggingFace+PyPI | 19 |
| AI Company Financials | Yahoo Finance | 17 |
| Eurozone / AKShare | Jin10 财经日历 | 12 |
| DeFi & Prediction Markets | Polymarket+DeFi Llama+CoinGecko | 10 |
| Alternative / Leading | AKShare | 10 |
| UK / AKShare | Jin10 财经日历 | 10 |
| Bond Market / AKShare | 中美债券收益率 | 9 |
| Central Bank Rates | Jin10 财经日历 | 9 |
| Hong Kong / AKShare | 香港宏观数据 | 8 |
| Canada / AKShare | Jin10 | 7 |
| Futures / AKShare | 新浪财经主力合约 | 6 |
| Germany / AKShare | Jin10 | 6 |
| Australia / AKShare | Jin10 | 6 |
| Switzerland / AKShare | Jin10 | 5 |
| Japan / BoJ+AKShare | BoJ+Jin10 | 5 |
| Shipping / AKShare | 波罗的海指数 | 4 |
| Energy / EIA | 原油+天然气 | 2 |

### 标签分类索引

287 个指标全部打上中文标签（28 个分类），**不需要猜关键词即可浏览**：

| 标签 | 覆盖 | 标签 | 覆盖 |
|---|---|---|---|
| 增长 | 57 | AI公司财务 | 17 |
| 通胀 | 40 | 央行利率 | 16 |
| AI产业链 | 39 | 原材料 | 16 |
| 全球宏观 | 31 | 就业 | 13 |
| 市场情绪 | 27 | 汇率 | 12 |
| AI算力 | 26 | 能源电力 | 12 |
| 债券 | 25 | 数据中心 | 11 |
| 货币政策 | 24 | 贸易 | 10 |
| 利率 | 24 | 房地产 | 10 |
| LLM生态 | 19 | 资金流向 | 9 |
| 半导体 | 8 | DeFi | 7 |
| 航运 | 6 | 期货 | 6 |
| 信用利差 | 4 | 预测市场 | 3 |
| 金融条件 | 2 | 风险情绪 | 1 |

### 外部项目如何发现数据

无论 MCP、REST API 还是 Python SDK，标准流程：

```
1. data_sources / list_tags           → 了解 21 个数据源 + 28 个标签的全貌
2. list_indicators?tag=AI产业链       → 按标签筛选（一次性拿到全部 39 个 AI 供应链指标）
3. search_indicators?q=关键词         → 按名称/描述/标签搜索
4. query_data?start=&end=             → 取时间序列
```

**示例**：
```bash
# 拿到所有 AI 产业链数据
curl "http://localhost:8000/api/v1/indicators?tag=AI产业链"

# 在 AI 产业链里搜数据中心
curl "http://localhost:8000/api/v1/indicators/search?q=数据中心"

# 取 NVIDIA 营收的时间序列
curl "http://localhost:8000/api/v1/data/261?start=2023-01-01"
```

---

## 步骤 6：定时调度（可选）

```python
from app.pipeline import start_scheduler
scheduler = start_scheduler()
# 后台自动运行：
#   日度 08:07 — 日频指标
#   周度 周一 08:13 — 日频+周频
#   月度 15日 08:21 — 全部包括月/季/年
# Ctrl+C 停止
```

---

## 步骤 7：部署 WeWe RSS（可选 — 微信公众号抓取）

如果需要抓微信公众号文章作为数据源补充：

```bash
mkdir -p ~/wewe-rss && cd ~/wewe-rss

cat > docker-compose.yml << 'EOF'
services:
  wewe-rss:
    image: cooderl/wewe-rss-sqlite:latest
    restart: always
    ports:
      - "4000:4000"
    environment:
      - DATABASE_TYPE=sqlite
      - AUTH_CODE=set_auth_code_here
      - FEED_MODE=fulltext
      - CRON_EXPRESSION=35 8,20 * * *
    volumes:
      - ./data:/app/data
EOF

docker compose up -d
```

1. 浏览器 `http://localhost:4000` → 输入 AUTH_CODE
2. 微信读书扫码（仅一次，别勾选"24h自动退出"）
3. 在微信读书复制公众号文章链接 → 粘贴添加订阅
4. 之后每天自动定时抓取，生成 RSS：`http://localhost:4000/feeds/公众号名.atom`

详见 `DEPLOY_WEWE_RSS.md`。

---

## 验证清单

部署完成后逐项检查：

- [ ] `python3 -c "import duckdb; con=duckdb.connect('eco_data.duckdb',read_only=True); print(con.execute('SELECT COUNT(*) FROM indicators').fetchone()[0])"` → 287
- [ ] Agent 调用 `data_sources` → 返回 21 个数据源
- [ ] Agent 调用 `list_tags` → 返回 28 个标签
- [ ] Agent 调用 `search_indicators` 搜 `AI产业链` → 返回 39 个指标
- [ ] `curl http://localhost:8000/api/v1/tags` → 返回标签列表
- [ ] `curl "http://localhost:8000/api/v1/indicators?tag=数据中心"` → 11 个数据中心指标
- [ ] `curl "http://localhost:8000/api/v1/indicators?tag=AI产业链"` → 39 个 AI 产业链指标
- [ ] `curl http://localhost:8000/docs` → OpenAPI 交互文档可访问

---

## 常见问题

**Q: FRED API 限流？**
FRED 免费 tier 120 req/min。Pipeline 每次约 80 个 FRED 指标，远低于限额。

**Q: Jin10 数据不更新？**
Eurozone/UK/德国/澳洲/加拿大/瑞士/banks 来自 Jin10 财经日历，上游在 2025 年 8-9 月停止更新。FRED 的对应指标更可靠（如 sovereign_yield 系列）。

**Q: 无 FRED Key 能用吗？**
可以。无 Key 时 229 个非 FRED 指标正常使用（58 US + 21 AI infra 需 FRED）。

**Q: PyPI 下载量超时？**
已切换到 `pypistats` 库（httpx-based），带 3 次重试+退避。

**Q: 如何查看全部数据？**
浏览器打开 `report.html` 或调用 `GET /api/v1/indicators`。
