import os
import select
import socket
import tempfile
import threading
import time

from os.path import basename
from unittest import TestCase, mock

from faker import Faker

from pywpas import Control
from pywpas.utils import tempnam
from pywpas.const import STATUS_CONNECTED
from pywpas.models import Network

from .test_models import INTERFACE_STATUS, SCAN_RESULTS

FAKE = Faker()


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
        self.start()

    def _run(self):
        networks = network_iter()
        while self._running:
            if self._sock in select.select([self._sock], [], [], 0.1)[0]:
                cmd, address = self._sock.recvfrom(1024)
                self._commands.append(cmd)
                if cmd == b'PING':
                    self._sock.sendto(bytearray('PONG', 'utf-8'), address)
                elif cmd == b'STATUS':
                    self._sock.sendto(INTERFACE_STATUS, address)
                elif cmd == b'SCAN_RESULTS':
                    self._sock.sendto(next(networks), address)

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
        self.client = Control(sock_path=self.server.sock_path).interface(self.server.name)

    def tearDown(self):
        self.client.close()
        self.server.stop()

    def test_ping(self):
        # Ping checks for the reply.
        self.client.ping()
        self.assertEqual(self.server.last_command, b'PING')

    def test_status(self):
        status = self.client.status()
        self.assertEqual(self.server.last_command, b'STATUS')
        self.assertEqual(status.wpa_state, STATUS_CONNECTED)

    def test_scan(self):
        networks = []
        scan = self.client.background_scan(lambda x: networks.append(x))
        time.sleep(0.2)
        self.assertEqual(self.server.last_command, b'SCAN')
        time.sleep(4.1)
        self.assertEqual(self.server.last_command, b'SCAN_RESULTS')
        self.assertEqual(4, len(networks))
        scan.stop()
        self.assertFalse(scan._running)
