"""
LLM Ecosystem Metrics — proxy indicators for AI industry activity.

Tracks publicly available metrics as proxies for LLM adoption & usage:
  - GitHub stars: developer mindshare (daily)
  - HuggingFace model downloads: model adoption velocity (daily snapshots)
  - PyPI SDK downloads: developer usage volume (monthly)

These are PROXIES, not direct token counts. No LLM company publishes
token consumption publicly. The metrics track ecosystem growth velocity.

Update frequency: daily snapshots recommended — deltas reveal trends.
"""

from __future__ import annotations

import pandas as pd
import requests
from datetime import date


class LLMMetricsHarness:
    """LLM ecosystem metrics — GitHub / HuggingFace / PyPI proxies."""

    # Key LLM repos: China vs US
    GITHUB_REPOS = {
        # US / Global
        "openai-python": "openai/openai-python",
        "anthropic-sdk": "anthropics/anthropic-sdk-python",
        "gemini-sdk": "google-gemini/generative-ai-python",
        "llama": "meta-llama/llama",
        "mistral": "mistralai/mistral-inference",
        # China
        "deepseek": "deepseek-ai/DeepSeek-V3",
        "qwen": "QwenLM/Qwen",
        "chatglm": "THUDM/ChatGLM-6B",
        "yi": "01-ai/Yi",
    }

    # HuggingFace model IDs for download tracking
    HF_MODELS = {
        # US
        "llama-3.1-405b": "meta-llama/Meta-Llama-3.1-405B",
        "mistral-large": "mistralai/Mistral-Large-Instruct-2411",
        # China
        "deepseek-v3": "deepseek-ai/DeepSeek-V3",
        "qwen2.5-72b": "Qwen/Qwen2.5-72B-Instruct",
        "yi-1.5-34b": "01-ai/Yi-1.5-34B-Chat",
    }

    # PyPI packages for LLM SDKs
    PYPI_PACKAGES = {
        "openai": "openai",
        "anthropic": "anthropic",
        "google-genai": "google-genai",
        "dashscope": "dashscope",       # Alibaba Qwen SDK
        "zhipuai": "zhipuai",           # Zhipu GLM SDK
    }

    def __init__(self):
        self._gh_session = requests.Session()
        self._gh_session.headers.update({
            'Accept': 'application/vnd.github.v3+json',
            'User-Agent': 'eco-data-platform',
        })

    # -- GitHub Stars (daily) --

    def github_stars(self):
        """Fetch current GitHub star counts for all tracked LLM repos.
        Returns DataFrame with date=snapshot_date, value=stars, and code=repo_key."""
        records = []
        today = str(date.today())
        for key, repo in self.GITHUB_REPOS.items():
            try:
                resp = self._gh_session.get(
                    f'https://api.github.com/repos/{repo}', timeout=15
                )
                if resp.ok:
                    d = resp.json()
                    records.append({
                        "code": key,
                        "date": today,
                        "value": d.get("stargazers_count", 0),
                    })
            except Exception:
                continue
        return pd.DataFrame(records)

    def github_stars_single(self, repo_key: str):
        """Fetch stars for a single repo. repo_key like 'deepseek', 'openai-python'."""
        repo = self.GITHUB_REPOS.get(repo_key)
        if not repo:
            return pd.DataFrame(columns=["date", "value"])
        try:
            resp = self._gh_session.get(
                f'https://api.github.com/repos/{repo}', timeout=15
            )
            if resp.ok:
                d = resp.json()
                return pd.DataFrame([{
                    "date": str(date.today()),
                    "value": d.get("stargazers_count", 0),
                }])
        except Exception:
            pass
        return pd.DataFrame(columns=["date", "value"])

    # -- HuggingFace Downloads (daily snapshot → deltas) --

    def hf_downloads(self):
        """Fetch cumulative HF downloads. Delta = daily adoption velocity."""
        records = []
        today = str(date.today())
        for key, model_id in self.HF_MODELS.items():
            try:
                resp = requests.get(
                    f'https://huggingface.co/api/models/{model_id}', timeout=15
                )
                if resp.ok:
                    d = resp.json()
                    records.append({
                        "code": key,
                        "date": today,
                        "value": d.get("downloads", 0),
                    })
            except Exception:
                continue
        return pd.DataFrame(records)

    def hf_downloads_single(self, model_key: str):
        """Fetch downloads for a single model."""
        model_id = self.HF_MODELS.get(model_key)
        if not model_id:
            return pd.DataFrame(columns=["date", "value"])
        try:
            resp = requests.get(
                f'https://huggingface.co/api/models/{model_id}', timeout=15
            )
            if resp.ok:
                d = resp.json()
                return pd.DataFrame([{
                    "date": str(date.today()),
                    "value": d.get("downloads", 0),
                }])
        except Exception:
            pass
        return pd.DataFrame(columns=["date", "value"])

    # -- PyPI Downloads (monthly) --

    @staticmethod
    def _fetch_pypi_downloads(pkg: str) -> int:
        """Fetch last-month downloads for a PyPI package with retry+backoff."""
        import json, time as _time
        from pypistats import recent
        for attempt in range(3):
            try:
                raw = recent(pkg, period='month', format='json')
                data = json.loads(raw).get("data", {})
                return data.get("last_month", 0)
            except Exception:
                if attempt < 2:
                    _time.sleep(10 * (attempt + 1))  # 10s, 20s backoff
        return 0

    def pypi_downloads(self):
        """Fetch PyPI monthly download counts for LLM SDK packages.
        Uses pypistats library (httpx-based, works around LibreSSL issue)."""
        import time as _time
        records = []
        try:
            from pypistats import recent  # noqa: F401 — check import works
        except ImportError:
            print("[LLMMetrics] pypistats not installed — pip install pypistats")
            return pd.DataFrame(columns=["date", "code", "value"])
        for key, pkg in self.PYPI_PACKAGES.items():
            try:
                downloads = self._fetch_pypi_downloads(pkg)
                records.append({
                    "code": key,
                    "date": str(date.today()),
                    "value": downloads,
                })
                _time.sleep(10)  # Respect rate limits
            except Exception:
                continue
        return pd.DataFrame(records)

    def pypi_downloads_single(self, pkg_key: str):
        """Fetch PyPI downloads for a single package."""
        pkg = self.PYPI_PACKAGES.get(pkg_key)
        if not pkg:
            return pd.DataFrame(columns=["date", "value"])
        try:
            from pypistats import recent  # noqa: F401
            downloads = self._fetch_pypi_downloads(pkg)
            return pd.DataFrame([{
                "date": str(date.today()),
                "value": downloads,
            }])
        except ImportError:
            print("[LLMMetrics] pypistats not installed — pip install pypistats")
        except Exception:
            pass
        return pd.DataFrame(columns=["date", "value"])

    # -- Google Trends (search interest) --
    # Note: Google Trends API has rate limits. pytrends library can do this.
    # The data is normalized 0-100 relative to peak, making it good for comparison.

    def google_trends_llm(self):
        """Fetch Google Trends for LLM search terms.
        Requires: pip install pytrends
        Note: Google may block automated requests — use sparingly."""
        try:
            from pytrends.request import TrendReq
            pytrends = TrendReq(hl='en-US', tz=360)
            kw_list = ['ChatGPT', 'Claude AI', 'Gemini AI', 'DeepSeek', 'Qwen AI']
            pytrends.build_payload(kw_list, timeframe='today 3-m')
            df = pytrends.interest_over_time()
            if df.empty:
                return pd.DataFrame(columns=["date", "code", "value"])
            # Convert wide format to long
            records = []
            for idx, row in df.iterrows():
                for col in df.columns:
                    if col != 'isPartial':
                        records.append({
                            "date": str(idx.date()),
                            "code": col.lower().replace(' ', '_'),
                            "value": row[col],
                        })
            return pd.DataFrame(records)
        except ImportError:
            print("[LLMMetrics] pytrends not installed — pip install pytrends")
            return pd.DataFrame(columns=["date", "code", "value"])
        except Exception as e:
            print(f"[LLMMetrics] Google Trends error: {e}")
            return pd.DataFrame(columns=["date", "code", "value"])
