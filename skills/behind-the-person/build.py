#!/usr/bin/env python3
"""behind-the-person: a panel of graphics BEHIND the speaker (the speaker is cut out and sits on top of it),
big words on the chest as they are said, and a profile card that counts up.

    <kit>/.venv/bin/python build.py spec.json

Spec (see SKILL.md for every field):
  video, start, end, out, format
  panel: {type: grid | bars | image, ...}          the graphic behind the head
  chest: [{text, at}, ...]                          big words; "{count}" in a text counts up to card.count
  card:  {avatar, name, label, count, at, count_at, button, pressed, press_at}   optional
  panel_left, panel_top, panel_width, panel_height, chest_top, card_top, card_left    layout overrides
"""
import html
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'kit'))
from reel import Job, Comp, count_js, parse_number  # noqa: E402
import theme as T  # noqa: E402

CAR_ICON = ('<svg class="cico" viewBox="0 0 24 24" width="30" height="30"><rect x="7" y="3" width="14" height="14" rx="3" '
            'fill="none" stroke="#fff" stroke-width="2"/><path d="M4 7v11.5A2.5 2.5 0 0 0 6.5 21H17" fill="none" '
            'stroke="#fff" stroke-width="2" stroke-linecap="round"/></svg>')
GRID_ICON = ('<svg viewBox="0 0 24 24" width="30" height="30"><g fill="#fff"><rect x="3" y="3" width="7.5" height="7.5" rx="2"/>'
             '<rect x="13.5" y="3" width="7.5" height="7.5" rx="2"/><rect x="3" y="13.5" width="7.5" height="7.5" rx="2"/>'
             '<rect x="13.5" y="13.5" width="7.5" height="7.5" rx="2"/></g></svg>')


