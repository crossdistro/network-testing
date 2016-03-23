# User space networking test suite

## Overview

The network application testing project consinst of an easy to use test
framework for IPv4 and IPv6 features in applications and libraries. It
is based on network namespaces and the `ptrace()` syscall. Each piece
of software is tested in different network configurations and evaluated
for features and bugs.

## Installation

Dependencies:

 * Python 2.7 (going to support for 3.4)
 * python-ptrace 0.8.1
 * netresolve-compat from git master
 * iproute2 with netns support

You can use the project directly from git. Just clone the repository and
run the tests.

    git clone https://github.com/pavlix/network-testing.git
    cd network-testing
    make run

Python distutils are supported so that you can easily package the project
for any distribution.

### Fedora and EPEL

There is a Fedora COPR repository for Fedora and EPEL distributions. You
can install `network-testing-deps` to also get all tested packages.

    dnf copr enable pavlix/network-testing
    dnf install network-testing-deps
    test-client-server

Alternatively you can install just the test project and individual
dependencies for individual tests.

    dnf copr enable pavlix/network-testing
    dnf install network-testing openssh
    test-client-server ssh

## Client and server software tests

Test driver for testing client-server applications is located in
`network_testing/client_server.py` and the individual tests are defined in
subdirectories of `testcases/client-server` directory. Each subdirectory
defines one test case consisting of a client script and a server script.

The test driver is written in Python in order to be reasonably simple
but at the same time have access to all low-level operating system
APIs. It uses the `ptrace()` system call via *python-ptrace* library
to trace the client and server processes. Any subprocesses are traced
as well. The scripts are run in network namespaces configured for
several network configuration scenarios..

### Running tests in Git working directory

Run individual test (for netresolve):

    sudo ./test-client-server netresolve

Run all tests:

    sudo ./test-client-server

### Writing tests

The preferred form of test cases is a pair of short shell scripts that
use `exec` to run the client or server scripts in the same process. But
any form of test is supported including scripts in Python and other
languages. For inspiration look at `netresolve`, `ssh`, `python` and
`python3-asyncio` testcases.
