"""Setup configuration for Words - Language Learning Telegram Bot."""

from setuptools import setup, find_packages
from pathlib import Path

# Read the contents of README.md
readme_file = Path(__file__).parent / "README.md"
long_description = readme_file.read_text(encoding="utf-8") if readme_file.exists() else ""

# Read requirements from requirements.txt
requirements_file = Path(__file__).parent / "requirements.txt"
if requirements_file.exists():
    with open(requirements_file, "r", encoding="utf-8") as f:
        requirements = [
            line.strip()
            for line in f
            if line.strip() and not line.startswith("#")
        ]
else:
    requirements = []

setup(
    name="words-bot",
    version="0.1.0",
    author="Words Bot Team",
    description="A Telegram bot for language learning with adaptive spaced repetition",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/words",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    python_requires=">=3.11",
    install_requires=requirements,
    extras_require={
        "dev": [
            "black>=24.1.1",
            "ruff>=0.2.1",
            "mypy>=1.8.0",
        ],
        "test": [
            "pytest>=7.0.0,<8.0.0",
            "pytest-asyncio>=0.23.4",
            "pytest-cov>=4.1.0",
            "pytest-mock>=3.12.0",
            "faker>=22.6.0",
        ],
    },
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Education",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Framework :: AsyncIO",
        "Topic :: Education",
    ],
    entry_points={
        "console_scripts": [
            "words-bot=words.__main__:main",
        ],
    },
    include_package_data=True,
    zip_safe=False,
)
