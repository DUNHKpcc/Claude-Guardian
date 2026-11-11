"""Build Switch icons from the supplied logo; regeneration uses macOS sips."""
import base64
from pathlib import Path
import struct
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'tools/assets/claude-color.png'
OUTPUT = ROOT / 'skills/claude-guardian/assets/killswitch'


def render():
    with tempfile.TemporaryDirectory() as directory:
        resized = Path(directory) / 'icon.png'
        subprocess.run(['sips', '-z', '256', '256', str(SOURCE), '--out', str(resized)],
                       check=True, capture_output=True)
        png = resized.read_bytes()
    encoded = base64.b64encode(png).decode('ascii')
    svg = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 256 256">'
           '<image width="256" height="256" href="data:image/png;base64,' + encoded + '"/></svg>\n')
    return {'icon.png': png, 'icon.svg': svg.encode(),
            'icon.ico': struct.pack('<HHH', 0, 1, 1) + struct.pack('<BBBBHHII', 0, 0, 0, 0, 1, 32, len(png), 22) + png,
            'icon.icns': b'icns' + struct.pack('!I', len(png) + 16) + b'ic08' + struct.pack('!I', len(png) + 8) + png}


if __name__ == '__main__':
    for name, data in render().items():
        (OUTPUT / name).write_bytes(data)
    print('Generated SVG, PNG, ICO and ICNS icons from supplied logo')
