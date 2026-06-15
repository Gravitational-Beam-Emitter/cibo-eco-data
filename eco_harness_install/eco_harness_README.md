# Eco Data API Harness — 安装说明

统一宏观经济数据接入层，封装 FRED / AKShare / World Bank / DBnomics / OECD / ECB / BoJ / EIA 共 10 个数据源为单一 facade。

---

## 快速安装

### 方式 1: Agent 自安装（推荐）

将 `eco_harness_skill.md` 交给任意 Claude Code / AI 编程助手的 agent，让 agent 阅读后自行完成全部安装步骤（创建目录、写入文件、安装依赖、验证、询问 API Key）。Agent 会按 skill 文件中的指令逐步执行。

### 方式 2: 手动安装

```bash
# 1. 安装依赖
pip install fredapi akshare wbgapi dbnomics opensdmx boj-api requests pandas

# 2. 复制 eco_harness/ 目录到目标项目的 app/ 下
cp -r eco_harness/ <target_project>/app/

# 3. 确保 app/__init__.py 存在（可为空文件）
touch <target_project>/app/__init__.py
```

---

## API Key 配置

| 数据源 | 是否需要 Key | 获取方式 |
|--------|-------------|---------|
| FRED | **需要**（免费） | fred.stlouisfed.org → Register |
| EIA | **需要**（免费） | eia.gov/opendata → Register |
| US Treasury | 不需要 | — |
| AKShare | 不需要 | — |
| World Bank | 不需要 | — |
| DBnomics | 不需要 | — |
| OECD SDMX | 不需要 | — |
| ECB SDMX | 不需要 | — |
| Bank of Japan | 不需要 | — |

**无 Key 时**: `eh.cn.*`、`eh.global_.*`、`eh.sdmx.*`、`eh.jp.*`、`eh.us.treasury_*` 方法均可正常使用。

设置环境变量或在代码中传入：

```python
from app.eco_harness import EcoHarness
eh = EcoHarness(fred_api_key='your_fred_key', eia_api_key='your_eia_key')
```

---

## 验证安装

```python
from app.eco_harness import EcoHarness
eh = EcoHarness()

# 无需 Key 的方法验证
eh.us.treasury_debt_latest()       # 美国国债
eh.cn.cpi()                        # 中国 CPI
eh.global_.population('CHN')       # 中国人口
```

---

## 使用示例

```python
# US (FRED)
eh.us.gdp()              # GDP (Billions, SAAR)
eh.us.cpi()              # CPI (1982-84=100)
eh.us.unemployment()     # Unemployment Rate
eh.us.fed_funds()        # Fed Funds Rate
eh.us.get('T10Y2Y')      # 任意 FRED 序列

# US (Treasury — 无需 Key)
eh.us.treasury_debt_latest()
eh.us.treasury_rates_of_exchange('China')

# China (AKShare)
eh.cn.gdp()              # GDP (亿元)
eh.cn.pmi()              # 制造业 PMI
eh.cn.m2()               # M2
eh.cn.lpr()              # LPR

# Global
eh.global_.gdp('CHN')
eh.global_.gdp_growth('CHN')
eh.global_.dbnomics('OECD', 'MEI', 'USA.B6BLTT01.CXCUSA.Q')

# SDMX
eh.sdmx.oecd('QNA', country='USA', freq='Q')
eh.sdmx.ecb('EXR', freq='D', currency='USD')

# Japan
eh.jp.fx('USDJPY')
eh.jp.tankan()

# Energy (需要 EIA Key)
eh.energy.crude_price()
eh.energy.natural_gas_price()
```

---

## 文件结构

```
eco_harness/
├── __init__.py      # EcoHarness facade (统一入口)
├── us.py            # US: FRED + Treasury
├── cn.py            # China: AKShare
├── global_.py       # Global: World Bank + DBnomics
├── sdmx.py          # OECD + ECB + Eurostat (SDMX)
├── jp.py            # Bank of Japan
└── energy.py        # EIA Energy Data
```

所有方法返回标准化 `pd.DataFrame`（`date` + `value` 列，按日期升序，无 NaN）。
