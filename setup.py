"""
Setup script for Procurement Lighthouse PoC
"""
from setuptools import setup, find_packages

with open("requirements.txt") as f:
    requirements = f.read().splitlines()

# Filter out comments and empty lines
requirements = [req for req in requirements if req and not req.startswith('#')]

setup(
    name="procurement-lighthouse",
    version="1.0.0",
    description="Event-driven procurement control tower PoC for AWS t2.micro",
    packages=find_packages(),
    install_requires=requirements,
    python_requires=">=3.8",
    entry_points={
        'console_scripts': [
            'procurement-lighthouse=procurement_lighthouse.main:main',
        ],
    },
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
    ],
)