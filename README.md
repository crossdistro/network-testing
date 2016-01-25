# fedora-networking

## Fedora networking tests

Dependencies:

 * netresolve-devel (should be fixed to only require a non-devel package)
 * libtool (we should get rid of it)
 * strace

Run individual test (for netresolve):

    cd netns-tests
    sudo ./run netresolve

Run all tests:

    cd netns-tests
    sudo ./run
