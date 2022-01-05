import os
import time
import tempfile
import threading
import socket
import logging

from select import select
from typing import List, Union
from os.path import join as pathjoin

from .utils import tempnam, is_sock
from .models import InterfaceStatus, Network, deserialize_networks


LOGGER = logging.getLogger(__name__)
LOGGER.addHandler(logging.NullHandler())

SEND_TIMEOUT = 5.0
RECV_TIMEOUT = 5.0
SCAN_TIMEOUT = 30.0
RECV_BUFFER_SIZE = 4096


class _BackgroundScan(object):
    """
    High-level scan.

    Scans in background thread and calls callable with each new network.
    """
    def __init__(self, interface: 'Interface'):
        self._interface = interface
        self._running = False
        self._t = None

    def _scan(self, callback, timeout):
        networks, started = set(), time.time()
        self._interface.scan()
        while self._running and time.time() - started < timeout:
            time.sleep(1.0)
            for network in self._interface.results():
                if network.ssid not in networks:
                    networks.add(network.ssid)
                    callback(network)

    def start(self, callback: callable, timeout: float=SCAN_TIMEOUT):
        assert callable(callback), 'Callback must be callable'
        self._running = True
        self._t = threading.Thread(
            target=self._scan, args=(callback, timeout), daemon=True)
        self._t.start()

    def stop(self):
        if self._t is None:
            return
        self._running = False
        self._t.join()
        self._t = None


# Supported commands are listed here:
# https://github.com/digsrc/wpa_supplicant/blob/master/wpa_supplicant/ctrl_iface.c#L8128
#
# ANQP_GET AP_SCAN AUTOSCAN BLACKLIST BSS BSS_EXPIRE_AGE BSS_EXPIRE_COUNT
# BSS_FLUSH BSSID CHAN_SWITCH DATA_TEST_CONFIG DATA_TEST_FRAME DATA_TEST_TX
# DEAUTHENTICATE DISABLE_NETWORK DISASSOCIATE DRIVER DRIVER_EVENT DUMP
# DUP_NETWORK EAPOL_RX ENABLE_NETWORK FT_DS GAS_REQUEST GAS_RESPONSE_GET
# GET GET_CAPABILITY GET_CRED GET_NETWORK GET_PREF_FREQ_LIST HS20_ANQP_GET
# HS20_GET_NAI_HOME_REALM_LIST HS20_ICON_REQUEST IBSS_RSN
# INTERWORKING_ADD_NETWORK INTERWORKING_CONNECT INTERWORKING_SELECT
# LIST_NETWORKS LOG_LEVEL MAC_RAND_SCAN MESH_GROUP_ADD MESH_GROUP_REMOVE
# MESH_INTERFACE_ADD MGMT_TX NEIGHBOR_REP_REQUEST NFC_GET_HANDOVER_REQ
# NFC_GET_HANDOVER_SEL NFC_REPORT_HANDOVER NOTE P2P_ASP_PROVISION
# P2P_ASP_PROVISION_RESP P2P_CONNECT P2P_EXT_LISTEN P2P_FIND P2P_GROUP_ADD
# P2P_GROUP_REMOVE P2P_INVITE P2P_LISTEN P2P_PEER P2P_PRESENCE_REQ
# P2P_PROV_DISC P2P_REJECT P2P_REMOVE_CLIENT P2P_SERV_DISC_CANCEL_REQ
# P2P_SERV_DISC_EXTERNAL P2P_SERV_DISC_REQ P2P_SERV_DISC_RESP P2P_SERVICE_ADD
# P2P_SERVICE_DEL P2P_SERVICE_REP P2P_SET P2P_UNAUTHORIZE PKTCNT_POLL PREAUTH
# RADIO_WORK RELOG REMOVE_CRED REMOVE_NETWORK ROAM SCAN SCAN_INTERVAL
# SELECT_NETWORK SET SET_CRED SET_NETWORK SIGNAL_POLL STA STA_AUTOCONNECT
# STA-NEXT STATUS STKSTART TDLS_CANCEL_CHAN_SWITCH TDLS_CHAN_SWITCH
# TDLS_DISCOVER TDLS_LINK_STATUS TDLS_SETUP TDLS_TEARDOWN TEST_ALLOC_FAIL
# TEST_FAIL VENDOR VENDOR_ELEM_ADD VENDOR_ELEM_GET VENDOR_ELEM_REMOVE
# WFD_SUBELEM_GET WFD_SUBELEM_SET WMM_AC_ADDTS WMM_AC_DELTS WNM_BSS_QUERY
# WNM_SLEEP WPA_CTRL_RSP WPS_AP_PIN WPS_CHECK_PIN WPS_ER_CONFIG WPS_ER_LEARN
# WPS_ER_NFC_CONFIG_TOKEN WPS_ER_PBC WPS_ER_PIN WPS_ER_SET_CONFIG
# WPS_ER_START WPS_NFC WPS_NFC_CONFIG_TOKEN WPS_NFC_TAG_READ WPS_NFC_TOKEN
# WPS_PBC WPS_PIN WPS_REG
#
class Interface(object):
    """
    Handle a unix:// datagram connection for a given interface.
    """
    def __init__(self, control: 'Control', name: str,
                 send_timeout: float=SEND_TIMEOUT,
                 recv_timeout: float=RECV_TIMEOUT):
        self._control = control
        self._name = name
        self._send_timeout = send_timeout
        self._recv_timeout = recv_timeout
        self._server_path = pathjoin(self._control._sock_path, self.name)
        assert is_sock(self._server_path), 'Not a valid interface'
        self._client_path = None
        self._connection = None

    def __del__(self):
        self.close()

    @property
    def name(self):
        return self._name

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

    def _send(self, cmd: Union[str, bytes]) -> None:
        """
        Send data to wpa_supplicant.

        Accepts a string or bytes.
        """
        self._ensure_connection()
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

    def background_scan(self, callback: callable,
                        timeout: float=SCAN_TIMEOUT) -> None:
        scan = _BackgroundScan(self)
        scan.start(callback, timeout)
        return scan

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

    def config_write(self):
        self._send('SAVE_CONFIG')

    def stop_ap(self):
        self._send('STOP_AP')
