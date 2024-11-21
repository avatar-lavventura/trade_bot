#!/usr/bin/python3

from setuptools import find_packages, setup

with open("README.org", "r") as fh:
    long_description = fh.read()

with open("requirements.txt", "r") as f:
    requirements = list(map(str.strip, f.read().split("\n")))[:-1]

setup(
    name="bot",
    packages=find_packages(),
    setup_requires=["wheel", "ccxt", "ipdb", "rich"],
    version="2.0.1",  # don't change this manually, use bumpversion instead
    license="MIT",
    description="Alpy trade bot.",  # noqa: E501
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="Alper Alimoglu",
    author_email="alper.alimoglu@gmail.com",
    keywords=["trading", "bot"],
    install_requires=requirements,
    include_package_data=True,
    python_requires=">=3.9,<4",
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Build Tools",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
    ],
)
