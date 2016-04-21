# -*- coding: utf-8 -*-
from __future__ import print_function

import errno
import json
import os
import re
import socket
import subprocess

from .logger import logger

result_str = {False: "FAIL", True: "PASS", None: "INFO"}

data_path = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'data')
testcase_path = os.path.join(data_path, 'testcases', 'client-server')

registered_properties = []


def register_property(cls):
    registered_properties.append(cls)
    return cls


class Property(object):
    description = ""
    type = "bool"
    values = None

    def __init__(self, value):
        self.value = value

    def __str__(self):
        return "{.name}".format(self)

    def __repr__(self):
        return repr(str(self))

    @property
    def status(self):
        return bool(self.value)

    def to_dict(self):
        return {'value': self.value, 'status': result_str[self.status]}

@register_property
class IP4Listener(Property):
    name = 'ip4-listener'
    description = "Listens on IPv4"
    short = "L4"


@register_property
class IP6Listener(Property):
    name = 'ip6-listener'
    description = "Listens on IPv6"
    short = "L6"


@register_property
class IP4Connection(Property):
    name = 'ip4-connection'
    description = "Attempts IPv4 connection"
    short = "C4"


@register_property
class IP6Connection(Property):
    name = 'ip6-connection'
    description = "Attempts IPv6 connection"
    short = "C6"


@register_property
class V6PreferredDelay(Property):
    name = 'ip6-preferred-delay'
    description = "Delay that ensures IPv6 preference"
    short = "D6"
    type = "float"

    def __str__(self):
        if self.value is None:
            return "IPv6 isn't preferred or fallback to IPv4 doesn't work."
        else:
            return "IPv6 is preferred and fallback to IPv4 takes {value:.3f} seconds.".format(**vars(self))


@register_property
class ConnectionCleanup(Property):
    name = 'connection-cleanup'
    description = "Connection was shut down and closed"
    short = "CC"
    status = None


@register_property
class ParallelConnect(Property):
    name = 'parallel-connect'
    description = "Connection method is parallel"
    short = "PC"
    values = {
        False: {
            'description': "This is a classic dual-stack connection method resulting in a significant timeout when the preferred address family fails silently.",
        },
        True: {
            'description': "This is a happy eyeballs style dual-stack connection method resulting in fast fallback when the preferred address family fails silently.",
        },
    }
    status = None


@register_property
class Errors(Property):
    name = 'errors'
    description = "Number of errors"
    short = "Err"
    type = "int"

    @property
    def status(self):
        return not self.value


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
        # this import is here to be able to run the client_server.py to anything except running tests also without
        # installed dependencies. To generate SRPM one has to run the client_server.py and it tracebacks without ptrace
        from . import debug
        import ptrace.debugger

        debugger = debug.SyscallDebugger()

        # Run entities and collect syscalls.
        self.prepare()
        try:
            logger.info("\n*** {} / {} ***\n".format(self.testcase.name, self.name))

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
                    logger.debug("Server exit code is {}.".format(event.exitcode))
                if event.process == self.client:
                    logger.debug("Client exit code is {}.".format(event.exitcode))
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
        return ['ip', 'netns', 'exec', 'test-{}'.format(origin), 'wrapresolve',
                os.path.join(testcase_path, name, origin)]

    def postprocess(self):
        self.testcase.add_property(
            IP4Listener(bool([listener for listener in self.listeners if listener.domain.value == socket.AF_INET])))
        self.testcase.add_property(
            IP6Listener(bool([listener for listener in self.listeners if listener.domain.value == socket.AF_INET6])))
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
            errors.value += len(scenario.errors)
        self.add_property(errors)
        self.result = len([prop for prop in self.properties.values() if prop.status is False]) == 0

    def add_property(self, prop):
        self.properties[type(prop)] = prop

    def report(self):
        print(self.name)
        print("  Scenarios:")
        for scenario in self.scenarios:
            scenario.report()
        print("  Properties:")
        for text, status in sorted([(str(value), value.status) for value in self.properties.values()]):
            print("    {} ({})".format(text, result_str[status]))
        print("  Result: {}".format(result_str[self.result]))
        print()

    def to_dict(self):
        result = {'status': result_str[self.result]}
        props = result['properties'] = {prop.name: prop.to_dict() for prop in self.properties.values()}
        return result

    def save(self, outdir):
        with open(os.path.join(outdir, "test-client-server-{}.json".format(self.name)), 'w') as stream:
            json.dump({self.name: self.to_dict()}, stream, indent=4, separators=(',', ': '))
            print(file=stream)


class TestSuite:
    def __init__(self, testcases=None, scenarios=None):
        self.testcases = [TestCase(name, scenarios) for name in sorted(os.listdir(testcase_path))]
        if testcases:
            self.testcases = [testcase for testcase in self.testcases if testcase.name in testcases]

    def run(self):
        for testcase in self.testcases:
            testcase.run()
        self.result = not [testcase.result for testcase in self.testcases if testcase.result is False]

    def save(self, outdir):
        if not os.path.isdir(outdir):
            os.mkdir(outdir)
        for testcase in self.testcases:
            testcase.save(outdir)

    def report(self):
        print()
        for testcase in self.testcases:
            testcase.report()
