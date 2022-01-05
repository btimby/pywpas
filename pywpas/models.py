from dataclasses import dataclass
from typing import List

from .const import STATUS_CONSTS
from .utils import safe_decode


@dataclass
class InterfaceStatus:
    bssibd: str
    frequency: int
    ssid: str
    id: str
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
        kwargs = {}
        for l in data:
            k, v = l.split(b'=')
            kwargs[safe_decode(k)] = safe_decode(v)
        kwargs['wpa_state'] = STATUS_CONSTS[kwargs['wpa_state'].lower()]
        kwargs['frequency'] = int(kwargs.pop('freq'))
        return InterfaceStatus(**kwargs)

    def serialize(self):
        pass


@dataclass
class Network:
    bssid: str
    frequency: int
    signal_level: int
    flags: str
    ssid: str

    def __str__(self):
        key_mgmt = '|'.join(self.key_mgmt)
        return f'bssid={self.bssid}, freq={self.freq}, signal={self.signal},' \
               f' ssid={self.ssid}, key_mgmt={key_mgmt}, auth={auth}'

    @staticmethod
    def deserialize(header, network):
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
        key_mgmt = ','.join(self.key_mgmt)
        data = f'\n{self.bssid}\t{self.freq}\t{self.signal}\t' \
               f'{key_mgmt}\t{self.ssid}'
        return data.encode('utf-8')


def deserialize_networks(lines: str) -> List[Network]:
    header = lines[0]
    return [
        Network.deserialize(header, l) for l in lines[1:]
    ]


def serialize_networks(networks):
    header = b'bssid / frequency / signal level / flags / ssid\n'
    networks = b'\n'.join([network.serialize() for network in networks])
    return header + networks
