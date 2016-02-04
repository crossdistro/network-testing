# fedora-networking

## Fedora networking tests

Dependencies:

 * Python 2.7
 * python-ptrace
 * netresolve-devel (should be fixed to only require a non-devel package)
 * iproute2

Run individual test (for netresolve):

    cd tests/client-server
    sudo ./run netresolve

Run all tests:

    cd tests/client-server
    sudo ./run
