#!/usr/bin/python

import os
import time

import ptrace.debugger

def patch(ns):
    def _patch(func):
        orig = getattr(ns, func.__name__)
        def new(*args, **kargs):
            return func(orig, *args, **kargs)
        setattr(ns, func.__name__, new)
    return _patch

#
# Patch python-ptrace
#

# Change execve/execv to execvpe/execvp so that executed programs
# are found easily.
@patch(ptrace.debugger.child)
def _execChild(orig, arguments, no_stdout, env):
    if no_stdout:
        try:
            null = open(devnull, 'wb')
            os.dup2(null.fileno(), 1)
            os.dup2(1, 2)
            null.close()
        except IOError as err:
            os.close(2)
            os.close(1)
    try:
        if env is not None:
            os.execvpe(arguments[0], arguments, env)
        else:
            os.execvp(arguments[0], arguments)
    except Exception as err:
        raise ptrace.debugger.child.ChildError(str(err))
