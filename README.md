# fedora-networking

## Network testing

Dependencies:

 * Python 2.7 (should be fixed for 3.4)
 * python-ptrace 0.8.1
 * netresolve-devel git master (should be fixed to only require a non-devel package)
 * iproute2 with netns support

### Client and server software tests

Test driver for testing client-server applications is located in
`network_testing/client_server.py` and the individual tests are defined in
subdirectories of `testcases/client-server` directory. Each subdirectory
defines one test case consisting of a client script and a server script.

#### Running tests in Git working directory

Run individual test (for netresolve):

    sudo ./test-client-server netresolve

Run all tests:

    sudo ./test-client-server

#### Writing tests

The preferred form of test cases is a pair of short shell scripts that
use `exec` to run the client or server scripts in the same process. But
any form of test is supported including scripts in Python and other
languages. For inspiration look at `netresolve`, `ssh`, `python` and
`python3-asyncio` testcases.

#### Technical details

The test driver is written in Python in order to be reasonably simple
but at the same time have access to all low-level operating system
APIs. It uses the `ptrace()` system call via *python-ptrace* library
to trace the client and server processes. Any subprocesses are traced
as well. The scripts are run in network namespaces configured for
several network configuration scenarios..
