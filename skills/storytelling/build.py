#!/usr/bin/env python3
"""storytelling: three simple image cards, a boxed title and a small accent subtitle under them, all landing
together, over one continuous take with simple captions. Vertical: the cards run across the top. Horizontal: they sit
on one side and the take is shifted so the face sits on the other.

    <kit>/.venv/bin/python build.py spec.json

Spec (see SKILL.md):
  video, start, end, out, format
  side: "right", face_x: 960                              horizontal only
  cards: [3 x {type: image | cover | stat | comments | text, ...}]
  title: ["I made this carousel", "in a few minutes"]     one black box per line
  subtitle: "and it's doing extremely well"
  zoom: 1.30                                              punch-in on the take (1 = none)
"""
import html
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'kit'))
from reel import Job, Comp, caption_css, count_js, cover_html, parse_number, word_caps  # noqa: E402
import theme as T  # noqa: E402

DOTS = T.ramp(5)


def card(j, c, i, k, x, y):
    t = k.get('type', 'image')
    st = f'left:{x}px;top:{y}px'
    if t == 'image':
        src = j.images(k.get('src'))[0]
        return f'<div class="sc" id="c{i}" style="{st}"><img src="{c.asset(src)}" style="width:296px;height:296px;object-fit:cover"></div>'
    if t == 'cover':
        img = (j.images(k.get('image')) or [None])[0]
        c.js.append(f'tl.fromTo("#c{i} .cover",{{y:0}},{{y:-60,duration:{c.dur - 0.1:.3f},ease:"none"}},0.1);')
        return f'<div class="sc" id="c{i}" style="{st}">{cover_html(c, 296, img, k.get("text", ""), k.get("cta", "SWIPE →"))}</div>'
    if t == 'stat':
        val = str(k.get('value', ''))
        num = parse_number(val)
        ring = float(k.get('ring', 0.75))
        if num:
            c.js.append(count_js([f'n{i}'], num[0], j.t(k.get('at'), 0.15), dur=float(k.get('count_for', 1.6)), fmt=num[1]))
        c.js.append(f'tl.to("#rg{i}",{{strokeDashoffset:{490 * (1 - ring):.0f},duration:{float(k.get("count_for", 1.6))},ease:"power1.out"}},{j.t(k.get("at"), 0.15):.3f});')
        return (f'<div class="sc" id="c{i}" style="{st}"><div class="lb">{html.escape(k.get("label", ""))}</div>'
                f'<svg width="180" height="180" viewBox="0 0 180 180"><circle cx="90" cy="90" r="78" fill="none" stroke="{T.LINE}" stroke-width="12"/>'
                f'<circle id="rg{i}" cx="90" cy="90" r="78" fill="none" stroke="{T.ACCENT}" stroke-width="12" stroke-linecap="round" '
                f'stroke-dasharray="490" stroke-dashoffset="490" transform="rotate(-90 90 90)"/></svg>'
                f'<div class="n" id="n{i}">{"0" if num else html.escape(val)}</div><div class="u">{html.escape(k.get("unit", ""))}</div></div>')
    if t == 'comments':
        rows = ''.join(f'<div class="cr"><i style="background:{DOTS[q % len(DOTS)]}"></i><div><div class="h">{html.escape(h)} · 1m</div>'
                       f'<div class="t">{html.escape(tx)}</div></div></div>' for q, (h, tx) in enumerate(k.get('rows', [])[:4]))
        return f'<div class="sc cm" id="c{i}" style="{st}"><div class="hd">{html.escape(k.get("title", "Comments"))}</div>{rows}</div>'
    if t == 'text':
        return (f'<div class="sc tx" id="c{i}" style="{st}"><div class="big">{html.escape(k.get("big", ""))}</div>'
                f'<div class="sm">{html.escape(k.get("small", ""))}</div></div>')
    sys.exit(f'card type {t} is not one of image, cover, stat, comments, text')


