# -*- coding: utf-8 -*-
from __future__ import print_function

import argparse
import logging
import os

from .test_suite import TestCase, TestSuite, testcase_path


def main():
    if os.geteuid() != 0:
        print("You have to be root to run the test driver. Please use sudo.")
        exit(1)

    parser = argparse.ArgumentParser(description="Test driver for client-server networking applications.")
    parser.add_argument("--debug", "-d", action="store_true", help="Print debug messages.")
    parser.add_argument("--list-testcases", "-l", action="store_true", help="List testcases and scenarios.")
    parser.add_argument("--list-scenarios", action="store_true", help="List testcases and scenarios.")
    parser.add_argument("--deps", action="store_true", help="List dependencies.")
    parser.add_argument("--outdir", default="./json-output/", help="List dependencies.")
    parser.add_argument("testcases", nargs="?")
    parser.add_argument("scenarios", nargs="?")
    options = parser.parse_args()

    if options.debug:
        logging.getLogger().setLevel(logging.DEBUG)

    testcases = options.testcases and options.testcases.split(',')
    scenarios = options.scenarios and options.scenarios.split(',')

    suite = TestSuite(testcases, scenarios)
    if options.list_testcases:
        for testcase in suite.testcases:
            print(testcase.name)
        exit(0)
    elif options.list_scenarios:
        for scenario in TestCase.scenario_classes:
            print(scenario.name)
        exit(0)
    elif options.deps:
        dependencies = set()
        for testcase in suite.testcases:
            try:
                with open(os.path.join(testcase_path, testcase.name, 'deps')) as deps_file:
                    for dependency in deps_file.read().splitlines():
                        if dependency:
                            dependencies.add(dependency)
            except IOError:
                pass
        for dependency in sorted(dependencies):
            print(dependency)
        exit(0)
    else:
        suite.run()
        suite.save(options.outdir)
        suite.report()

    exit(0 if suite.result else 1)

if __name__ == '__main__':
    main()
