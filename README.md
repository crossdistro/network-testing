# fedora-networking

## Network testing

Dependencies:

 * Python 2.7 (should be fixed for 3.4)
 * python-ptrace 0.8.1
 * netresolve-devel git master (should be fixed to only require a non-devel package)
 * iproute2 with netns support

### Client and server software tests

In `tests/client-server` directory you can find a test driver `run` and
the testcase subdirectories under `testcases` directory. Each testcase
subdirectory contains a pair of scripts for client and server
processes.

#### Running tests

Run individual test (for netresolve):

    cd tests/client-server
    sudo ./run netresolve

Run all tests:

    cd tests/client-server
    sudo ./run

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
