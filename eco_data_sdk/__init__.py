"""
Eco Data SDK — Python client for the Eco Data API.

Usage:
    from eco_data_sdk import EcoDataClient

    client = EcoDataClient()                          # default: http://localhost:8000
    client = EcoDataClient(base_url="https://...")   # remote

    # List all indicators
    indicators = client.list_indicators()
    indicators = client.list_indicators(source="cn")

    # Get indicator detail
    ind = client.get_indicator(1)

    # Search
    results = client.search("GDP")

    # Query data
    data = client.query_data(3, start="2024-01-01", limit=100)

    # Latest value
    latest = client.latest(3)

    # Trigger refresh
    summary = client.fetch()
    summary = client.fetch(source="cn")

    # Health
    health = client.health()
"""

from eco_data_sdk.client import EcoDataClient
