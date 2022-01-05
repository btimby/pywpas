from dataclasses import dataclass


@dataclass
class InterfaceStatus:
    wpa_state: str


@dataclass
class Network:
    bssid: str
    freq: int
    signal: int
    ssid: str
    key_mgmt: list
    auth: str

    @staticmethod
    def deserialize(data):
        bssid, freq, signal, akm, ssid = data.split('\t')
        key_mgmt = []
        auth = ''
        return Network(bssid, freq, signal, ssid, key_mgmt, auth)

    def serialize(self):
        key_mgmt = ','.join(self.key_mgmt)
        data = f'\n{self.bssid}\t{self.freq}\t{self.signal}\t' \
               f'{key_mgmt}\t{self.ssid}'
        return data.encode('utf-8')
