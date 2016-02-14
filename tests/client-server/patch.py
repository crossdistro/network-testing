#!/usr/bin/python

from __future__ import print_function

import os, sys, subprocess, errno, signal
import multiprocessing
import collections, functools, itertools
import logging
import time
import argparse
import traceback

import ptrace.debugger
import ptrace.func_call
import ptrace.syscall
import ptrace.binding.func

import logging
log = logging.getLogger()

def patch(ns):
    def _patch(func):
        orig = getattr(ns, func.__name__)
        def new(*args, **kargs):
            return func(orig, *args, **kargs)
        setattr(ns, func.__name__, new)
    return _patch

#
# Patch some standard Python functions
#

@patch(subprocess)
def check_call(orig, *args, **kargs):
    log.debug((args, kargs))
    return orig(*args, **kargs)

#
# Patch python-ptrace on the fly
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

# Change process status formatter to understand exitcode
# correctly.
#@patch(ptrace.process_tools)
def formatProcessStatus(orig, exitcode, title="Process"):
    """
    Format a process status (integer) as a string.
    """
    if exitcode:
        text = "%s exited with code %s" % (title, exitcode)
    else:
        text = "%s exited normally" % title
    return text

# Ignore specific PtraceProcess errors when terminating process.
#import ptrace.debugger.process
@patch(ptrace.debugger.process.PtraceProcess)
def terminate(orig, self, *args, **kargs):
    try:
        return orig(self, *args, **kargs)
    except ptrace.error.PtraceError as error:
        if error.errno == 3:
            log.error("Ptrace exception during 'PtraceProcess.terimate()': {}".format(error))
        else:
            raise

#@patch(ptrace.binding.func)
def ptrace(orig, *args, **kargs):
    log.debug((os.getpid(), orig.__name__, args, kargs))
    return orig(*args, **kargs)
