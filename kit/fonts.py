#!/usr/bin/env python3
"""TTF copies of the bundled WOFF2 fonts, for tools that cannot read WOFF2 (Pillow draws the long-form captions).

    python kit/fonts.py            # converts once into kit/fonts/.ttf/ (ignored by git)
"""
from pathlib import Path

KIT = Path(__file__).resolve().parent
SRC = KIT / 'fonts'
DST = SRC / '.ttf'


def ttf(name):
    """path to a TTF version of fonts/<name>.woff2 (or a bundled .ttf), converting on first use"""
    direct = SRC / name
    if direct.suffix == '.ttf' and direct.exists():
        return direct
    stem = Path(name).stem
    out = DST / f'{stem}.ttf'
    if out.exists():
        return out
    from fontTools.ttLib import TTFont
    DST.mkdir(exist_ok=True)
    f = TTFont(str(SRC / f'{stem}.woff2'))
    f.flavor = None
    f.save(str(out))
    return out


if __name__ == '__main__':
    for w in sorted(SRC.glob('*.woff2')):
        print(ttf(w.name))
