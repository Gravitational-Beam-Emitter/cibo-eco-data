# Eco Data 使用指南 — 给外部项目/Claude 的快速上手

## 你不需要了解 287 个指标

你只需要掌握**一个 4 步流程**，每次都能精准找到你需要的数据。

---

## 用前确认：服务在跑

```bash
curl http://localhost:8000/api/v1/health
# → {"status":"ok","indicators":287,...}
```

---

## 4 步找到任何数据

### 第 1 步：看有什么标签（了解全局）

```bash
curl http://localhost:8000/api/v1/tags
```

返回 28 个中文标签，每人看一遍就知道这个平台有什么：
```
增长(57)  通胀(40)  AI产业链(39)  全球宏观(31)  市场情绪(27)
AI算力(26)  债券(25)  货币政策(24)  利率(24)  LLM生态(19)
AI公司财务(17)  央行利率(16)  原材料(16)  就业(13)  汇率(12)
能源电力(12)  数据中心(11)  贸易(10)  房地产(10)  ...
```

不需要记关键词，看标签就能定位。

### 第 2 步：按标签筛选

```bash
# 一次性拿到某个主题的全部指标
curl "http://localhost:8000/api/v1/indicators?tag=AI产业链"
# → 39 个 AI 产业链指标（含名称、描述、频率、数据源）

curl "http://localhost:8000/api/v1/indicators?tag=通胀"
# → 40 个通胀相关指标

curl "http://localhost:8000/api/v1/indicators?tag=数据中心"
# → 11 个数据中心指标
```

### 第 3 步：按关键词搜（当你已有具体想法）

```bash
curl "http://localhost:8000/api/v1/indicators/search?q=GDP"
# 搜名称、描述、标签，返回匹配的指标列表
```

### 第 4 步：取时间序列

```bash
curl "http://localhost:8000/api/v1/data/261?start=2024-01-01"
# → {indicator:"NVIDIA Revenue", data:[{date,value},...]}

curl "http://localhost:8000/api/v1/data/261/latest"
# → 最新值
```

---

## 常见场景速查

### 场景：我要看美国经济

```bash
# 列出所有美国指标
curl "http://localhost:8000/api/v1/indicators?source=us"
# → 58 个 FRED 指标：GDP、CPI、失业率、利率、信用利差...

# 或者按标签缩小范围
curl "http://localhost:8000/api/v1/indicators?tag=通胀"
curl "http://localhost:8000/api/v1/indicators?tag=就业"
curl "http://localhost:8000/api/v1/indicators?tag=货币政策"
```

### 场景：我要看中国/全球经济

```bash
curl "http://localhost:8000/api/v1/indicators?source=cn"      # 中国 32
curl "http://localhost:8000/api/v1/indicators?source=global_"  # 全球 31
```

### 场景：我要看 AI 产业景气度

```bash
curl "http://localhost:8000/api/v1/indicators?tag=AI产业链"
# 39 个指标覆盖全链：半导体 → 数据中心 → 电力 → AI 公司财务

# 子主题：
curl "http://localhost:8000/api/v1/indicators?tag=AI算力"    # 26
curl "http://localhost:8000/api/v1/indicators?tag=数据中心"   # 11
curl "http://localhost:8000/api/v1/indicators?tag=半导体"     # 8
curl "http://localhost:8000/api/v1/indicators?tag=能源电力"   # 12
```

### 场景：我要看 LLM 开源生态热度

```bash
curl "http://localhost:8000/api/v1/indicators?tag=LLM生态"
# GitHub Stars、HuggingFace 下载量、PyPI SDK 下载量
```

### 场景：我要看 DeFi/链上

```bash
curl "http://localhost:8000/api/v1/indicators?source=defi"
# Polymarket 交易量、DEX TVL、RWA 规模...
```

### 场景：我要做 AML/CFT 合规风险评估

```bash
# 列出所有风险指标（AML + 制裁 + CPI）
curl "http://localhost:8000/api/v1/risk/indicators"

# 只看 AML 评级
curl "http://localhost:8000/api/v1/risk/indicators?source=aml"

# 获取 FATF 黑/灰名单历史趋势
curl "http://localhost:8000/api/v1/risk/data/{id}"

# 获取 TI 腐败感知指数最新评分
curl "http://localhost:8000/api/v1/risk/data/{id}/latest"
```

### 场景：我要筛查客户是否在制裁/PEP 名单中

```bash
# 中文名筛查
curl -X POST "http://localhost:8000/api/v1/name-screening/search" \
  -H "Content-Type: application/json" \
  -d '{"query":"习近平","include_news":false}'

# 英文名筛查
curl -X POST "http://localhost:8000/api/v1/name-screening/search" \
  -H "Content-Type: application/json" \
  -d '{"query":"Xi Jinping","include_news":false}'

# 批量筛查
curl -X POST "http://localhost:8000/api/v1/name-screening/batch" \
  -H "Content-Type: application/json" \
  -d '{"queries":["习近平","李克强","汪洋"]}'

# 查看数据库统计
curl "http://localhost:8000/api/v1/name-screening/stats"
```

---

## 如果用 MCP（Claude Code 直接调）

12 个工具，流程完全一样：

```
# 数据浏览
1. data_sources_by_category → 三层分类一览（宏观/风险/筛查）
2. list_tags                → 28 个标签一览
3. list_indicators?tag=XX   → 按标签拿指标列表
4. search_indicators?q=XX   → 关键词搜
5. query_data?id=XX         → 取时间序列
6. get_latest?id=XX         → 取最新值

# 风险合规
7. list_risk_indicators     → 列出 AML/制裁/CPI 指标
8. search_name?q=习近平     → 筛查制裁/PEP名单（中英文）
9. name_screening_stats     → 筛查数据库统计
```

---

## 如果用 Python SDK

```python
from eco_data_sdk import EcoDataClient

client = EcoDataClient("http://localhost:8000")

# 分类浏览
categories = client.list_categories()         # 三层分类概览

# 宏观数据浏览
tags = client.list_tags()                    # 28 个标签
ai_indicators = client.query_by_tag("AI产业链")  # 39 个 AI 指标
results = client.search("GDP")               # 关键词搜索

# 取数
data = client.query_data(261, start="2024-01-01")  # 时间序列
latest = client.latest(261)                        # 最新值

# 国家风险
risk_indicators = client.list_risk_indicators()    # AML、制裁、CPI 指标
risk_data = client.query_risk_data(id, start="2020-01-01")
risk_latest = client.risk_latest(id)

# 名称筛查
result = client.screen_name("习近平")              # 单名称筛查
batch = client.screen_name_batch(["习近平","特朗普"])  # 批量筛查
stats = client.name_screening_stats()              # 数据库统计

# 刷新
client.fetch(source="cn")  # 更新中国宏观数据
client.risk_fetch()        # 更新风险数据
```

---

## 核心原则

**不要试图记住 287 个指标。通过标签浏览，一次只关注你当前需要的主题。**

每个指标都有中英文描述，`get_indicator(id)` 可以看到完整元数据。
