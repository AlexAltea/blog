from __future__ import print_function
from PIL import Image, ImageDraw, ImageColor

n = 5      # Generation number
mg = 32    # Image magnification (line segment size)
width = 3  # Line width

def morton(n):
    pos = [ 0, 0 ]
    yield tuple(pos)
    for i in range(1, 1 << (2 * n)):
        k = 1
        while True:
            pos[0] ^= k
            k &= ~pos[0]
            if not k:
                break
            pos[1] ^= k
            k &= ~pos[1]
            if not k:
                break
            k <<= 1
        yield tuple(pos)

def disinterleave(z):
    x = 0
    y = 0
    k = 0
    while z:
        x |= (z & 1) << k
        y |= (z & 2) << k
        z >>= 2
        k += 1
    y >>= 1
    return x, y

def interleave(x, y):
    z = 0
    y <<= 1
    k = 0
    while x or y:
        z |= ((x & 1) | (y & 2)) << k
        x >>= 1
        y >>= 1
        k += 2
    return z

def morton2(n):
    for i in range(1 << (2 * n)):
        yield disinterleave(i)

def scale_point(pt, corner, mg):
    return corner[0] + pt[0] * mg, corner[1] + pt[1] * mg

def draw_morton(n, mg, width, color='black'):
    sz = width + mg * ((1 << n) - 1)
    img = Image.new('RGB', (sz, sz), ImageColor.getcolor('white', 'RGB'))
    draw = ImageDraw.Draw(img)
    gen = morton(n)
    corner = (width >> 1, width >> 1)
    scaler = lambda x: scale_point(x, corner, mg)
    pos = next(gen)
    for npos in gen:
        draw.line(list(map(scaler, [ pos, npos ])), fill=ImageColor.getcolor(color, img.mode), width=width)
        pos = npos
    return img

img = draw_morton(5, mg=16, color='black', width=1)
img.show()
img.save('xorpd_0x3d_morton.png', optimize=True, dpi=(150, 150))
