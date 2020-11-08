from __future__ import print_function
from PIL import Image, ImageDraw, ImageColor

sz = 256		# Image size
mg = 32			# Image magnification (line segment size)
width = 3		# Line width

# Utility function for mapping list of colors names
def get_colors(colors, mode='RGB'):
	if colors is None:
		colors = 'black'
	return list(map(lambda x: ImageColor.getcolor(x, mode), colors.split(',')))

def popcount(x):
	n = 0
	while x:
		n += 1
		x &= (x - 1)	# Clear the bottom-most set bit - cf snippet 0x2f
	return n

def hilbert_direction(idx):
	aa = 0xaa
	aa |= aa << 8
	aa |= aa << 16
	aa |= aa << 32
	r = popcount(idx & (idx & aa) >> 1) & 1
	s = popcount(-idx & (-idx & aa) >> 1) & 1
	return 1 - r - s, r - s

def draw_hilbert(n, mg, width=1, colors=None, mode='RGB'):
	# how much to shift lines by
	e = width >> 1
	# Calculate canvas size
	sz = mg * ((1 <<  n) - 1) + width
	pos = (e, e)
	img = Image.new(mode, (sz, sz), get_colors('white', mode)[0])
	draw = ImageDraw.Draw(img)
	colors = get_colors(colors, mode)
	for i in range(1, 1 << (n << 1)):
		dx, dy = hilbert_direction(i)
		npos = (pos[0] + mg * dx, pos[1] - mg * dy)
		line = [ pos, npos ]
		draw.line(line, fill=colors[(i - 1) % len(colors)], width=width)
		pos = npos
	return img

img = draw_hilbert(5, mg=16, colors='blue,red',width=7)
img.show()
img.save('xorpd_3c_hilbert.png', optimize=True, dpi=(150, 150))


