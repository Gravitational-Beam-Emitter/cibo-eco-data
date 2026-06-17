# 前端数据看板 — 接口文档 & 构建指南

## API 地址

```
BASE: http://localhost:8000
```

---

## 接口速查（14 个端点全部返回 JSON）

| 端点 | 用途 | 看板用途 |
|---|---|---|
| **宏观数据** | | |
| `GET /api/v1/categories` | 三层分类概览 | 首页分类导航 |
| `GET /api/v1/tags` | 28 个标签及覆盖数 | 分类导航/侧边栏 |
| `GET /api/v1/indicators?tag=` | 按标签筛指标 | 分类页面数据 |
| `GET /api/v1/indicators?source=` | 按数据源筛指标 | 数据源视图 |
| `GET /api/v1/indicators/search?q=` | 关键词搜索 | 搜索框 |
| `GET /api/v1/indicators/{id}` | 单个指标详情 | 指标详情弹窗 |
| `GET /api/v1/data/{id}?start=&end=&limit=` | 时间序列 | 图表渲染 |
| `GET /api/v1/data/{id}/latest` | 最新值 | 卡片数字/KPI |
| **国家风险** | | |
| `GET /api/v1/risk/indicators` | 风险指标列表 | 风险分类页 |
| `GET /api/v1/risk/indicators/{id}` | 风险指标详情 | 指标详情弹窗 |
| `GET /api/v1/risk/data/{id}` | 风险时序数据 | 图表渲染 |
| `GET /api/v1/risk/data/{id}/latest` | 风险最新值 | KPI 卡片 |
| **名称筛查** | | |
| `POST /api/v1/name-screening/search` | 单名称筛查 | 筛查输入框 |
| `POST /api/v1/name-screening/batch` | 批量名称筛查 | 批量筛查上传 |
| `GET /api/v1/name-screening/stats` | 筛查数据库统计 | 状态标识 |
| **系统** | | |
| `GET /api/v1/health` | 健康检查 | 状态标识 |

---

## 响应格式 — 精确 JSON 结构

### `GET /api/v1/tags`

```json
[
  {"tag": "增长",      "count": 57},
  {"tag": "通胀",      "count": 40},
  {"tag": "AI产业链",  "count": 39},
  {"tag": "全球宏观",  "count": 31},
  {"tag": "市场情绪",  "count": 27},
  ...
]
```

### `GET /api/v1/indicators?tag=AI产业链`

```json
[
  {
    "id": 263,
    "source": "ai",
    "name": "SOX Semiconductor Index",
    "method": "sox_index",
    "params": {},
    "description": "PHLX Semiconductor Index (Daily)...",
    "frequency": "daily",
    "last_updated": "2026-06-16T16:01:14",
    "tags": "AI产业链,AI算力,半导体,市场情绪"
  },
  {
    "id": 284,
    "source": "ai_co",
    "name": "NVIDIA Revenue",
    "method": "nvidia_revenue",
    "params": {},
    "description": "NVIDIA quarterly total revenue (USD)...",
    "frequency": "quarterly",
    "last_updated": "2026-06-16T16:01:14",
    "tags": "AI产业链,AI公司财务,AI算力,增长"
  }
  // ... 共 39 个
]
```

字段说明：
- `frequency`: `"daily"` | `"monthly"` | `"quarterly"` | `"annual"` — 选图表时间粒度
- `tags`: 逗号分隔，用于前端二次打标签或交叉筛选
- `params`: 部分指标有参数（如 `{"pkg_key":"dashscope"}`）

### `GET /api/v1/data/284?start=2024-01-01`

```json
{
  "indicator": {
    "id": 284,
    "source": "ai_co",
    "name": "NVIDIA Revenue",
    "method": "nvidia_revenue",
    "params": {},
    "description": "NVIDIA quarterly total revenue (USD)...",
    "frequency": "quarterly",
    "last_updated": "2026-06-16T16:01:14",
    "tags": "AI产业链,AI公司财务,AI算力,增长"
  },
  "count": 9,
  "data": [
    {"date": "2026-04-30", "value": 81615000000.0},
    {"date": "2026-01-31", "value": 68127000000.0},
    {"date": "2025-10-31", "value": 57006000000.0}
    // ... 降序排列（最新在前）
  ]
}
```

`date` 格式：
- daily → `2026-06-16`
- monthly → `2026-05-01`
- quarterly → `2026-04-30`
- annual → `2026-01-01`

### `GET /api/v1/data/284/latest`

```json
{
  "indicator": { /* 同上 */ },
  "latest": {"date": "2026-04-30", "value": 81615000000.0}
}
```

---

## 看板加载策略（减少请求数）

### 首页加载 — 一次性获取结构

```
1. GET /api/v1/tags            → 28 个标签（侧边栏/导航）      1 次请求
2. GET /api/v1/indicators      → 全部 287 个指标元数据（可缓存） 1 次请求
```

全部指标元数据约 150KB JSON，建议前端缓存 5-10 分钟。

### 用户点进分类 — 按需取时间序列

```
GET /api/v1/indicators?tag=AI产业链     → 39 个指标元数据
GET /api/v1/data/263/latest             → 每个指标的 KPI 卡片  ︴并行发
GET /api/v1/data/264/latest             →                       ︴39 个请求
...
// 用户点开某个指标的图表时再拉时间序列
GET /api/v1/data/263?start=2020-01-01   → 完整时间序列
```

如果首页要渲染很多 KPI 卡片，可用 `/data/{id}/latest` 并行请求。一次全部 287 个 `latest` 约需 10-15 秒（串行），建议只拉当前视图内的。

---

## 推荐看板布局

### 第一层：标签分类页（首页）

