"Control interface for wpa_supplicant"

import os
import logging

from typing import List

from .interface import Interface
from .utils import find_sockets


LOGGER = logging.getLogger(__name__)
LOGGER.addHandler(logging.NullHandler())

DEFAULT_SOCK_PATH = os.environ.get('WPA_SOCK', '/var/run/wpa_supplicant')


class Control:
    """
    Control wpa_supplicant.
    """
    def __init__(self, sock_path: str=DEFAULT_SOCK_PATH):
        self._sock_path = sock_path
        self._interfaces = None

    def __del__(self):
        self.close()

    def close(self) -> None:
        "Close all interfaces"
        LOGGER.info('Closing interfaces')
        if self._interfaces is None:
            LOGGER.debug('No interfaces')
            return
        for iface in self._interfaces:
            iface.close()
        self._interfaces = None

    def interface(self, name: str, **kwargs) -> Interface:
        "Get specific interface"
        LOGGER.info('Connecting to interface %s', name)
        return Interface(self, name, **kwargs)

    def interface_names(self):
        "List of interface names"
        LOGGER.info('Returning names of %i interfaces', len(self.interfaces))
        return [
            interface.name for interface in self.interfaces
        ]

    @property
    def interfaces(self) -> List[Interface]:
        "List of interfaces"
        LOGGER.info('Listing interfaces')
        if self._interfaces is None:
            self._interfaces = []
            for name in find_sockets(self._sock_path):
                self._interfaces.append(Interface(self, name))
        return self._interfaces
