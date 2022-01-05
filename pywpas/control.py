import os
import socket
import logging
import tempfile
import stat
import threading
import time

from select import select
from functools import wraps
from os.path import dirname, join as pathjoin
from typing import List, Union

from .models import InterfaceStatus, Network, deserialize_networks


LOGGER = logging.getLogger(__name__)
LOGGER.addHandler(logging.NullHandler())

DEFAULT_SOCK_PATH = os.environ.get('WPA_SOCK', '/var/run/wpa_supplicant')
RECV_BUFFER_SIZE = 4096
SEND_TIMEOUT = 5.0
RECV_TIMEOUT = 5.0
SCAN_TIMEOUT = 30.0


def ensure_connection(f):
    """
    Decorator that ensures the connection is established before executing a
    function's body.
    """
    @wraps(f)
    def inner(self, *args, **kwargs):
        self._ensure_connection()
        return f(self, *args, **kwargs)
    return inner


def tempnam(dir: str, prefix: str='') -> str:
    """
    Utility function.

    Creates a temporary file, but removes and closes the file. In effect
    it creates a temporary path (that does not exist). For use as a socket
    address.
    """
    fd, path = tempfile.mkstemp(dir=dir, prefix=prefix)
    os.close(fd)
    os.remove(path)
    return path


def _is_sock(path):
    return stat.S_ISSOCK(os.stat(path).st_mode)


def _find_sockets(dir):
    return [path for path in os.listdir(dir) if _is_sock(pathjoin(dir, path))]


def scan(iface: 'Interface', callback: callable,
         timeout: float=SCAN_TIMEOUT) -> None:
    """
    High-level scan.

    Scans in background thread and calls callable with each new network.
    """
    assert callable(callback), 'Callback must be callable'
    networks, started = set(), time.time()
    iface.scan()
    def _scan():
        while time.time() - started < timeout:
            time.sleep(1.0)
            for network in iface.results():
                if network.ssid not in networks:
                    networks.add(network.ssid)
                    callback(network)
    t = threading.Thread(target=_scan, daemon=True)
    t.start()


class Interface(object):
    """
    Handle a unix:// datagram connection for a given interface.
    """
    def __init__(self, control: 'Control', name: str,
                 send_timeout: float=SEND_TIMEOUT,
                 recv_timeout: float=RECV_TIMEOUT):
        self._control = control
        self.name = name
        self._send_timeout = send_timeout
        self._recv_timeout = recv_timeout
        self._server_path = pathjoin(self._control._sock_path, self.name)
        assert _is_sock(self._server_path), 'Not a valid interface'
        self._client_path = None
        self._connection = None

    def __del__(self):
        self.close()

    @property
    def control(self) -> 'Control':
        return self._control

    def close(self) -> None:
        """
        Close the socket when deallocated.
        """
        if self._connection is None:
            return
        self._connection.close()
        self._connection = None
        try:
            os.remove(self._client_path)
        except FileNotFoundError:
            LOGGER.warn('Error deleting client socket at: %s',
                        self._client_path)
            pass
        self._client_path = None

    def _ensure_connection(self):
        """
        Open a connection if not already established.
        """
        if self._connection is not None:
            return
        self._client_path = tempnam(tempfile.tempdir, 'pywpas')
        self._connection = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
        self._connection.bind(self._client_path)
        self._connection.connect(self._server_path)

    @ensure_connection
    def _send(self, cmd: Union[str, bytes]) -> None:
        """
        Send data to wpa_supplicant.

        Accepts a string or bytes.
        """
        try:
            cmd = cmd.encode('utf-8')
        except AttributeError:
            pass
        if self._connection not in select([], [self._connection], [],
                                          self._send_timeout)[1]:
            raise TimeoutError()
        LOGGER.debug('sending(%s) >> %s', self.name, cmd)
        self._connection.send(cmd)

    def _recv(self) -> str:
        """
        Read data from wpa_supplicant.

        Returns a string, possibly multiple lines.
        """
        if self._connection not in select([self._connection], [], [],
                                          self._recv_timeout)[0]:
            raise TimeoutError()
        data = self._connection.recv(RECV_BUFFER_SIZE)
        data = data.strip()
        LOGGER.debug('received(%s) << %s', self.name, data)
        return data

    def _send_and_recv(self, cmd: Union[str, bytes]) -> List[str]:
        """
        Send data to then read data from wpa_supplicant.

        Returns an array of strings (one per line).
        """
        self._send(cmd)
        resp = self._recv()
        return resp.split(b'\n')

    def ping(self) -> None:
        resp = self._send_and_recv(b'PING')
        assert resp == [b'PONG'], 'Did not receive proper reply'

    def status(self) -> InterfaceStatus:
        status = InterfaceStatus.deserialize(self._send_and_recv('STATUS'))
        LOGGER.info('Interface status: %s', status)
        return status

    def scan(self) -> None:
        LOGGER.info('Scanning')
        self._send(b'SCAN')

    def results(self):
        networks = deserialize_networks(self._send_and_recv(b'SCAN_RESULTS'))
        for network in networks:
            LOGGER.info('Found network: %s', network)
        return networks

    def add_network(self, network: Network) -> None:
        pass

    def networks(self) -> List[Network]:
        pass

    def del_network(self, network: Network) -> None:
        self._send(b'REMOVE_NETWORK %s' % network.id)

    def clear_networks(self) -> None:
        LOGGER.info('Removing all networks')
        self._send(b'REMOVE_NETWORK all')

    def connect(self, network: Network):
        pass

    def disconnect(self) -> None:
        self._send(b'DISCONNECT')


class Control(object):
    """
    Control wpa_supplicant.
    """
    def __init__(self, sock_path: str=DEFAULT_SOCK_PATH):
        self._sock_path = sock_path
        self._interfaces = None

    def __del__(self):
        self.close()

    def close(self) -> None:
        if self._interfaces is None:
            return
        for iface in self._interfaces:
            iface.close()
        self._interfaces = None

    def interface(self, name: str) -> Interface:
        for iface in self.interfaces:
            if iface.name == name:
                return iface
        raise ValueError('Invalid interface name: %s' % name)

    def interface_names(self):
        return [
            interface.name for interface in self.interfaces
        ]

    @property
    def interfaces(self) -> List[Interface]:
        if self._interfaces is None:
            self._interfaces = []
            for name in _find_sockets(self._sock_path):
                self._interfaces.append(Interface(self, name))
        return self._interfaces
