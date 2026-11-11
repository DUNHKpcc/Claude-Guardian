"""Verify native icon containers and reproducible generation from the supplied logo."""
import base64
import importlib.util
from pathlib import Path
import shutil
import struct
import unittest
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / 'skills/claude-guardian/assets/killswitch'


class SwitchIcons(unittest.TestCase):
    def test_native_containers_embed_the_displayed_logo(self):
        png = (ASSETS / 'icon.png').read_bytes()
        self.assertEqual(struct.unpack('!II', png[16:24]), (256, 256))
        ico = (ASSETS / 'icon.ico').read_bytes()
        self.assertEqual(struct.unpack('<HHH', ico[:6]), (0, 1, 1))
        width, height, _, _, planes, depth, size, offset = struct.unpack('<BBBBHHII', ico[6:22])
        self.assertEqual((width, height, planes, depth, size, offset), (0, 0, 1, 32, len(png), 22))
        self.assertEqual(ico[offset:], png)
        icns = (ASSETS / 'icon.icns').read_bytes()
        self.assertEqual(icns[:4], b'icns')
        self.assertEqual(struct.unpack('!I', icns[4:8])[0], len(icns))
        self.assertEqual(icns[8:12], b'ic08')
        self.assertEqual(struct.unpack('!I', icns[12:16])[0], len(png) + 8)
        self.assertEqual(icns[16:], png)
        image = ET.parse(ASSETS / 'icon.svg').getroot().find('{http://www.w3.org/2000/svg}image')
        self.assertEqual(base64.b64decode(image.attrib['href'].split(',', 1)[1]), png)

    @unittest.skipUnless(shutil.which('sips'), 'Icon regeneration uses macOS sips')
    def test_generator_reproduces_committed_icons(self):
        spec = importlib.util.spec_from_file_location('switch_icon', ROOT / 'tools/generate_switch_icon.py')
        generator = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(generator)
        for name, expected in generator.render().items():
            self.assertEqual((ASSETS / name).read_bytes(), expected, name)


if __name__ == '__main__':
    unittest.main()
