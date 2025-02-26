from setuptools import setup, find_packages

setup(
    name="babywise",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "pytest",
        "pytest-asyncio",
        "langchain",
        "langgraph",
        "langchain-core",
    ],
    python_requires=">=3.9",
) 