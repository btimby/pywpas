from unittest import TestCase

from pywpas.models import Network


SCAN_RESULTS = b'bssid / frequency / signal level / flags / ssid\n08:02:8e:9c:9d:15\t2452\t-36\t[WPA2-PSK-CCMP][ESS]\tNachoWIFI\nf8:2c:18:66:4b:ba\t5805\t-79\t[WPA2-PSK-CCMP][WPS][ESS]\tATT6YFg7Nq\nf8:2c:18:66:4b:ba\t5805\t-79\t[WPA2-PSK-CCMP][WPS][ESS]\t\nf8:2c:18:66:4b:b4\t2412\t-70\t[WPA2-PSK-CCMP][ESS]\t\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\n58:56:e8:4a:8f:4f\t5560\t-79\t[WPA2-PSK-CCMP][WPS][ESS]\tMotoVAP_M91336SA0R45\nf8:2c:18:66:4b:b1\t2412\t-75\t[WPA2-PSK-CCMP][WPS][ESS]\tATT6YFg7Nq\n76:69:42:03:45:bc\t2412\t-83\t[WPA2-PSK-CCMP][ESS]\tSpectrumSetup-BE\n58:d9:d5:90:dc:01\t2412\t-83\t[WPA-PSK-CCMP][WPA2-PSK-CCMP][ESS]\tSpectrumSetup-BE_EXT\nea:47:32:75:69:88\t2437\t-79\t[WPA2-PSK-CCMP][ESS]\t\n62:45:b1:79:51:75\t5745\t-68\t[WEP][ESS]\t\n62:45:b1:be:d1:b5\t5220\t-79\t[WEP][ESS]'


class NetworkTestCase(TestCase):
    def test_network_deserialize(self):
        pass
