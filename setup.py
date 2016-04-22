#!/usr/bin/env python
# -*- coding: utf-8 -*-

from setuptools import setup

setup(
    name='network-testing',
    version='0.0.1',
    description='Network application test framework and tests.',
    author='Pavel Šimerda',
    author_email='pavlix@pavlix.net',
    url='https://github.com/pavlix/network-testing',
    packages=['network_testing'],
    entry_points={
        'console_scripts': [
            'test-client-server = network_testing.client_server:main',
            'test-client-server-genhtml = network_testing.client_server_genhtml:main'
        ]
    },
    package_data={
        'network_testing': [
            'data/hosts',
            'data/testcases/*/*/*',
            'data/report/templates/*',
            'data/report/static_data/*'
            'data/report/example_data/*'
        ]
    },
)
