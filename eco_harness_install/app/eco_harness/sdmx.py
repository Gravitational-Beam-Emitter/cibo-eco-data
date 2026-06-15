"""
SDMX Harness — OECD + ECB via opensdmx.

Data limits: SDMX endpoints are public, no key. Rate varies by provider.
opensdmx caches in SQLite+Parquet — first fetch per dataset is slow, replay is instant.
"""


class SDMXHarness:
    """OECD + ECB unified access via SDMX protocol."""

    def __init__(self):
        self._loaded = False

    def _ensure(self):
        if not self._loaded:
            try:
                import opensdmx
                self.opensdmx = opensdmx
                self._loaded = True
            except ImportError:
                print('[SDMXHarness] opensdmx not installed — pip install opensdmx')
                raise

    def oecd(self, dataset: str, **dimensions):
        """Fetch OECD dataset with optional dimension filters.

        Example:
            eh.sdmx.oecd('QNA', country='USA', freq='Q')
        """
        self._ensure()
        self.opensdmx.set_provider('oecd')
        return self.opensdmx.fetch(dataset, **dimensions)

    def ecb(self, dataset: str, **dimensions):
        """Fetch ECB dataset.

        Example:
            eh.sdmx.ecb('EXR', freq='D', currency='USD')
            eh.sdmx.ecb('YC', maturity='10Y')   # yield curve
        """
        self._ensure()
        self.opensdmx.set_provider('ecb')
        return self.opensdmx.fetch(dataset, **dimensions)

    def eurostat(self, dataset: str, **dimensions):
        """Fetch Eurostat dataset."""
        self._ensure()
        self.opensdmx.set_provider('eurostat')
        return self.opensdmx.fetch(dataset, **dimensions)

    def search(self, query: str, provider: str = 'oecd'):
        """Search datasets in a provider."""
        self._ensure()
        return self.opensdmx.search_dataset(query, provider=provider)