def panel_grid(j, c, p, PW, PH):
    imgs = j.images(p.get('images'))
    if not imgs:
        sys.exit('panel.images is empty')
    cols = int(p.get('columns', max(3, (PW - 48 + 9) // 287)))
    cw = (PW - 48 - (cols - 1) * 9) // cols
    ch = round(cw * 1.25)
    n = cols * 4
    tabs = p.get('tabs', ['Posts', 'Reels', 'Tagged'])
    hl = p.get('highlight') or {}
    hi = int(hl.get('index', 0))
    cells = []
    for i in range(n):
        src = imgs[i % len(imgs)]
        strip = [src] + (j.images(hl.get('slides')) if i == hi and hl else [])
        inner = ''.join(f'<img src="{c.asset(s)}">' for s in strip)
        cells.append(f'<div class="cell" id="cell{i}"><div class="strip">{inner}</div>{CAR_ICON if len(strip) > 1 or p.get("icons", True) else ""}</div>')
    head = ''.join(f'<b>{html.escape(t)}</b>' if k == 0 else f'<span>{html.escape(t)}</span>' for k, t in enumerate(tabs))
    label = hl.get('label')
    c.css.append(f'''#grid{{position:absolute;left:24px;top:124px;width:{PW - 48}px;display:grid;grid-template-columns:repeat({cols},{cw}px);gap:9px}}
.cell{{position:relative;width:{cw}px;height:{ch}px;overflow:hidden;border-radius:12px;background:{T.LINE}}}
.cell .strip{{display:flex;height:{ch}px}}
.cell img{{width:{cw}px;height:{ch}px;object-fit:cover;flex:none}}''')
    c.body.append(f'''<div id="ig" class="a"><div class="hd"><div class="igl">{GRID_ICON}</div>{head}</div>
<div id="grid">{''.join(cells)}{'<div id="hl" class="hid"></div>' if hl else ''}{f'<div id="hlc" class="hid">{html.escape(label)}</div>' if label else ''}</div></div>''')
    c.js.append(f'tl.fromTo("#grid",{{y:0}},{{y:{-int(p.get("scroll", 150))},duration:{c.dur:.3f},ease:"none"}},0);')
    if hl:
        col, row = hi % cols, hi // cols
        x, y = col * (cw + 9) - 5, row * (ch + 9) - 5
        ta = j.t(hl.get('at'), 0.6)
        c.js.append(f'''tl.set("#hl",{{left:{x},top:{y},width:{cw + 10},height:{ch + 10},visibility:"visible"}},{ta:.3f});
tl.fromTo("#hl",{{scale:1.12,autoAlpha:0}},{{scale:1,autoAlpha:1,duration:.24,ease:"power3.out"}},{ta:.3f});''')
        swipes = hl.get('swipe_at') or [ta + 0.33 + k * 0.6 for k in range(len(j.images(hl.get('slides'))))]
        for k, s in enumerate(swipes[:len(j.images(hl.get('slides')))]):
            c.js.append(f'tl.to("#cell{hi} .strip",{{x:{-cw * (k + 1)},duration:.32,ease:"power2.inOut"}},{j.t(s):.3f});')
        if label:
            tl_ = j.t(hl.get('label_at'), ta + 1.0)
            c.js.append(f'''tl.set("#hlc",{{left:{x + 21},top:{y + ch - 43},visibility:"visible"}},{tl_:.3f});
tl.fromTo("#hlc",{{scale:.6,autoAlpha:0}},{{scale:1,autoAlpha:1,duration:.22,ease:"back.out(2)"}},{tl_:.3f});''')


def panel_bars(j, c, p, PW, PH):
    bars = p.get('bars') or []
    if not bars:
        sys.exit('panel.bars is empty')
    top = max(float(b['value']) for b in bars) or 1
    n = len(bars)
    bw = min(150, (PW - 120 - (n - 1) * 26) / n)
    x0 = (PW - (n * bw + (n - 1) * 26)) / 2
    acc = p.get('color', T.ACCENT)
    hi = p.get('highlight', n - 1)
    hmax = PH - 350
    items = []
    for i, b in enumerate(bars):
        h = hmax * float(b['value']) / top
        x = x0 + i * (bw + 26)
        col = acc if i == hi else T.LINE
        items.append(f'<div class="bar" id="bar{i}" style="left:{x:.0f}px;width:{bw:.0f}px;height:{h:.0f}px;background:{col}"></div>'
                     f'<div class="bv" id="bv{i}" style="left:{x - 20:.0f}px;width:{bw + 40:.0f}px;bottom:{170 + h + 12:.0f}px;'
                     f'color:{acc if i == hi else T.INK}">{html.escape(str(b.get("show", b["value"])))}</div>'
                     f'<div class="bl" style="left:{x - 20:.0f}px;width:{bw + 40:.0f}px">{html.escape(str(b.get("label", "")))}</div>')
    c.css.append(f'''.bar{{position:absolute;bottom:170px;border-radius:18px 18px 6px 6px;transform-origin:50% 100%}}
.bv{{position:absolute;text-align:center;font:800 40px 'Inter';letter-spacing:-.03em}}
.bl{{position:absolute;bottom:110px;text-align:center;font:600 28px 'Inter';color:{T.MUTED}}}
#ig .ttl{{position:absolute;left:44px;top:40px;font:800 46px/1.1 'Inter';color:{T.INK};letter-spacing:-.04em}}''')
    c.body.append(f'<div id="ig" class="a"><div class="ttl">{html.escape(p.get("title", ""))}</div>{"".join(items)}</div>')
    t0 = j.t(p.get('at'), 0.3)
    for i in range(n):
        c.js.append(f'tl.fromTo("#bar{i}",{{scaleY:0}},{{scaleY:1,duration:.5,ease:"power3.out"}},{t0 + i * 0.12:.3f});'
                    f'tl.fromTo("#bv{i}",{{autoAlpha:0,y:20}},{{autoAlpha:1,y:0,duration:.3}},{t0 + i * 0.12 + 0.3:.3f});')


def panel_image(j, c, p, PW, PH):
    src = j.images(p.get('src'))[0]
    c.css.append(f'#ig img.shot{{position:absolute;left:0;top:0;width:{PW}px;height:auto}}')
    c.body.append(f'<div id="ig" class="a"><img class="shot" id="shot" src="{c.asset(src)}"></div>')
    c.js.append(f'tl.fromTo("#shot",{{y:0}},{{y:{-int(p.get("scroll", 200))},duration:{c.dur:.3f},ease:"none"}},0);')


def main(spec):
    j = Job(spec, 'behind-the-person')
    c = Comp(j)
    p = j.get('panel') or {}
    hz = j.horizontal
    PL = j.get('panel_left', j.pick(90, 340))
    PT = j.get('panel_top', j.pick(150, 80))
    PW = j.get('panel_width', j.pick(900, 1240))
    PH = j.get('panel_height', j.pick(870, 680))
    chest_top = j.get('chest_top', j.pick(1105, 770))
    card_top = j.get('card_top', j.pick(1235, 830))
    card_w, card_h = j.pick((740, 150), (640, 124))
    card_left = j.get('card_left', j.pick(170, 120))
    chest_size = j.pick(84, 76)
    c.css.append(f'''
#ig{{left:{PL}px;top:{PT}px;width:{PW}px;height:{PH}px;border-radius:44px;background:{T.SURFACE};overflow:hidden;
  box-shadow:{T.SHADOW_DARK},inset 0 0 0 1px rgba(11,11,15,.05)}}
#ig .hd{{position:absolute;left:0;top:0;width:{PW}px;height:112px;display:flex;align-items:center;gap:46px;padding:0 40px;
  font:600 36px 'Inter';color:{T.MUTED};z-index:2;background:{T.SURFACE};letter-spacing:-.02em}}
#ig .hd b{{color:{T.INK};font-weight:700;position:relative}}
#ig .hd b:after{{content:'';position:absolute;left:0;right:0;bottom:-30px;height:4px;background:{T.ACCENT};border-radius:2px}}
.igl{{width:54px;height:54px;border-radius:16px;background:{T.ACCENT};display:grid;place-items:center;flex:none}}
.cell .cico{{position:absolute;right:12px;top:12px;filter:drop-shadow(0 1px 3px rgba(0,0,0,.5))}}
#hl{{position:absolute;border:5px solid {T.ACCENT};border-radius:16px;box-shadow:0 0 0 4px rgba(255,255,255,.9),0 16px 40px {T.rgba(T.ACCENT, .45)}}}
#hlc{{position:absolute;padding:7px 15px;border-radius:30px;background:{T.ACCENT};color:#fff;font:700 26px 'Inter';white-space:nowrap}}
.big{{position:absolute;left:0;width:{c.W}px;top:{chest_top}px;text-align:center;font:800 {chest_size}px/1 'Inter';color:#fff;letter-spacing:-.045em;
  text-shadow:0 2px 6px rgba(0,0,0,.3),0 8px 30px rgba(0,0,0,.45);visibility:hidden}}
.big .n{{background:{T.ACCENT};padding:0 .16em .06em;border-radius:.18em;text-shadow:none}}
#pc{{left:{card_left}px;top:{card_top}px;width:{card_w}px;height:{card_h}px;border-radius:32px;background:rgba(255,255,255,.96);
  box-shadow:{T.SHADOW_DARK};display:flex;align-items:center;gap:22px;padding:0 24px;visibility:hidden}}
#pc img,#pc i{{width:{card_h - 50}px;height:{card_h - 50}px;border-radius:50%;object-fit:cover;flex:none}}
#pc i{{background:{T.ACCENT}}}
#pc .nm{{font:700 {j.pick(36, 32)}px/1.1 'Inter';color:{T.INK};letter-spacing:-.02em}}
#pc .sb{{font:500 {j.pick(27, 24)}px/1.3 'Inter';color:{T.MUTED}}}
#pc .sb b{{color:{T.ACCENT};font-weight:800}}
#pc .fb{{margin-left:auto;padding:{j.pick(16, 13)}px {j.pick(30, 26)}px;border-radius:40px;background:{T.ACCENT};color:#fff;font:700 {j.pick(30, 26)}px 'Inter'}}
''')
    full = f'position:absolute;left:0;top:0;width:{c.W}px;height:{c.H}px'
    c.body.append(c.video(j.clip, full, 'bg'))
    {'grid': panel_grid, 'bars': panel_bars, 'image': panel_image}[p.get('type', 'grid')](j, c, p, PW, PH)
    c.js.append('tl.fromTo("#ig",{y:60,autoAlpha:0,scale:.96},{y:0,autoAlpha:1,scale:1,duration:.42,ease:"power3.out"},0);')
    c.body.append(c.video(j.cutout(), full, 'cut'))

    card = j.get('card')
    count = parse_number(card.get('count')) if card and card.get('count') is not None else None
    count_ids = []
    chest = j.get('chest') or []
    times = [j.t(w.get('at')) for w in chest]
    for i, w in enumerate(chest):
        a = times[i]
        b = times[i + 1] if i + 1 < len(chest) else c.dur
        txt = html.escape(w['text'])
        if '{count}' in w['text']:
            txt = txt.replace('{count}', f'<span class="n" id="cnt{i}">0</span>')
            count_ids.append((f'cnt{i}', a, b))
        c.body.append(f'<div class="big" id="bw{i}">{txt}</div>')
        c.js.append(f'tl.set("#bw{i}",{{visibility:"visible"}},{a:.3f});tl.set("#bw{i}",{{visibility:"hidden"}},{b:.3f});'
                    f'tl.fromTo("#bw{i}",{{scale:.9,y:10}},{{scale:1,y:0,duration:.18,ease:"power3.out"}},{a:.3f});')
    if card:
        lab = html.escape(card.get('label', 'new followers'))
        num = '<b id="pcn">+0</b> ' if count else ''
        av = j.images(card['avatar'])[0] if card.get('avatar') else None
        pic = f'<img src="{c.asset(av)}">' if av else '<i></i>'
        c.body.append(f'<div id="pc" class="a">{pic}<div><div class="nm">{html.escape(card.get("name", ""))}</div>'
                      f'<div class="sb">{num}{lab}</div></div><div class="fb" id="fb">{html.escape(card.get("button", "Follow"))}</div></div>')
        ca = j.t(card.get('at'), 0.4)
        c.js.append(f'tl.fromTo("#pc",{{autoAlpha:0,y:30,scale:.96}},{{autoAlpha:1,y:0,scale:1,duration:.32,ease:"power3.out"}},{ca:.3f});')
        if card.get('pressed'):
            pa = j.t(card.get('press_at'), c.dur - 0.8)
            c.js.append(f'tl.set("#fb",{{textContent:{json.dumps(card["pressed"])},background:"{T.INK}"}},{pa:.3f});'
                        f'tl.fromTo("#fb",{{scale:.9}},{{scale:1,duration:.18,ease:"back.out(3)"}},{pa:.3f});')
    if count:
        to, fmt = count
        at = j.t(card.get('count_at'), count_ids[0][1] if count_ids else 1.0)
        c.js.append(count_js([i for i, _, _ in count_ids], to, at, fmt=fmt) if count_ids else '')
        c.js.append(count_js(['pcn'], to, at, fmt=fmt, prefix='+'))
    j.finish(c)


if __name__ == '__main__':
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    main(sys.argv[1])
