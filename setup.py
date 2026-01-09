"""Setup script for REACH Code Visualizer."""

from setuptools import setup, find_packages

setup(
    name="reach-code-visualizer",
    version="0.1.0",
    description="Code analysis and visualization tool for the REACH game project",
    author="REACH Development Team",
    python_requires=">=3.10",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    install_requires=[
        "flask>=3.0.0",
        "flask-socketio>=5.3.0",
        "watchdog>=3.0.0",
        "networkx>=3.2.1",
        "pyyaml>=6.0.1",
        "regex>=2023.12.25",
        "python-dotenv>=1.0.0",
        "click>=8.1.7",
        "rich>=13.7.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.4.4",
        ]
    },
    entry_points={
        "console_scripts": [
            "reach-viz=cli:cli",
        ]
    },
)
