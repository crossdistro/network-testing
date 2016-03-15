#!/usr/bin/python

from __future__ import print_function

import os, sys, subprocess, errno
import collections, functools, itertools
import argparse
import socket
import re

import debug
import ptrace.debugger

import logging
logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger('tests')

data_path = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'data')
testcase_path = os.path.join(data_path, 'testcases', 'client-server')

SOCKET_OPERATIONS = set(['bind', 'listen', 'accept', 'connect', 'getsockopt', 'shutdown', 'close'])
PROCESS_SYSCALLS = set(['close', 'execve', 'fork', 'clone'])

class Property(object):
    success = lambda self: None

    def __init__(self, arg):
        self.arg = arg

    def __str__(self):
        return self.template.format(**vars(self))

    def __repr__(self):
        return repr(str(self))

    @property
    def success(self):
        return bool(self.arg)

class Errors(Property):
    template = "Number of errors: {arg}"

    @property
    def success(self):
        return not self.arg

class IP4Listener(Property):
    template = "Listens on IPv4: {arg}"

class IP6Listener(Property):
    template = "Listens on IPv6: {arg}"

class IP4Connection(Property):
    template = "Attempts IPv4 connection: {arg}"

class IP6Connection(Property):
    template = "Attempts IPv6 connection: {arg}"

class ParallelConnect(Property):
    template = "Connection method is {method}. {description}"
    success = None

    def __init__(self, flag):
        if flag:
            self.method = "parallel"
            self.description = "This is a happy eyeballs style dual-stack connection method resulting in fast fallback when the preferred address family fails silently."
        else:
            self.method = "sequential"
            self.description = "This is a classic dual-stack connection method resulting in a significant timeout when the preferred address family fails silently."

class V6PreferredDelay(Property):
    def __str__(self):
        if self.arg is None:
            return "IPv6 isn't preferred or fallback to IPv4 doesn't work."
        else:
            return "IPv6 is preferred and fallback to IPv4 takes {arg:.3f} seconds.".format(**vars(self))

class ConnectionCleanup(Property):
    template = "Connection was shut down and closed: {arg}"
    success = None