用 `GET /api/v1/tags` 的数据，每个标签渲染成一张卡片：

```
┌──────────────────────────────────────────────────┐
│  📊 宏观经济数据平台                              │
├──────────┬──────────┬──────────┬─────────────────┤
│ 增长     │ 通胀     │ AI产业链 │ 全球宏观         │
│  57      │  40      │  39      │  31              │
├──────────┼──────────┼──────────┼─────────────────┤
│ 市场情绪 │ AI算力   │ 债券     │ 货币政策         │
│  27      │  26      │  25      │  24              │
├──────────┼──────────┼──────────┼─────────────────┤
│ ...      │          │          │                  │
└──────────────────────────────────────────────────┘
```

每张卡片可加一行**子标签**辅助说明（AI产业链 → 半导体/数据中心/电力）。

### 第二层：分类详情页

点击 "AI产业链" 进入：

```
┌─ 面包屑：首页 > AI产业链 (39 个指标) ─────────────┐
│                                                    │
│  [增长率] [时间序列]  [数据源]  ▼排序              │
│                                                    │
│ ┌ SOX Semiconductor Index ─────────────────────┐   │
│ │ tags: AI算力,半导体,市场情绪                  │   │
│ │ daily  ·  FRED   ·  最新: 4,521.3  (↑2.3%)  │   │
│ │ ┌──────────────────────────────────┐         │   │
│ │ │  ████████████████░░░░░░░░░░░░░░░ │ ← 迷你图 │   │
│ │ └──────────────────────────────────┘         │   │
│ └──────────────────────────────────────────────┘   │
│                                                    │
│ ┌ NVIDIA Revenue ──────────────────────────────┐   │
│ │ tags: AI公司财务,AI算力,增长                   │   │
│ │ quarterly · Yahoo Finance · 最新: $81.6B      │   │
│ │ ┌──────────────────────────────────┐         │   │
│ │ │  ██████████████████████████░░░░░ │         │   │
│ │ └──────────────────────────────────┘         │   │
│ └──────────────────────────────────────────────┘   │
│                                                    │
│  ... 分页 (每页 20 个)                              │
└────────────────────────────────────────────────────┘
```

### 第三层：指标详情 + 大图

点击单个指标展开：

```
┌─ 面包屑：首页 > AI产业链 > NVIDIA Revenue ─────────┐
│                                                     │
│ NVIDIA Revenue                                      │
│ NVIDIA 季度总收入 (USD)                              │
│ 数据源: Yahoo Finance  ·  频率: quarterly            │
│ 标签: AI产业链 AI公司财务 AI算力 增长                  │
│                                                     │
│ 最新: $81.6B (2026 Q1)    YoY: +85.2%               │
│                                                     │
│ ┌─────────────────────────────────────────────────┐ │
│ │  $81.6B                                     ┌──┐│ │
│ │                                              │  ││ │
│ │  $60B  ┤          ████                       │  ││ │
│ │        ┤        ████  ██                      │选││ │
│ │  $40B  ┤      ████    █████                   │时││ │
│ │        ┤    ██████    ████████                 │间││ │
│ │  $20B  ┤  ██████      ██████████               │范││ │
│ │        ┤ ██                                    │围││ │
│ │       └──┴──┴──┴──┴──┴──┴──┴──┴──             │  ││ │
│ │        2022  2023  2024  2025  2026            └──┘│ │
│ └─────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────┘
```

---

## 标签层级设计（给 UI 的建议）

28 个标签可以分为两组呈现：

**跨领域标签**（可出现在任意指标上，用于交叉筛选）：
`增长` `通胀` `市场情绪` `货币政策` `利率` `汇率` `贸易`

**主题标签**（专属某个领域，用于主导航）：
```
AI产业链 ─┬─ AI算力
          ├─ 数据中心
          ├─ 半导体
          ├─ AI公司财务
          └─ 能源电力

金融类   ─┬─ 债券
          ├─ 央行利率
          ├─ 信用利差
          ├─ 资金流向
          └─ DeFi

实体类   ─┬─ 就业
          ├─ 房地产
          ├─ 原材料
          ├─ 航运
          └─ 期货

综合类   ─┬─ 全球宏观
          ├─ LLM生态
          ├─ 金融条件
          ├─ 预测市场
          └─ 风险情绪
```

可以在侧边栏用这种层级展示。

---

## 搜索实现

```
GET /api/v1/indicators/search?q=GDP
```

返回匹配的指标列表（搜名称、描述、标签、数据源），直接渲染成结果列表，每条可展开到详情页。

---

## 数据刷新按钮

```bash
# 全部刷新
curl -X POST http://localhost:8000/api/v1/fetch
# 只刷新某个数据源
curl -X POST "http://localhost:8000/api/v1/fetch?source=cn"
```

看板上放一个「刷新数据」按钮，POST 后轮询 `/api/v1/health` 观察 `last_updated` 变化即可。

---

## 快速原型 — 最简 HTML 验证

```html
<!DOCTYPE html>
<html>
<head><title>Eco Data</title></head>
<body>
<div id="app"></div>
<script>
// 验证数据通不通 — 打开浏览器控制台看
fetch('http://localhost:8000/api/v1/tags')
  .then(r => r.json())
  .then(tags => {
    console.log('Tags loaded:', tags.length);
    document.getElementById('app').innerHTML =
      tags.map(t => `<div style="display:inline-block;margin:8px;padding:12px;border:1px solid #ccc;border-radius:8px">
        <strong>${t.tag}</strong><br>${t.count}
      </div>`).join('');
  });
</script>
</body>
</html>
```

复制这段保存为 `dashboard.html`，双击打开即可验证数据联通。
