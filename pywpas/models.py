"Representation of wpa_supplicant constructs."
# pylint: disable=too-many-instance-attributes

from dataclasses import dataclass
from typing import List

from .utils import safe_decode


@dataclass
class InterfaceStatus:
    "Represents a wifi interface status."
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
        "Deserialize wpa_supplicant form of interface status to object."
        kwargs = {}
        for line in data:
            key, val = line.split(b'=')
            kwargs[safe_decode(key)] = safe_decode(val)
        kwargs['frequency'] = int(kwargs.pop('freq'))
        return InterfaceStatus(**kwargs)


@dataclass
class Profile:
    "Represents a wifi network in wpa_supplicant config file."
    id: int = None  # pylint: disable=invalid-name
    ssid: str = None
    key_mgmt: str = None
    proto: str = None
    ciphers: str = None
    psk: str = None

    def __str__(self):
        return f'id={self.id}, ssid={self.ssid}, key_mgmt={self.key_mgmt}, ' \
               f'proto={self.proto}, ciphers={self.ciphers}, psk={self.psk}'


@dataclass
class Scanned:
    "Represents a wifi network in wpa_supplicant config file."
    bssid: str = None
    frequency: int = None
    signal_level: int = None
    flags: str = None
    ssid: str = None

    def __str__(self):
        return f'bssid={self.bssid}, frequency={self.frequency}, ' \
               f'signal_level={self.signal_level}, flags={self.flags}, ' \
               f'ssid={self.ssid}'

    @staticmethod
    def deserialize(header, network):
        "Deserialize wpa_supplicant form of network into object."
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
        return Scanned(**kwargs)

    def as_profile(self, psk=None) -> Profile:
        "Convert to profile for connecting."
        return Profile(ssid=self.ssid, psk=psk)


def deserialize_scanned(lines: str) -> List[Scanned]:
    "Convert wpa_supplicant form of network list into objects."
    header = lines[0]
    return [
        Scanned.deserialize(header, l) for l in lines[1:]
    ]
