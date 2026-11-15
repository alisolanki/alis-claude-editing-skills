"""The house style: one accent, Inter everywhere, flat surfaces, generous radii, soft shadows.

Every skill pulls its colours from here, so the whole kit can be re-themed in one place.
Set EDIT_ACCENT (a #rrggbb hex) in the environment to try another accent without touching code.
"""
import os
import re

_env = os.environ.get('EDIT_ACCENT', '').strip()
ACCENT = _env if re.fullmatch(r'#[0-9a-fA-F]{6}', _env) else '#5000fa'


def rgb(hex_):
    h = hex_.lstrip('#')
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def rgba(hex_, a):
    r, g, b = rgb(hex_)
    return f'rgba({r},{g},{b},{a})'


def mix(hex_a, hex_b, t):
    """t=0 -> a, t=1 -> b"""
    a, b = rgb(hex_a), rgb(hex_b)
    return '#' + ''.join(f'{round(x + (y - x) * t):02x}' for x, y in zip(a, b))


ACCENT_RGB = rgb(ACCENT)
ACCENT_SOFT = mix(ACCENT, '#ffffff', 0.88)     # a pale tint for light surfaces
ACCENT_LIGHT = mix(ACCENT, '#ffffff', 0.45)    # readable accent on dark backgrounds
ACCENT_DEEP = mix(ACCENT, '#000000', 0.35)

INK = '#0b0b0f'          # text on light
PAPER = '#f6f6f8'        # light backdrop
SURFACE = '#ffffff'      # cards on light
MUTED = '#8b8b96'        # secondary text
LINE = '#e4e4ea'         # hairlines on light
NIGHT = '#0c0c10'        # dark backdrop
NIGHT_SURFACE = '#17171d'
NIGHT_LINE = 'rgba(255,255,255,.08)'

FONT = "'Inter'"
RADIUS = 28
SHADOW = '0 24px 60px rgba(10,10,20,.22)'
SHADOW_DARK = '0 30px 80px rgba(0,0,0,.55)'

# a monochrome ramp from the accent, for tiers, bars and other ordered sets
def ramp(n):
    if n <= 1:
        return [ACCENT]
    return [mix(ACCENT, '#ffffff', 0.62 * i / (n - 1)) for i in range(n)]


def on(hex_):
    """black or white text, whichever reads on this background"""
    r, g, b = rgb(hex_)
    return INK if (0.299 * r + 0.587 * g + 0.114 * b) > 150 else '#ffffff'
