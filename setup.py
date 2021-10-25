#!/usr/bin/env python3

from setuptools import find_packages, setup

with open("requirements.txt") as requirements:
    requirements = requirements.readlines()

with open("README.md") as f:
    long_description = f.read()

setup(
    name="pulp-ostree",
    version="2.0.0a2",
    description="OSTree plugin for the Pulp Project",
    long_description=long_description,
    long_description_content_type="text/markdown",
    license="GPLv2+",
    author="Pulp Project Developers",
    author_email="pulp-list@redhat.com",
    url="http://www.pulpproject.org",
    python_requires=">=3.8",
    install_requires=requirements,
    include_package_data=True,
    packages=find_packages(exclude=["tests"]),
    classifiers=[
        "License :: OSI Approved :: GNU General Public License v2 or later (GPLv2+)",
        "Operating System :: POSIX :: Linux",
        "Development Status :: 3 - Alpha",
        "Framework :: Django",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
    ],
    entry_points={"pulpcore.plugin": ["pulp_ostree = pulp_ostree:default_app_config"]},
)
