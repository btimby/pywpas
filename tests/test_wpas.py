import os
import select
import socket
import tempfile
import threading
import time

from os.path import basename
from unittest import TestCase, mock

from faker import Faker

from pywpas import Control, scan
from pywpas.control import tempnam
from pywpas.const import STATUS_CONNECTED
from pywpas.models import Network


FAKE = Faker()
STATUS_REPLY = '''
wpa_state=completed
'''

def random_network():
    network = Network(
        bssid=FAKE.slug(),
        freq=FAKE.random_digit_not_null(),
        signal=-87,
        ssid=FAKE.slug(),
        key_mgmt=[],
        auth='',
    )
    return network.serialize()


class MockServer(object):
    def __init__(self):
        self.sock_path = tempfile.mkdtemp()
        sock_file = tempnam(self.sock_path)
        self.name = basename(sock_file)
        self._running = True
        self._sock = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
        self._sock.bind(sock_file)
        self.start()

    def _run(self):
        while self._running:
            if self._sock in select.select([self._sock], [], [], 0.1)[0]:
                cmd, address = self._sock.recvfrom(1024)
                if cmd == b'PING':
                    self._sock.sendto(bytearray('PONG', 'utf-8'), address)
                elif cmd == b'STATUS':
                    self._sock.sendto(
                        bytearray(STATUS_REPLY, 'utf-8'), address)
                elif cmd == b'SCAN_RESULTS':
                    self._sock.sendto(random_network(), address)

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

    def test_status(self):
        status = self.client.status()
        self.assertEqual(status.wpa_state, STATUS_CONNECTED)

    def test_scan(self):
        networks = []
        scan(self.client, lambda x: networks.append(x), timeout=5.0)
        time.sleep(4.1)
        self.assertEqual(4, len(networks))