class Scenario(object):
    client = server = None

    def __init__(self, testcase):
        self.expected_exitcodes = {'server': 0, 'client': 0}
        self.namespaces = []
        self.testcase = testcase
        self.errors = []
        self.listeners = []
        self.connections = []

    def __str__(self):
        return self.name

    def run(self):
        debugger = debug.SyscallDebugger()

        # Run entities and collect syscalls.
        self.prepare()
        try:
            log.info("\n*** {} / {} ***\n".format(self.testcase.name, self.name))

            try:
                self.server = self.start(debugger, "server")
                debugger.set_timeout(35)
                debugger.wait(self.server, "listen")
                debugger.set_timeout(5)
                debugger.wait(self.server, "listen")
            except debug.Timeout:
                self.error("Server timeout occured.")

            try:
                self.client = self.start(debugger, "client")
                debugger.set_timeout(20)
                debugger.wait(self.client)
            except debug.Timeout:
                self.error("Client timeout occured.")
        except BaseException as error:
            self.error("Python exception {} occured: {}".format(type(error), error))
            raise
        finally:
            debugger.quit()
            self.cleanup()

        self.events = debugger.events
        del debugger

        # Process collected events.
        for event in self.events:
            if isinstance(event, ptrace.debugger.process_event.ProcessExit):
                if event.exitcode != self.expected_exitcodes[event.origin]:
                    self.error("Unexpected {} exit code {}.".format(event.origin, event.exitcode))
                if event.process == self.server:
                    log.debug("Server exit code is {}.".format(event.exitcode))
                if event.process == self.client:
                    log.debug("Client exit code is {}.".format(event.exitcode))
            elif event.name == 'listen':
                if event.origin != 'server':
                    continue
                self.listeners.append(event.socket)
            elif event.name == 'connect':
                if event.origin != 'client':
                    continue
                if event.socket.domain.value not in (socket.AF_INET, socket.AF_INET6):
                    continue
                if re.search(" sin6?_port=0, ", event.arguments[1].text):
                    continue
                conn = event.socket
                conn.attempted = event.time
                conn.status = event.result
                conn.nonblocking = conn.status == errno.EINPROGRESS
                conn.shutdown = False
                conn.closed = None
                self.connections.append(conn)
            elif event.name == 'getsockopt':
                if event.origin != 'client':
                    continue
                if event.arguments[1].value != socket.SOL_SOCKET:
                    continue
                if event.arguments[2].value != socket.SO_ERROR:
                    continue
                event.socket.status = event.arguments[3].value
            elif event.name == 'shutdown' and event.result == 0:
                event.socket.shutdown = True
            elif event.name == 'close' and event.result == 0:
                event.socket.closed = event.time


        # Postprocess acquired data.
        self.postprocess()

    def start(self, debugger, origin):
        command = self.command(self.testcase.name, origin)

        try:
            return debugger.new_child(origin, command)
        except ptrace.debugger.child.ChildError:
            self.error("Script '{}' not found.".format(name))
            return debugger.new_child(origin, ['/bin/true'])

    def prepare(self):
        os.environ['NETRESOLVE_BACKENDS'] = 'any|loopback|numerichost|hosts';
        os.environ['NETRESOLVE_SYSCONFDIR'] = data_path;
        os.environ['DEFAULT_SERVICE'] = 'http'

    def cleanup(self):
        for ns in self.namespaces:
            subprocess.call(['ip', 'netns', 'delete', ns])

    def postprocess(self):
        pass

    def _add_netns(self, ns):
        self.namespaces.append(ns)
        subprocess.call(['ip', 'netns', 'delete', ns])
        subprocess.check_call(['ip', 'netns', 'add', ns])
        subprocess.check_call(['ip', '-n', ns, 'link', 'set', 'lo', 'up'])

    def _add_veth(self, ns1, ns2):
        link1, link2 = ns1, ns2
        subprocess.check_call(['ip', 'link', 'add', 'dev', link1, 'type', 'veth', 'peer', 'name', link2])
        for ns, link in (ns1, link1), (ns2, link2):
            subprocess.check_call(['ip', 'link', 'set', link, 'netns', ns, 'up'])

    def _add_address(self, ns, link, address):
        subprocess.check_call(['ip', '-n', ns, 'address', 'add', address, 'dev', link])

    def error(self, error):
        self.errors.append(error)

    def report(self):
        print('    ' + self.name)
        for listener in self.listeners:
            print("      Listener: {}".format(listener))
            for event in listener.events:
                print("        {}".format(event))
        for connection in self.connections:
            print("      Connection: {}".format(connection))
            for event in connection.events:
                print("        {}".format(event))
        for error in self.errors:
            print('      ' + str(error))

class LoopbackScenario(Scenario):
    name = 'loopback'

    def prepare(self):
        super(self.__class__, self).prepare()
        os.environ['SOURCE'] = os.environ['DESTINATION'] = 'localhost'
        self._add_netns('test-loopback')

    def command(self, name, origin):
        return ['ip', 'netns', 'exec', 'test-loopback', 'wrapresolve', os.path.join(testcase_path, name, origin)]

class DualstackScenario(Scenario):
    name = 'dualstack'

    source_ns = 'test-client'
    destination_ns = 'test-server'
    source_link, destination_link = source_ns, destination_ns
    destination_config = ['192.0.2.1/24', '2001:DB8::2:1/64']
    source_config = ['192.0.2.2/24', '2001:DB8::2:2/64']

    def prepare(self):
        super(DualstackScenario, self).prepare()
        os.environ['SOURCE'] = 'client.example.net'
        os.environ['DESTINATION'] = 'server.example.net'
        for ns in self.source_ns, self.destination_ns:
            self._add_netns(ns)
        self._add_veth(self.source_ns, self.destination_ns)
        for address in self.source_config:
            self._add_address(self.source_ns, self.source_link, address)
        for address in self.destination_config:
            self._add_address(self.destination_ns, self.destination_link, address)

    def command(self, name, origin):
        return ['ip', 'netns', 'exec', 'test-{}'.format(origin), 'wrapresolve', os.path.join(testcase_path, name, origin)]

    def postprocess(self):
        self.testcase.add_property(IP4Listener(bool([listener for listener in self.listeners if listener.domain.value == socket.AF_INET])))
        self.testcase.add_property(IP6Listener(bool([listener for listener in self.listeners if listener.domain.value == socket.AF_INET6])))
        self.testcase.add_property(ParallelConnect(len(self.connections) > 1))

