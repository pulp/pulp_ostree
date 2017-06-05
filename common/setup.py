from setuptools import setup, find_packages

setup(
    name='pulp-ostree-common',
    version='2.0.0a1.dev0',
    packages=find_packages(exclude=['test']),
    url='http://www.pulpproject.org',
    license='GPLv2+',
    author='Pulp Team',
    author_email='pulp-list@redhat.com',
    description='Common code for Pulp\'s OSTree support',
)
