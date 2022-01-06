"Communication with wpa_supplicant interface"
# pylint: disable=too-many-instance-attributes

import os
import time
import threading
import socket
import logging

from select import select
from typing import List, Union
from os.path import join as pathjoin, dirname

from .utils import tempnam, is_sock, safe_encode, SOCKET_PREFIX
from .models import InterfaceStatus, Network, deserialize_networks


LOGGER = logging.getLogger(__name__)
LOGGER.addHandler(logging.NullHandler())

SEND_TIMEOUT = 5.0
RECV_TIMEOUT = 5.0
SCAN_TIMEOUT = 30.0
RECV_BUFFER_SIZE = 4096


class _BackgroundScan:
    """
    High-level scan.

    Scans in background thread and calls callable with each new network.
    """
    def __init__(self, interface: 'Interface'):
        self._interface = interface
        self._running = False
        self._t = None

    def _scan(self, callback, timeout):
        "Background scan thread entry point"
        networks, started = set(), time.time()
        self._interface.scan()
        while self._running and time.time() - started < timeout:
            time.sleep(1.0)
            for network in self._interface.scan_results():
                if network.ssid not in networks:
                    networks.add(network.ssid)
                    callback(network)

    def start(self, callback: callable, timeout: float=SCAN_TIMEOUT):
        "Start background scan"
        assert callable(callback), 'Callback must be callable'
        self._running = True
        self._t = threading.Thread(
            target=self._scan, args=(callback, timeout), daemon=True)
        self._t.start()

    def stop(self):
        "Stop background scan"
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
class Interface:
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
        self._connection = None
        self._server_path = pathjoin(self._control._sock_path, self.name)
        assert is_sock(self._server_path), 'Not a valid interface'
        self._client_path = None
        self._networks = {}

    def __del__(self):
        self.close()

    @property
    def name(self):
        "This interface's name"
        return self._name

    @property
    def control(self) -> 'Control':
        "The parent object which gives access to additional interfaces"
        return self._control

    @property
    def networks(self):
        "Networks discovered by list_networks()"
        return list(self._networks.values())

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
            LOGGER.warning('Error deleting client socket at: %s',
                        self._client_path)
        self._client_path = None

    def _ensure_connection(self):
        """
        Open a connection if not already established.
        """
        if self._connection is not None:
            return
        self._client_path = tempnam(dirname(self._server_path), SOCKET_PREFIX)
        self._connection = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
        self._connection.bind(self._client_path)
        self._connection.connect(self._server_path)

    def _send(self, cmd: Union[str, bytes]) -> None:
        """
        Send data to wpa_supplicant.

        Accepts a string or bytes.
        """
        self._ensure_connection()
        cmd = safe_encode(cmd)
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
        "Connection test"
        LOGGER.info('Pinging wpa_supplicant')
        resp = self._send_and_recv(b'PING')
        assert resp == [b'PONG'], 'Did not receive proper reply'

    def status(self) -> InterfaceStatus:
        "Get interface status"
        LOGGER.info('Retrieving interface status')
        status = InterfaceStatus.deserialize(self._send_and_recv('STATUS'))
        return status

    def scan(self) -> None:
        "Start scanning"
        LOGGER.info('Initiating scan')
        self._send(b'SCAN')

    def background_scan(self, callback: callable,
                        timeout: float=SCAN_TIMEOUT) -> None:
        "Perform background scan on thread"
        LOGGER.info('Starting background scan')
        scan = _BackgroundScan(self)
        scan.start(callback, timeout)
        return scan

    def scan_results(self):
        "Return scan results"
        LOGGER.info('Retrieving scan results')
        networks = deserialize_networks(self._send_and_recv(b'SCAN_RESULTS'))
        for network in networks:
            LOGGER.info('Found network: %s', network)
        return networks

    def add_network(self, network: Network) -> None:
        "Add network profile"
        LOGGER.info('Adding network: %s', network.ssid)
        network.id = int(self._send_and_recv(b'ADD_NETWORK')[0])
        LOGGER.debug('Assigned id: %i', network.id)
        self._send(f'SET_NETWORK {network.id} ssid {network.ssid}')
        self._send(f'SET_NETWORK {network.id} key_mgmt {network.key_mgmt}')
        self._send(f'SET_NETWORK {network.id} proto {network.proto}')
        self._send(f'SET_NETWORK {network.id} psk {network.psk}')
        self._networks[network.id] = network

    def list_networks(self) -> List[Network]:
        "List network profiles"
        LOGGER.info('Listing networks')
        network_ids = map(int, self._send_and_recv(b'LIST_NETWORKS'))
        LOGGER.debug('Received network ids: %s', network_ids)
        for network_id in network_ids:
            kwargs = {}
            kwargs['ssid'] = self._send_and_recv(f'GET_NETWORK {network_id} ssid')[0]
            kwargs['key_mgmt'] = self._send_and_recv(f'GET_NETWORK {network_id} key_mgmt')[0]
            kwargs['proto'] = self._send_and_recv(f'GET_NETWORK {network_id} proto')[0]
            kwargs['ciphers'] = self._send_and_recv(f'GET_NETWORK {network_id} pairwise')[0]
            self._networks[network_id] = Network(**kwargs)
        return self.networks

    def remove_network(self, network: Network) -> None:
        "Remove given network profile"
        LOGGER.info('Removing network profile: %s', network.ssid)
        self._send(f'REMOVE_NETWORK {network.id}')
        self._networks.pop(network.id, None)

    def remove_networks(self) -> None:
        "Delete all network profiles"
        LOGGER.info('Removing all networks')
        self._send(b'REMOVE_NETWORK all')
        self._networks.clear()

    def connect(self, network: Network):
        "connect interface to given network"
        if network.id is None:
            self.add_network(network)
        LOGGER.info('Connecting to network: %s', network.ssid)
        self._send_and_recv(f'SELECT_NETWORK {network.id}')

    def disconnect(self) -> None:
        "Disconnect interface"
        LOGGER.info('Disconnecting')
        self._send(b'DISCONNECT')

    def save_config(self):
        "Save running config to file"
        LOGGER.info('Saving configuration')
        self._send(b'SAVE_CONFIG')

    def stop_ap(self):
        "Stop access point"
        LOGGER.info('Stopping access point')
        self._send(b'STOP_AP')
