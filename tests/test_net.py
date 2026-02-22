from unittest import TestCase
from unittest.mock import Mock, patch

import requests

from ip_tray.net import (
    fixed_speed_token,
    get_flag_emoji_for_country,
    get_public_ip_and_country,
    human_speed,
    human_traffic_gb,
)


class NetFormattingTests(TestCase):
    def test_human_speed(self):
        self.assertEqual(human_speed(512), "512B/s")
        self.assertEqual(human_speed(3 * 1024), "3KB/s")
        self.assertEqual(human_speed(5 * 1024 * 1024), "5MB/s")

    def test_human_traffic_gb(self):
        gb = 1024.0 * 1024.0 * 1024.0
        self.assertEqual(human_traffic_gb(5 * gb), "5.00GB")
        self.assertEqual(human_traffic_gb(15 * gb), "15.0GB")
        self.assertEqual(human_traffic_gb(120 * gb), "120GB")

    def test_country_flag(self):
        self.assertEqual(get_flag_emoji_for_country("US"), "🇺🇸")
        self.assertEqual(get_flag_emoji_for_country(""), "🏳️")

    def test_fixed_speed_token_has_stable_width(self):
        samples = [0, 12, 1024, 5 * 1024 * 1024, 8 * 1024 * 1024 * 1024]
        tokens = [fixed_speed_token(v) for v in samples]
        self.assertTrue(all(len(token) == 5 for token in tokens))
        self.assertEqual(fixed_speed_token(1024), "   1K")
        self.assertEqual(fixed_speed_token(15), "  15B")


class PublicIpFallbackTests(TestCase):
    @patch("ip_tray.net.requests.get")
    def test_fallback_to_second_ip_provider(self, mock_get):
        first = Mock()
        first.raise_for_status.side_effect = requests.RequestException("boom")

        second = Mock()
        second.raise_for_status.return_value = None
        second.json.return_value = {"ip": "1.2.3.4"}

        geo = Mock()
        geo.raise_for_status.return_value = None
        geo.json.return_value = {"country": "jp"}

        mock_get.side_effect = [first, second, geo]

        ip, cc = get_public_ip_and_country(timeout=0.1)

        self.assertEqual(ip, "1.2.3.4")
        self.assertEqual(cc, "JP")

    @patch("ip_tray.net.requests.get")
    def test_returns_empty_when_all_sources_fail(self, mock_get):
        failed = Mock()
        failed.raise_for_status.side_effect = requests.RequestException("boom")
        mock_get.side_effect = [failed, failed, failed, failed, failed]

        ip, cc = get_public_ip_and_country(timeout=0.1)

        self.assertEqual(ip, "")
        self.assertEqual(cc, "")
