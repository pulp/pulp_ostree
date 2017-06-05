#!/usr/bin/env python3

from setuptools import setup, find_packages

requirements = [
    'pulpcore-plugin',
    'pulp-ostree-common'
]

setup(
    name='pulp-ostree',
    version='2.0.0a1.dev0',
    packages=find_packages(exclude=['test']),
    url='http://www.pulpproject.org',
    install_requires=requirements,
    license='GPLv2+',
    author='Pulp Team',
    author_email='pulp-list@redhat.com',
    description='Plugin to enable OSTree support in Pulp',
    entry_points={
        'pulp.importers': [
            'importer = pulp_ostree.plugins.importers.web:entry_point',
        ],
        'pulp.distributors': [
            'distributor = pulp_ostree.plugins.distributors.web:entry_point'
        ],
        'pulp.unit_models': [
            'ostree=pulp_ostree.plugins.db.model:Branch'
        ]
    }
)
