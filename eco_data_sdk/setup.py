from setuptools import setup, find_packages

setup(
    name="eco-data-sdk",
    version="1.0.0",
    description="Python SDK for Eco Data API — unified macroeconomic data access",
    packages=find_packages(),
    install_requires=["requests"],
    python_requires=">=3.8",
)
