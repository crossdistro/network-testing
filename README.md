# User space networking test suite

## Overview

The network application testing project consinst of an easy to use test
framework for IPv4 and IPv6 features in applications and libraries. It
is based on network namespaces and the `ptrace()` syscall. Each piece
of software is tested in different network configurations and evaluated
for features and bugs.

## Installation

Dependencies:

 * Python 2.7/3.4
 * python-ptrace 0.9 with patches
 * netresolve-compat from git master
 * iproute2 with netns support
 * python-json
 * python-jinja2 (for HTML reports)

You can use the project directly from git. Just clone the repository and
run the tests and generate html reports.

    git clone https://github.com/pavlix/network-testing.git
    cd network-testing
    sudo ./test-client-server
    ./test-client-server-genhtml

Python distutils are supported so that you can easily package the project
for any distribution.

### Fedora and EPEL

There is a Fedora COPR repository for Fedora and EPEL distributions. Just
enable the COPR repository and install the test suite.

    dnf copr enable pavlix/network-testing
    dnf install network-testing

Then install packages required for your desired test and run the test. You
can ask the test driver for the names of the packages required for your
desired test and generate html.

    dnf install `test-client-server --deps ssh`
    test-client-server ssh
    test-client-server-genhtml

Alternatively, you may want to install available packages for all tests. In
case your version of Fedora doesn't provide some of the packages, those
tests would fail. Then you can run all tests and generate html.

    for pkg in `test-client-server --deps`; do dnf -y install $pkg; done
    test-client-server
    test-client-server-genhtml

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

The test should maintain the following properties:

 * The server must run on foreground, accept connections and wait until being killed by the framework.
 * The client must run on foreground, perform a query on the server and exit.
 * No modification of system files. If you perform actions that change
   files e.g. in `/etc` or `/var`, use private copies under `/run/network-testing` instead.
