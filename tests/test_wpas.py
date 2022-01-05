import os
import select
import socket
import tempfile
import threading
import time

from os.path import basename
from unittest import TestCase, mock

from pywpas import Control
from pywpas.utils import tempnam
from pywpas.models import Network

from .test_models import INTERFACE_STATUS, SCAN_RESULTS


def network_iter():
    networks = SCAN_RESULTS.split(b'\n')
    preamble = networks[0]
    for network in networks[1:]:
        yield preamble + b'\n' + network


class MockServer(object):
    def __init__(self):
        self.sock_path = tempfile.mkdtemp()
        sock_file = tempnam(self.sock_path)
        self.name = basename(sock_file)
        self._running = True
        self._sock = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
        self._sock.bind(sock_file)
        self._commands = []
        self.command_received = threading.Event()
        self.start()

    def _run(self):
        networks = network_iter()
        while self._running:
            if self._sock in select.select([self._sock], [], [], 0.1)[0]:
                cmd, address = self._sock.recvfrom(1024)
                self._commands.append(cmd)
                self.command_received.set()
                if cmd == b'PING':
                    self._sock.sendto(b'PONG', address)
                elif cmd == b'STATUS':
                    self._sock.sendto(INTERFACE_STATUS, address)
                elif cmd == b'SCAN_RESULTS':
                    self._sock.sendto(next(networks), address)
                elif cmd == b'ADD_NETWORK':
                    self._sock.sendto(b'1', address)
                elif cmd == b'LIST_NETWORKS':
                    self._sock.sendto(b'1', address)
                elif cmd == b'SELECT_NETWORK 1':
                    self._sock.sendto(b'foobar', address)
                elif cmd.startswith(b'GET_NETWORK 1'):
                    self._sock.sendto(b'foobar', address)

    @property
    def last_command(self):
        try:
            return self._commands[-1]
        except IndexError:
            return None

    def start(self):
        self._t = threading.Thread(target=self._run, daemon=True)
        self._t.start()

    def stop(self):
        self._running = False
        if self._t:
            self._t.join()
        self._sock.close()


class ControlTestCase(TestCase):
    def setUp(self):
        self.server = MockServer()
        self.control = Control(sock_path=self.server.sock_path)

    def tearDown(self):
        self.control.close()
        del self.control
        self.server.stop()

    def test_interface_names(self):
        self.assertEqual([self.server.name], self.control.interface_names())

    def test_interface(self):
        with self.assertRaises(FileNotFoundError):
            self.control.interface('foobar')


class InterfaceTestCase(TestCase):
    def setUp(self):
        self.server = MockServer()
        self.client = Control(sock_path=self.server.sock_path).interface(self.server.name)

    def tearDown(self):
        self.client.close()
        del self.client
        self.server.stop()

    def assertCommand(self, command):
        # Has command already been received?
        for cmd in self.server._commands:
            if cmd == command:
                return True
        # If not, wait for it to arrive.
        self.server.command_received.clear()
        while True:
            if not self.server.command_received.wait(timeout=1.0):
                # We timed out, assertion failed.
                raise AssertionError(f'Command {command} not received')
            # clear so we can for next command.
            self.server.command_received.clear()
            if command == self.server.last_command:
                return True

    def test_control(self):
        self.assertIsInstance(self.client.control, Control)

    def test_ping(self):
        # Ping checks for the reply.
        self.client.ping()
        self.assertEqual(self.server.last_command, b'PING')

    def test_status(self):
        status = self.client.status()
        self.assertEqual(self.server.last_command, b'STATUS')
        self.assertEqual(status.wpa_state, 'COMPLETED')

    def test_scan(self):
        networks = []
        scan = self.client.background_scan(lambda x: networks.append(x))
        time.sleep(0.2)
        self.assertCommand(b'SCAN')
        time.sleep(4.1)
        self.assertCommand(b'SCAN_RESULTS')
        self.assertEqual(4, len(networks))
        scan.stop()
        self.assertFalse(scan._running)
        # Should be fine to call it again.
        scan.stop()

    def test_add_network(self):
        self.client.add_network(Network(psk='foobar'))
        self.assertCommand(b'SET_NETWORK 1 psk foobar')

    def test_connect(self):
        self.client.connect(Network(psk='foobar'))
        self.assertCommand(b'SELECT_NETWORK 1')

    def test_list_networks(self):
        networks = self.client.list_networks()
        self.assertCommand(b'GET_NETWORK 1 pairwise')
        self.assertEqual(1, len(networks))

    def test_remove_network(self):
        self.client.remove_network(Network(id=1))
        self.assertCommand(b'REMOVE_NETWORK 1')

    def test_remove_networks(self):
        self.client.remove_networks()
        self.assertCommand(b'REMOVE_NETWORK all')

    def test_disconnect(self):
        self.client.disconnect()
        self.assertCommand(b'DISCONNECT')

    def test_save_config(self):
        self.client.save_config()
        self.assertCommand(b'SAVE_CONFIG')

    def test_stop_ap(self):
        self.client.stop_ap()
        self.assertCommand(b'STOP_AP')


class TimeoutTestCase(TestCase):
    def setUp(self):
        self.server = MockServer()
        self.client = Control(sock_path=self.server.sock_path).interface(self.server.name, send_timeout=1.0, recv_timeout=1.0)
        self.client._ensure_connection()
        # Server is stopped, so timeouts will occur.
        self.server.stop()

    def tearDown(self):
        self.client.close()

    def test_send_timeout(self):
        with self.assertRaises(ConnectionRefusedError):
            self.client._send('PING')

    def test_recv_timeout(self):
        with self.assertRaises(TimeoutError):
            self.client._recv()
