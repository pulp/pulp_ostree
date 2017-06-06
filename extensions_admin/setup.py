from setuptools import setup, find_packages

requirements = [
    'pulp-ostree-common'
]

setup(
    name='pulp-ostree-cli',
    version='2.0.0a1.dev0',
    packages=find_packages(exclude=['test']),
    url='http://www.pulpproject.org',
    install_requires=requirements,
    license='GPLv2+',
    author='Pulp Team',
    author_email='pulp-list@redhat.com',
    description='pulp-admin extensions for OSTree image support',
    entry_points={
        'pulp.extensions.admin': [
            'repo_admin = pulp_ostree.extensions.admin.pulp_cli:initialize',
        ]
    }
)
