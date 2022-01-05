from unittest import TestCase

from pywpas.models import (
    InterfaceStatus, Network, deserialize_networks,
)


INTERFACE_STATUS = b'bssibd=08:02:8e:9c:9d:15\n' \
                   b'freq=2452\n' \
                   b'ssid=NachoWIFI\n' \
                   b'id=0\n' \
                   b'mode=station\n' \
                   b'pairwise_cipher=CCMP\n' \
                   b'group_cipher=CCMP\n' \
                   b'key_mgmt=WPA2-PSK\n' \
                   b'wpa_state=COMPLETED\n' \
                   b'ip_address=192.168.1.102\n' \
                   b'p2p_device_address=f8:59:71:93:d1:14\n' \
                   b'address=f8:59:71:93:d1:13\n' \
                   b'uuid=2ef7f1d9-83d9-5b92-9e5b-91b60c83ecf0'
SCAN_RESULTS = b'bssid / frequency / signal level / flags / ssid\n' \
               b'08:02:8e:9c:9d:15\t2452\t-36\t[WPA2-PSK-CCMP][ESS]\tNachoWIFI\n' \
               b'f8:2c:18:66:4b:ba\t5805\t-79\t[WPA2-PSK-CCMP][WPS][ESS]\tATT6YFg7Nq\n' \
               b'f8:2c:18:66:4b:ba\t5805\t-79\t[WPA2-PSK-CCMP][WPS][ESS]\t\n' \
               b'f8:2c:18:66:4b:b4\t2412\t-70\t[WPA2-PSK-CCMP][ESS]\t\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\n' \
               b'58:56:e8:4a:8f:4f\t5560\t-79\t[WPA2-PSK-CCMP][WPS][ESS]\tMotoVAP_M91336SA0R45\n' \
               b'f8:2c:18:66:4b:b1\t2412\t-75\t[WPA2-PSK-CCMP][WPS][ESS]\tATT6YFg7Nq\n' \
               b'76:69:42:03:45:bc\t2412\t-83\t[WPA2-PSK-CCMP][ESS]\tSpectrumSetup-BE\n' \
               b'58:d9:d5:90:dc:01\t2412\t-83\t[WPA-PSK-CCMP][WPA2-PSK-CCMP][ESS]\tSpectrumSetup-BE_EXT\n' \
               b'ea:47:32:75:69:88\t2437\t-79\t[WPA2-PSK-CCMP][ESS]\t\n' \
               b'62:45:b1:79:51:75\t5745\t-68\t[WEP][ESS]\t\n' \
               b'62:45:b1:be:d1:b5\t5220\t-79\t[WEP][ESS]'


class NetworkTestCase(TestCase):
    def test_deserialize_networks(self):
        networks = deserialize_networks(SCAN_RESULTS.split(b'\n'))
        self.assertEqual(11, len(networks))
        self.assertEqual(
            'bssid=08:02:8e:9c:9d:15, frequency=2452, signal_level=-36, flags=[WPA2-PSK-CCMP][ESS], ssid=NachoWIFI',
            str(networks[0]))

    def test_deserialize_interfacestatus(self):
        status = InterfaceStatus.deserialize(INTERFACE_STATUS.split(b'\n'))
        self.assertEqual('station', status.mode)
        self.assertEqual('wpa_state=COMPLETED', str(status))
