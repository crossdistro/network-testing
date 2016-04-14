#!/usr/bin/env python
# -*- coding: utf-8 -*-

from distutils.core import setup

setup(
    name='network-testing',
    version='0.0.1',
    description='Network application test framework and tests.',
    author='Pavel Šimerda',
    author_email='pavlix@pavlix.net',
    url='https://github.com/pavlix/network-testing',
    packages=['network_testing'],
    scripts=['test-client-server', 'test-client-server-genhtml'],
    package_data={'network_testing': ['data/hosts', 'data/testcases/*/*/*', 'data/report/templates/*', 'data/report/static_data/*']},
)
