from unittest import TestCase

from ip_tray.graph import render_speed_sparkline


class GraphRenderTests(TestCase):
    def test_fixed_width_output(self):
        line = render_speed_sparkline([1, 2, 3], width=20)
        self.assertEqual(len(line), 20)

    def test_empty_samples_returns_baseline(self):
        line = render_speed_sparkline([], width=12)
        self.assertEqual(line, "▁" * 12)

    def test_downsample_keeps_shape(self):
        samples = [0.0] * 100 + [100.0] * 100
        line = render_speed_sparkline(samples, width=20)
        self.assertTrue(line[:8].count("▁") >= 6)
        self.assertTrue(line[-8:].count("█") >= 6)
