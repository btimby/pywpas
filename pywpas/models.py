"Representation of wpa_supplicant constructs"
# pylint: disable=too-many-instance-attributes

from dataclasses import dataclass
from typing import List

from .const import STATUS_CONSTS
from .utils import safe_decode


@dataclass
class InterfaceStatus:
    "Represents a wifi interface status"
    bssibd: str
    frequency: int
    ssid: str
    id: str  # pylint: disable=invalid-name
    mode: str
    wpa_state: str
    pairwise_cipher: str
    group_cipher: str
    key_mgmt: str
    ip_address: str
    p2p_device_address: str
    address: str
    uuid: str

    def __str__(self):
        return f'wpa_state={self.wpa_state}'

    @staticmethod
    def deserialize(data):
        "Deserialize wpa_supplicant form of interface status to object"
        kwargs = {}
        for line in data:
            key, val = line.split(b'=')
            kwargs[safe_decode(key)] = safe_decode(val)
        kwargs['wpa_state'] = STATUS_CONSTS[kwargs['wpa_state'].lower()]
        kwargs['frequency'] = int(kwargs.pop('freq'))
        return InterfaceStatus(**kwargs)

    def serialize(self):
        "Serialize interface status to wpa_supplicant form"


@dataclass
class Network:
    "Represents a wifi network"
    bssid: str
    frequency: int
    signal_level: int
    flags: str
    ssid: str

    def __str__(self):
        return f'bssid={self.bssid}, frequency={self.frequency}, ' \
               f'signal_level={self.signal_level}, flags={self.flags}, ' \
               f'ssid={self.ssid}'

    @staticmethod
    def deserialize(header, network):
        "Deserialize wpa_supplicant form of network into object"
        kwargs = {}
        fields = safe_decode(header).split(' / ')
        fields = map(lambda x: x.strip().replace(' ', '_'), fields)
        values = safe_decode(network).split('\t')
        for i, field in enumerate(fields):
            try:
                kwargs[field] = values[i].strip()
            except IndexError:
                kwargs[field] = None
        kwargs['frequency'] = int(kwargs['frequency'])
        if not kwargs['ssid']:
            kwargs['ssid'] = None
        return Network(**kwargs)

    def serialize(self):
        "Serialize network into wpa_supplicant form"
        return '\t'.join((
            self.bssid, self.frequency, self.signal_level, self.flags, self.ssid
        )).encode('utf-8')


def deserialize_networks(lines: str) -> List[Network]:
    "Convert wpa_supplicant form of network list into objects"
    header = lines[0]
    return [
        Network.deserialize(header, l) for l in lines[1:]
    ]


def serialize_networks(networks):
    "Convert list of networks into wpa_supplicant form"
    header = b'bssid / frequency / signal level / flags / ssid\n'
    networks = b'\n'.join([network.serialize() for network in networks])
    return header + networks
