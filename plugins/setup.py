#!/usr/bin/env python2

from setuptools import setup, find_packages


setup(
    name='pulp_ostree_plugins',
    version='1.1.0b8',
    packages=find_packages(exclude=['test', 'test.*']),
    url='http://www.pulpproject.org',
    license='GPLv2+',
    author='Pulp Team',
    author_email='pulp-list@redhat.com',
    description='plugins for ostree support in pulp',
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
