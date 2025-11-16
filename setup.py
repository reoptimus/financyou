"""Setup configuration for time_series_slicer package."""

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

with open("requirements.txt", "r", encoding="utf-8") as fh:
    requirements = [line.strip() for line in fh if line.strip() and not line.startswith("#")]

setup(
    name="time_series_slicer",
    version="0.1.0",
    author="Time Series Slicer Contributors",
    author_email="",
    description="A powerful and flexible Python library for time series slicing and investment portfolio optimization",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/reoptimus/time_series_slicer",
    packages=find_packages(exclude=["tests*", "examples*", "legacy*", "docs*"]),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Intended Audience :: Science/Research",
        "Intended Audience :: Financial and Insurance Industry",
        "Topic :: Scientific/Engineering",
        "Topic :: Office/Business :: Financial :: Investment",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
    python_requires=">=3.7",
    install_requires=requirements,
    extras_require={
        "dev": [
            "pytest>=6.0.0",
            "pytest-cov>=2.12.0",
            "black>=21.0",
            "flake8>=3.9.0",
            "mypy>=0.910",
        ],
    },
    include_package_data=True,
    zip_safe=False,
    keywords="timeseries time-series data slicing segmentation pandas investment portfolio optimization finance",
    project_urls={
        "Bug Reports": "https://github.com/reoptimus/time_series_slicer/issues",
        "Source": "https://github.com/reoptimus/time_series_slicer",
    },
)