class IP6DroppedScenario(DualstackScenario):
    name = 'v6dropped'

    def prepare(self):
        super(IP6DroppedScenario, self).prepare()
        subprocess.check_call(['ip', 'netns', 'exec', 'test-client', 'ip6tables', '-A', 'OUTPUT', '-j', 'DROP'])

    @staticmethod
    def _check_preferred(preferred, fallback):
        # Preferred was attempted too late after fallback.
        if preferred.attempted > fallback.attempted + 0.1:
            return None
        # Preferred wasn't closed.
        if not preferred.closed:
            return None
        # Preferred was closed too early after attempted.
        if preferred.closed < preferred.attempted + 0.05:
            return None
        # Preferred was closed after fallback.
        if fallback.closed and preferred.closed > fallback.closed:
            return None
        return preferred.closed - preferred.attempted

    def postprocess(self):
        v4 = [conn for conn in self.connections if conn.domain.value == socket.AF_INET]
        v6 = [conn for conn in self.connections if conn.domain.value == socket.AF_INET6]

        self.testcase.add_property(IP4Connection(bool(v4)))
        self.testcase.add_property(IP6Connection(bool(v6)))

        if len(v4) == 1 and len(v6) == 1:
            v6preferred = self._check_preferred(v6[0], v4[0])
            self.testcase.add_property(V6PreferredDelay(v6preferred))
            self.testcase.add_property(ConnectionCleanup(bool(v6preferred and v4[0].shutdown and v4[0].closed)))

result_str = { False: "FAIL", True: "PASS", None: "INFO" }

class TestCase:
    scenario_classes = [LoopbackScenario, DualstackScenario, IP6DroppedScenario]

    def __init__(self, name, scenarios=None):
        self.name = name
        self.scenarios = [cls(self) for cls in self.scenario_classes]
        if scenarios:
            self.scenarios = [scenario for scenario in self.scenarios if scenario.name in scenarios]
        self.properties = {}

    def run(self):
        errors = Errors(0)
        for scenario in self.scenarios:
            scenario.run()
            errors.arg += len(scenario.errors)
        self.add_property(errors)
        self.result = len([prop for prop in self.properties.values() if prop.success is False]) == 0

    def add_property(self, prop):
        self.properties[type(prop)] = prop

    def report(self):
        print(self.name)
        print("  Scenarios:")
        for scenario in self.scenarios:
            scenario.report()
        print("  Properties:")
        for text, success in sorted([(str(value), value.success) for value in self.properties.values()]):
            print("    {} ({})".format(text, result_str[success]))
        print("  Result: {}".format(result_str[self.result]))
        print()

class TestSuite:
    def __init__(self, testcases=None, scenarios=None):
        self.testcases = [TestCase(name, scenarios) for name in sorted(os.listdir(testcase_path))]
        if testcases:
            self.testcases = [testcase for testcase in self.testcases if testcase.name in testcases]

    def run(self):
        for testcase in self.testcases:
            testcase.run()
        self.result = not [testcase.result for testcase in self.testcases if testcase.result is False]

    def report(self):
        print()
        for testcase in self.testcases:
            testcase.report()
        print("Overall result: {}".format(result_str[self.result]))
        print()

def main():
    parser = argparse.ArgumentParser(description="Test driver for client-server networking applications.")
    parser.add_argument("--debug", "-d", action="store_true", help="Print debug messages.")
    parser.add_argument("--list-testcases", "-l", action="store_true", help="List testcases and scenarios.")
    parser.add_argument("--list-scenarios", action="store_true", help="List testcases and scenarios.")
    parser.add_argument("--deps", action="store_true", help="List dependencies.")
    parser.add_argument("testcases", nargs="?")
    parser.add_argument("scenarios", nargs="?")
    options = parser.parse_args()

    if options.debug:
        logging.getLogger().setLevel(logging.DEBUG)

    testcases = options.testcases and options.testcases.split(',')
    scenarios = options.scenarios and options.scenarios.split(',')

    suite = TestSuite(testcases, scenarios)
    if options.list_testcases:
        for testcase in suite.testcases:
            print(testcase.name)
        exit(0)
    elif options.list_scenarios:
        for scenario in TestCase.scenario_classes:
            print(scenario.name)
        exit(0)
    elif options.deps:
        for testcase in suite.testcases:
            path = os.path.join(testcase_path, testcase.name, "deps")
            if os.path.isfile(path):
                subprocess.check_call(['cat', path])
        exit(0)
    else:
        suite.run()
        suite.report()

    exit(0 if suite.result else 1)

if __name__ == '__main__':
    main()
