from setuptools import setup, find_packages

setup(
    name="bigbang",
    version="0.1.0",
    description="BIG BANG — The Universe Generator. One YAML file. Infinite worlds.",
    packages=find_packages(),
    include_package_data=True,
    package_data={
        "bigbang": ["templates/**/*", "templates/**/.*.j2"],
    },
    install_requires=[
        "PyYAML>=6.0.1",
        "Jinja2>=3.1.4",
        "click>=8.1.7",
    ],
    extras_require={
        "serve": [
            "fastapi>=0.100.0",
            "uvicorn[standard]>=0.23.0",
            "python-multipart>=0.0.6",
        ],
        "studio": [
            "fastapi>=0.100.0",
            "uvicorn[standard]>=0.23.0",
            "python-multipart>=0.0.6",
            "anthropic>=0.40.0",
        ],
        "dev": [
            "pytest>=7.0",
            "httpx2",
        ],
    },
    entry_points={
        "console_scripts": [
            "big-bang=bigbang.cli:cli",
        ],
    },
    python_requires=">=3.10",
)
