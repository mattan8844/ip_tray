from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

from PIL import Image

from ip_tray.menu_graph_image import render_single_history_graph


class MenuGraphImageTests(TestCase):
    def test_render_single_colored_graph_image(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "single.png"
            render_single_history_graph(
                samples=[0, 80, 140, 60, 220, 120],
                path=path,
                line_color=(51, 123, 214, 255),
                fill_color=(74, 144, 226, 70),
                width=180,
                height=32,
            )
            self.assertTrue(path.exists())

            with Image.open(path) as img:
                self.assertEqual(img.size, (180, 32))
