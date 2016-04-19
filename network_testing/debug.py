import ptrace.debugger
import ptrace.func_call
import ptrace.syscall
import ctypes
import time
import socket

import logging
log = logging.getLogger()

from . import patch

SOCKET_OPERATIONS = set(['bind', 'listen', 'accept', 'connect', 'getsockopt', 'shutdown', 'close'])
PROCESS_SYSCALLS = set(['close', 'execve', 'fork', 'clone'])
TRACED_SYSCALLS = ptrace.syscall.SOCKET_SYSCALL_NAMES | PROCESS_SYSCALLS

class Socket:
    connection_attempted = False

    def __init__(self, fd, domain, socktype, protocol):
        self.events = []
        self.fd = fd
        self.domain = domain
        self.socktype = socktype
        self.protocol = protocol

        log.debug(self)

    def __str__(self):
        return "Socket({fd}/{domain.text}/{socktype.text}/{protocol.text})".format(**vars(self))

    def __repr__(self):
        return repr(str(self))

class Event:
    def __init__(self, syscall_event, time):
        self.process = syscall_event.process
        self.origin = self.process.origin
        self.pid = syscall_event.process.pid
        self.name = syscall_event.name
        self.result = syscall_event.result
        self.arguments = syscall_event.arguments
        self.time = time
        self.__string = "[{time:.3f} {origin} {pid}] {format} = {result}".format(format=syscall_event.format(), **vars(self))

    def __str__(self):
        return self.__string

class Property:
    def __init__(self, arg):
        self.arg = arg

    def __str__(self):
        return self.template.format(**vars(self))

    def __repr__(self):
        return repr(str(self))

class IP4Listening(Property):
    template = "Listening on IPv4: {arg}"

class IP6Listening(Property):
    template = "Listening on IPv6: {arg}"

class IP4Connected(Property):
    template = "Connected using IPv4: {arg}"

class IP6Connected(Property):
    template = "Connected using IPv6: {arg}"

class PreferredFamily(Property):
    template = "Preferred address family is {arg}."

class PreferredLoopbackFamily(PreferredFamily):
    template = "Preferred loopback address family is {family}."

class ParallelConnect(Property):
    template = "Connection method is {method}. {description}"

    def __init__(self, flag):
        if flag:
            self.method = "parallel"
            self.description = "This is a happy eyeballs style dual-stack connection method resulting in fast fallback when the preferred address family fails silently."
        else:
            self.method = "sequential"
            self.description = "This is a classic dual-stack connection method resulting in a significant timeout when the preferred address family fails silently."

class FallbackDelay(Property):
    template = "Fallback delay is {arg:.3f}."

class Timeout(Exception):
    pass

class SyscallDebugger(ptrace.debugger.PtraceDebugger):
    def __init__(self):
        super(SyscallDebugger, self).__init__()

        self.started = time.time()
        self.deadline = None
        self.active_sockets = {}
        self.events = []

        self.traceFork()

    def set_timeout(self, timeout):
        self.deadline = time.time() + timeout
        log.debug("New deadline: {:.3f}".format(self.deadline - self.started))

    def new_child(self, origin, command):
        log.debug("Starting {origin}: {command}".format(**locals()))

        process = self.addProcess(ptrace.debugger.child.createChild(command, False), True)
        process.origin = origin
        process.syscall()

        return process

    def wait(self, script=None, syscall=None):
        while self.dict:
            try:
                process = self.waitSyscall().process
                event = Event(process.syscall_state.event(ptrace.func_call.FunctionCallOptions()), time.time() - self.started)
            except ptrace.debugger.process_event.NewProcessEvent as event:
                process = event.process
                origin = process.origin = process.parent.origin

                log.info("[{}] New process: {}".format(origin, process.pid))

                event.process.parent.syscall()
                process.syscall()
            except ptrace.debugger.process_event.ProcessExit as event:
                process = event.process
                event.origin = process.origin

                log.debug("[{}] Process exited: {} {}".format(event.origin, process.pid, event.exitcode))
                self.add_event(event)

                if process == script:
                    return event
            except ptrace.debugger.ptrace_signal.ProcessSignal as event:
                process = event.process
                origin = process.origin
                log.debug("[{}] Signal received: {} {}".format(origin, process.pid, event.signum))

                process.syscall(event.signum & ~0x80)
            else:
                # Skip entered system calls.
                if event.result is None:
                    process.syscall()
                    continue

                # Handle socket related system calls.
                if event.name in ('socket', 'accept'):
                    if event.name == 'socket':
                        event.socket = Socket(event.result, *event.arguments)
                        event.socket.events.append(event)
                    elif event.name == 'accept':
                        listener = self.active_sockets[event.pid, event.arguments[0].value]
                        event.socket = Socket(event.result, listener.domain, listener.socktype, listener.protocol)
                        event.socket.events.append(event)
                    if event.socket.fd >= 0:
                        self.active_sockets[event.pid, event.socket.fd] = event.socket
                elif event.name == 'close':
                    event.socket = self.active_sockets.pop((event.pid, event.arguments[0].value), None)
                    if event.socket:
                        event.socket.events.append(event)
                    if not event.socket:
                        process.syscall()
                        continue
                elif event.name in SOCKET_OPERATIONS:
                    event.socket = self.active_sockets.get((event.pid, event.arguments[0].value))
                    if event.socket:
                        event.socket.events.append(event)

                # Handle syscalls that need to read process memory.
                if event.name == 'getsockopt':
                    if event.arguments[1].value != socket.SOL_SOCKET:
                        return
                    if event.arguments[2].value != socket.SO_ERROR:
                        return
                    arg = event.arguments[3]

                    arg.value = event.process.readStruct(arg.value, ctypes.c_int)
                    arg.text = "[{}]".format(arg.value)

                # Append all traced system calls.
                if event.name in TRACED_SYSCALLS:
                    log.debug(event)
                    self.add_event(event)

                    # Break loop if we reached the requested origin/syscall pair.
                    if event.origin == script.origin and event.name == syscall:
                        process.syscall()
                        return event

                process.syscall()

    def quit(self):
        log.debug("[{:.3f}] Quitting debugger.".format(time.time() - self.started))
        super(SyscallDebugger, self).quit()

    def add_event(self, event):
        self.events.append(event)

    def _wait_event(self, wanted_pid, blocking=True):
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
