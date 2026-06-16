"""
AI Infrastructure Harness — monitor the full AI supply chain via FRED.

Covers the AI infrastructure buildout from raw materials to cloud services:
  Raw Materials  → copper, uranium, lithium
  Semiconductors → SOX index, semiconductor industrial production, PPI
  Hardware       → PCB production, computer orders, storage, networking
  Data Centers   → Kelly DC index, cloud index, DC employment, fab construction
  Power/Energy   → nuclear generation, total generation, electricity price, gas PPI
  AI/Market      → AI & robotics index, Nasdaq tech sector

All data sourced from FRED (Federal Reserve Economic Data).
Requires FRED_API_KEY.
"""

from __future__ import annotations

import pandas as pd


class AIInfraHarness:
    """AI infrastructure supply chain indicators via FRED."""

    def __init__(self, fred_api_key: str = ""):
        self._fred_key = fred_api_key
        self._fred = None

    def _init_fred(self):
        if self._fred is None:
            from fredapi import Fred
            self._fred = Fred(api_key=self._fred_key)

    def _get_fred(self, code: str, start: str = None, end: str = None):
        self._init_fred()
        kwargs = {}
        if start:
            kwargs["observation_start"] = start
        if end:
            kwargs["observation_end"] = end
        s = self._fred.get_series(code, **kwargs)
        return s.reset_index().pipe(
            lambda df: df.rename(columns={"index": "date", 0: "value"})
        )

    # ── Semiconductor & Chip ──────────────────────────────────

    def sox_index(self):
        """PHLX Semiconductor Index — daily. Leading indicator for tech/economic cycle."""
        return self._get_fred("NASDAQSOX")

    def ip_semiconductor(self):
        """Industrial Production: Semiconductor & Electronic Components (monthly, index)."""
        return self._get_fred("IPG3344S")

    def ppi_semiconductor(self):
        """PPI: Semiconductor & Electronic Component Manufacturing (monthly, index)."""
        return self._get_fred("PCU33443344")

    def computer_electronics_orders(self):
        """Manufacturers' New Orders: Computers & Electronic Products (monthly, USD mn).
        Leading indicator — new orders precede actual production/shipments by 3-6 months."""
        return self._get_fred("A34SNO")

    # ── Hardware Components ───────────────────────────────────

    def pcb_production(self):
        """Industrial Production: Semiconductors, PCB & Other Electronic Components
        (monthly, index). Tracks bare PCB + loaded PCB assembly output."""
        return self._get_fred("IPB53122S")

    def computer_storage_ppi(self):
        """PPI: Computer Storage Device Manufacturing (monthly, index).
        Covers HDD, SSD, and other storage devices."""
        return self._get_fred("PCU334112334112")

    def data_networking_equipment_ppi(self):
        """PPI: Telephone & Wireline Data Networking Equipment (monthly, index).
        Routers, switches, and other networking hardware."""
        return self._get_fred("WPU117601")

    def power_transformer_ppi(self):
        """PPI: Electric Power & Specialty Transformer Manufacturing (monthly, index).
        Key data center power infrastructure component."""
        return self._get_fred("PCU335311335311")

    # ── Data Center & Cloud ───────────────────────────────────

    def kelly_data_center_index(self):
        """Kelly Data Center & Technology Infrastructure Index — daily.
        Tracks publicly traded companies in data center and tech infrastructure."""
        return self._get_fred("NASDAQSRVRSCPR")

    def cloud_computing_index(self):
        """ISE Cloud Computing Index — daily.
        Tracks cloud computing companies (IaaS, PaaS, SaaS providers)."""
        return self._get_fred("NASDAQCPQ")

    def data_processing_employment(self):
        """All Employees: Data Processing, Hosting & Related Services (monthly, thousands).
        Direct measure of data center workforce growth."""
        return self._get_fred("CES5051800001")

    def manufacturing_construction(self):
        """Total Construction Spending: Manufacturing (monthly, USD mn).
        Proxy for chip fab and data center construction spending (CHIPS Act buildout)."""
        return self._get_fred("TLMFGCONS")

    # ── AI & Technology Market ────────────────────────────────

    def ai_robotics_index(self):
        """Nasdaq AI & Robotics Index — daily.
        Tracks companies in artificial intelligence and robotics sectors."""
        return self._get_fred("NASDAQNQROBO")

    def nasdaq_tech_sector(self):
        """Nasdaq-100 Technology Sector Index — daily.
        Broad technology sector performance."""
        return self._get_fred("NASDAQNDXT")

    # ── Power & Energy ────────────────────────────────────────

    def nuclear_generation(self):
        """Industrial Production: Nuclear Electric Power Generation (monthly, index).
        Nuclear power is the primary zero-carbon baseload for data centers."""
        return self._get_fred("IPN221113S")

    def electric_power_generation(self):
        """Industrial Production: Electric Power Generation, Transmission & Distribution
        (monthly, index). Total US electricity system output."""
        return self._get_fred("IPG2211S")

    def electricity_price(self):
        """Average Price: Electricity per Kilowatt-Hour (monthly, USD).
        US city average retail electricity price."""
        return self._get_fred("APU000072610")

    def natural_gas_electric_ppi(self):
        """PPI: Natural Gas to Electric Power (monthly, index).
        Natural gas is the marginal fuel for US power generation."""
        return self._get_fred("WPS0554")

    # ── Raw Materials ─────────────────────────────────────────

    def uranium_price(self):
        """Global Price of Uranium (monthly, USD).
        Nuclear fuel — SMR (small modular reactor) narrative for data centers."""
        return self._get_fred("PURANUSDM")

    def copper_price(self):
        """Global Price of Copper (monthly, USD).
        Essential for power cables, transformers, data center electrical infrastructure."""
        return self._get_fred("PCOPPUSDM")

    def lithium_miners_index(self):
        """Sprott Lithium Miners Index — daily.
        Lithium is key for grid-scale battery storage (data center backup power)."""
        return self._get_fred("NASDAQNSLITP")