def main(spec):
    j = Job(spec, 'storytelling')
    c = Comp(j)
    S = float(j.get('zoom', 1.30))
    hz = j.horizontal
    if hz:
        side = j.get('side', 'right')
        vw, vh = 1920 * S, 1080 * S
        target = 560 if side == 'right' else 1360
        vx = min(0, max(1920 - vw, target - float(j.get('face_x', 960)) * S))
        vy = -(vh - 1080) / 2
        face = vx + float(j.get('face_x', 960)) * S
        x0 = 1920 - 120 - 3 * 272 - 2 * 16 if side == 'right' else 120
        xs, cy = [x0 + q * 288 for q in range(3)], 150
        tx, tw = x0, 3 * 272 + 32
        ty = 470
        cap = caption_css('tk', j.get('caption_top', 860), 1100, size=60, left=round(min(1920 - 1220, max(120, face - 550))))
        scale_card = 'transform:scale(.919);transform-origin:0 0'
    else:
        vx, vy = -(1080 * S - 1080) / 2, 0
        vw, vh = 1080 * S, 1920 * S
        xs, cy = [78, 392, 706], 212
        tx, tw, ty = 0, 1080, 528
        cap = caption_css('tk', j.get('caption_top', 1385), 1080, size=72)
        scale_card = ''
    c.css.append(f'''
.sc{{position:absolute;width:296px;height:296px;border-radius:32px;background:{T.SURFACE};overflow:hidden;box-shadow:{T.SHADOW};{scale_card}}}
.sc .lb{{position:absolute;left:0;right:0;top:40px;text-align:center;font:700 24px 'Inter';color:{T.MUTED};letter-spacing:.12em}}
.sc svg{{position:absolute;left:58px;top:82px}}
.sc .n{{position:absolute;left:0;right:0;top:132px;text-align:center;font:800 56px/1 'Inter';color:{T.INK};letter-spacing:-.04em}}
.sc .u{{position:absolute;left:0;right:0;top:192px;text-align:center;font:600 22px 'Inter';color:{T.MUTED}}}
.cm .hd{{padding:22px 22px 8px;text-align:center;font:700 24px 'Inter';color:{T.INK}}}
.cr{{display:flex;align-items:center;gap:12px;padding:8px 18px}}
.cr i{{width:40px;height:40px;border-radius:50%;flex:none}}
.cr .h{{font:500 16px/1.1 'Inter';color:{T.MUTED}}}
.cr .t{{font:700 23px/1.1 'Inter';color:{T.INK};letter-spacing:-.01em;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;max-width:200px}}
.tx{{display:flex;flex-direction:column;align-items:center;justify-content:center;gap:10px;padding:20px;text-align:center}}
.tx .big{{font:800 84px/1 'Inter';color:{T.ACCENT};letter-spacing:-.05em}}
.tx .sm{{font:600 24px/1.2 'Inter';color:{T.MUTED}}}
.tb{{position:absolute;left:{tx}px;width:{tw}px;text-align:center}}
.tb span{{display:inline-block;background:{T.SURFACE};color:{T.INK};font:800 {j.pick(70, 60)}px/1 'Inter';letter-spacing:-.045em;
  padding:12px 26px 16px;border-radius:20px;box-shadow:{T.SHADOW}}}
#sub span{{background:{T.ACCENT};color:#fff;font:700 {j.pick(40, 34)}px/1 'Inter';letter-spacing:-.02em;padding:10px 20px 13px;border-radius:14px}}
{cap}
''')
    c.body.append(c.video(j.clip, f'position:absolute;left:{vx:.0f}px;top:{vy:.0f}px;width:{vw:.0f}px;height:{vh:.0f}px', 'bg'))
    cards = (j.get('cards') or [])[:3]
    if len(cards) != 3:
        sys.exit('storytelling needs exactly 3 cards')
    ids = []
    for i, k in enumerate(cards):
        c.body.append(card(j, c, i, k, xs[i], cy))
        ids.append(f'#c{i}')
    y = ty
    for n, line in enumerate(j.get('title') or []):
        c.body.append(f'<div class="tb" id="t{n}" style="top:{y}px"><span>{html.escape(line)}</span></div>')
        ids.append(f'#t{n}')
        y += j.pick(100, 88)
    if j.get('subtitle'):
        c.body.append(f'<div class="tb" id="sub" style="top:{y + 12}px"><span>{html.escape(j.get("subtitle"))}</span></div>')
        ids.append('#sub')
    # everything lands together (one beat, not one at a time)
    c.js.insert(0, f'tl.fromTo({ids},{{autoAlpha:0,y:24}},{{autoAlpha:1,y:0,duration:.34,stagger:.025,ease:"power3.out"}},0.02);'.replace("'", '"'))
    word_caps(c, j.words, 'tk', '', maxw=3, maxc=15, keys=j.get('keys', []))
    j.finish(c)


if __name__ == '__main__':
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    main(sys.argv[1])
