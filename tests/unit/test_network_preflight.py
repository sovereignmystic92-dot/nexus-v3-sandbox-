import errno
from pathlib import Path
import socket
import sys
import unittest
from unittest.mock import patch, MagicMock

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'tools'))
from container_probe import credential_names, denied_probe


class NetworkPreflightTests(unittest.TestCase):
    def test_api_keys_and_proxy_credentials_are_detected_by_name(self):
        self.assertEqual(credential_names(['LANG', 'GEMINI_API_KEY', 'https_proxy_password']),
                         ['GEMINI_API_KEY', 'https_proxy_password'])

    def test_successful_udp_send_is_not_a_denial(self):
        with patch('container_probe.socket.socket', return_value=MagicMock()):
            self.assertFalse(denied_probe(socket.AF_INET, socket.SOCK_DGRAM, ('192.0.2.1',53)))

    def test_explicit_network_denial_or_unsupported_ipv6_passes(self):
        for code in (errno.ENETUNREACH, errno.EAFNOSUPPORT):
            with patch('container_probe.socket.socket', side_effect=OSError(code,'synthetic')):
                self.assertTrue(denied_probe(socket.AF_INET6,socket.SOCK_STREAM,('2001:db8::1',443)))

    def test_timeout_does_not_prove_denial(self):
        with patch('container_probe.socket.socket', side_effect=TimeoutError()):
            self.assertFalse(denied_probe(socket.AF_INET,socket.SOCK_STREAM,('192.0.2.1',443)))
