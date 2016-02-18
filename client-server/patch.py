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

class Timeout(Exception):
    pass

@patch(ptrace.debugger.PtraceDebugger)
def _wait_event(orig, self, wanted_pid, blocking=True):
    if wanted_pid is not None:
        return self._wait_event_pid(wanted_pid, blocking)

    pause = 0.001
    while True:
        for pid in tuple(self.dict):
            process = self._wait_event_pid(pid, False)
            if process is not None:
                return process
        if not blocking:
            return None
        pause = min(pause * 2, 0.5)
        if self.deadline is not None:
            shift = self.deadline - time.time()
            if shift > 0:
                pause = min(pause, shift)
            else:
                raise Timeout()
        time.sleep(pause)
