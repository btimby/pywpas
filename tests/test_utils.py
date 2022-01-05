from unittest import TestCase

from pywpas.utils import safe_decode


class DecodeTestCase(TestCase):
    def test_decode_str(self):
        self.assertEqual('foobar', safe_decode('foobar'))

    def test_decode_bytes(self):
        self.assertEqual('foobar', safe_decode(b'foobar'))
