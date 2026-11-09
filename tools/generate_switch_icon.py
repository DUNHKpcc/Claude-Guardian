"""Generate the original Guardian Switch icon without external imaging dependencies."""
from pathlib import Path
import struct
import zlib

OUTPUT = Path(__file__).resolve().parents[1] / 'skills/claude-guardian/assets/killswitch'
SHIELD = [(128,43),(193,66),(187,132),(169,173),(128,207),(87,173),(69,132),(63,66)]
CHECK = [(96,123),(119,146),(161,99)]


def inside(x, y, points):
    hit = False
    j = len(points) - 1
    for i, (xi, yi) in enumerate(points):
        xj, yj = points[j]
        if (yi > y) != (yj > y) and x < (xj-xi)*(y-yi)/(yj-yi)+xi:
            hit = not hit
        j = i
    return hit


def distance(x, y, a, b):
    dx, dy = b[0]-a[0], b[1]-a[1]
    t = max(0, min(1, ((x-a[0])*dx+(y-a[1])*dy)/(dx*dx+dy*dy)))
    return ((x-a[0]-t*dx)**2+(y-a[1]-t*dy)**2)**.5


def chunk(kind, data):
    return struct.pack('!I', len(data)) + kind + data + struct.pack('!I', zlib.crc32(kind+data))


def render():
    rows = bytearray()
    for y in range(256):
        rows.append(0)
        for x in range(256):
            colors = []
            for ox, oy in ((.25,.25),(.75,.25),(.25,.75),(.75,.75)):
                px, py = x+ox, y+oy
                radius = ((px-min(208,max(48,px)))**2 + (py-min(208,max(48,py)))**2)**.5
                c = (35,78,67,255) if radius <= 48 else (0,0,0,0)
                if inside(px,py,SHIELD): c = (232,242,227,255)
                if any(distance(px,py,a,b) <= 7 for a,b in zip(CHECK,CHECK[1:])): c = (35,78,67,255)
                colors.append(c)
            rows.extend(round(sum(c[i] for c in colors)/4) for i in range(4))
    png = b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR',struct.pack('!2I5B',256,256,8,6,0,0,0)) + chunk(b'IDAT',zlib.compress(rows,9)) + chunk(b'IEND',b'')
    svg = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 256 256"><rect width="256" height="256" rx="48" fill="#234e43"/><path d="M128 43 193 66 187 132 169 173 128 207 87 173 69 132 63 66Z" fill="#e8f2e3"/><path d="m96 123 23 23 42-47" fill="none" stroke="#234e43" stroke-width="14" stroke-linecap="round" stroke-linejoin="round"/></svg>\n'
    return {'icon.png':png, 'icon.svg':svg.encode(),
            'icon.ico':struct.pack('<HHH',0,1,1)+struct.pack('<BBBBHHII',0,0,0,0,1,32,len(png),22)+png,
            'icon.icns':b'icns'+struct.pack('!I',len(png)+16)+b'ic08'+struct.pack('!I',len(png)+8)+png}


if __name__ == '__main__':
    for name, data in render().items():
        (OUTPUT/name).write_bytes(data)
    print('Generated SVG, PNG, ICO and ICNS icons')
