# coding: utf-8
from pathlib import Path

from setuptools import find_packages, setup


NAME = "hyperstruck-sdk"
VERSION = "0.1.0"
README = Path(__file__).with_name("README.md")
REQUIRES = ["urllib3 >= 1.15", "six >= 1.10", "certifi", "python-dateutil"]


setup(
    name=NAME,
    version=VERSION,
    description="Python client SDK for the Hyperstruck Core API",
    author_email="support@hyperstruck.com",
    url="https://hyperstruck.com",
    keywords=["Hyperstruck", "SDK", "API client", "AI"],
    license="UNLICENSED",
    install_requires=REQUIRES,
    packages=find_packages(exclude=["test", "test.*"]),
    include_package_data=True,
    long_description=README.read_text(),
    long_description_content_type="text/markdown",
)
