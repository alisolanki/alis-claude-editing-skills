#!/usr/bin/env python3
"""split-screen: visuals in one half, the speaker in the other, captions on the seam between them.

    <kit>/.venv/bin/python build.py spec.json

Vertical: visuals on top, speaker at the bottom. Horizontal: visuals on the left, speaker on the right.

Spec (see SKILL.md):
  video, start, end, out, format
  badge: "Step 1"   headline: "Find a *viral* carousel"      (*word* = accent)
  visual: {type: grid-pick | image | checklist, ...}       what explains the point, in a window
  video_top: -430                                           vertical: moves the speaker inside the bottom half (face in frame)
  face_x: 960, zoom: 1.0                                    horizontal: centres the face in the right half
"""
import html
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'kit'))
from reel import Job, Comp, bare, groups, rich  # noqa: E402
import theme as T  # noqa: E402

STAR = ('<svg width="40" height="40" viewBox="0 0 100 100"><g stroke="#fff" stroke-width="11" stroke-linecap="round">'
        + ''.join(f'<line x1="50" y1="50" x2="{50+42*math.cos(a*0.5236):.1f}" y2="{50+42*math.sin(a*0.5236):.1f}"/>' for a in range(12))
        + '</g></svg>')
CURSOR = ('<svg id="cur" class="a" viewBox="0 0 24 24"><path d="M5 2.5v17.2l4.6-4.3 2.9 6.6 3-1.3-2.9-6.5h6.3z" fill="#111" '
          'stroke="#fff" stroke-width="1.6" stroke-linejoin="round"/></svg>')
LENS = ('<svg width="26" height="26" viewBox="0 0 24 24" style="margin-right:12px"><circle cx="10.5" cy="10.5" r="6.5" fill="none" '
        'stroke="#777" stroke-width="2.4"/><path d="M15.5 15.5l5 5" stroke="#777" stroke-width="2.4" stroke-linecap="round"/></svg>')


def window(inner, bar_text):
    return (f'<div id="win" class="a"><div class="bar"><div class="dot"></div><div class="dot"></div>'
            f'<div class="dot"></div><div class="sr">{LENS}{html.escape(bar_text)}</div></div>{inner}</div>')


def grid_pick(j, c, v):
    imgs = j.images(v.get('images'))
    if not imgs:
        sys.exit('visual.images is empty')
    n = min(16, max(8, len(imgs)))
    chips = v.get('chips') or []
    cells = ''.join(f'<div class="lc" id="lc{i}"><img src="{c.asset(imgs[i % len(imgs)])}">'
                    + (f'<div class="chip">{html.escape(chips[i % len(chips)])}</div>' if chips else '') + '</div>' for i in range(n))
    pick = int(v.get('pick', 5)) % n
    col, row = pick % 4, pick // 4
    px, py = 26 + col * 204, 100 + row * 252
    pick_at = j.t(v.get('pick_at'), min(c.dur * 0.6, 3.36))
    move_at = max(0.2, pick_at - 0.66)
    scroll = int(v.get('scroll', 150 if row >= 1 else 0))
    c.body.append(window(f'<div id="lib">{cells}</div><div id="pick" class="hid"></div>', v.get('search', 'search')))
    c.js.append(f'''tl.fromTo("#lib",{{y:0}},{{y:{-scroll},duration:{move_at:.3f},ease:"power1.inOut"}},0);
tl.set("#cur",{{x:900,y:1000}},0);
tl.to("#cur",{{x:{110+px+120},y:{410+py-scroll+130},duration:.55,ease:"power2.inOut"}},{move_at:.3f});
tl.to("#cur",{{scale:.82,duration:.07,yoyo:true,repeat:1}},{pick_at-0.08:.3f});
tl.to(".lc:not(#lc{pick})",{{opacity:.35,duration:.25}},{pick_at:.3f});
tl.to("#lc{pick}",{{scale:1.1,duration:.25,ease:"back.out(2)",zIndex:4}},{pick_at:.3f});
tl.set("#pick",{{left:{px-11},top:{py-scroll-11},width:212,height:260,visibility:"visible"}},{pick_at:.3f});
tl.fromTo("#pick",{{autoAlpha:0}},{{autoAlpha:1,duration:.15}},{pick_at:.3f});''')
    if chips:
        c.js.append(f'tl.fromTo(".chip",{{scale:0,autoAlpha:0}},{{scale:1,autoAlpha:1,duration:.2,stagger:.035,ease:"back.out(2.5)"}},{j.t(v.get("chips_at"), 0.6):.3f});')
    if v.get('button'):
        ba = j.t(v.get('button_at'), pick_at + 0.6)
        ca = j.t(v.get('click_at'), ba + 0.45)
        c.body.append(f'<div id="btn" class="a hid">{html.escape(v["button"])}</div>')
        c.js.append(f'''tl.set("#btn",{{visibility:"visible"}},{ba:.3f});
tl.fromTo("#btn",{{y:20,autoAlpha:0,scale:.9}},{{y:0,autoAlpha:1,scale:1,duration:.24,ease:"back.out(2)"}},{ba:.3f});
tl.to("#cur",{{x:640,y:850,duration:.32,ease:"power2.inOut"}},{ba+0.05:.3f});
tl.to("#cur",{{scale:.82,duration:.07,yoyo:true,repeat:1}},{ca:.3f});
tl.to("#btn",{{background:"{T.ACCENT}",scale:.95,duration:.1,yoyo:true,repeat:1}},{ca:.3f});''')
        fan = j.images(v.get('fan'))[:3]
        fa = j.t(v.get('fan_at'), ca + 0.12)
        for k, s in enumerate(fan):
            c.body.append(f'<div class="sl hid a" id="sl{k}"><img src="{c.asset(s)}"></div>')
            c.js.append(f'tl.set("#sl{k}",{{left:{110+px},top:{410+py-scroll},visibility:"visible",zIndex:5}},{fa:.3f});'
                        f'tl.fromTo("#sl{k}",{{x:0,y:0,rotation:0,autoAlpha:0}},{{x:{434+k*150-col*204},y:{42+scroll-row*252+k*40},'
                        f'rotation:{-8+k*8},autoAlpha:1,duration:.3,ease:"power3.out"}},{fa+k*0.05:.3f});')


def image(j, c, v):
    src = j.images(v.get('src'))[0]
    c.css.append('#win img.shot{position:absolute;left:0;top:78px;width:860px;height:auto}')
    c.body.append(window(f'<img class="shot" id="shot" src="{c.asset(src)}">', v.get('bar', '')))
    c.js.append(f'tl.fromTo("#shot",{{y:0}},{{y:{-int(v.get("scroll", 120))},duration:{c.dur:.3f},ease:"power1.inOut"}},0);'
                'gsap.set("#cur",{autoAlpha:0});')


def checklist(j, c, v):
    items = v.get('items') or []
    rows = ''.join(f'<div class="ck" id="ck{i}"><div class="bx"><svg viewBox="0 0 24 24" width="34" height="34"><path d="M5 12.5l4.5 4.5L19 7.5" '
                   f'fill="none" stroke="#fff" stroke-width="3.4" stroke-linecap="round" stroke-linejoin="round"/></svg></div>'
                   f'<span>{rich(it["text"])}</span></div>' for i, it in enumerate(items))
    c.css.append('''#ckl{position:absolute;left:40px;top:110px;right:40px}
.ck{display:flex;align-items:center;gap:22px;height:96px;font:600 40px/1.1 'Inter';color:#0b0b0f;letter-spacing:-.03em}
.ck em{font-style:normal;font-weight:800;color:ACCENT}
.ck .bx{width:58px;height:58px;border-radius:18px;border:3px solid #e4e4ea;display:grid;place-items:center;flex:none}
.ck .bx svg{opacity:0}'''.replace('ACCENT', T.ACCENT))
    c.body.append(window(f'<div id="ckl">{rows}</div>', v.get('bar', 'checklist')))
    c.js.append('gsap.set("#cur",{autoAlpha:0});')
    for i, it in enumerate(items):
        t = j.t(it.get('at'), 0.4 + i * 0.6)
        c.js.append(f'tl.fromTo("#ck{i}",{{x:-30,autoAlpha:0}},{{x:0,autoAlpha:1,duration:.3,ease:"power3.out"}},{max(0, t-0.35):.3f});'
                    f'tl.to("#ck{i} .bx",{{background:"{T.ACCENT}",borderColor:"{T.ACCENT}",duration:.15}},{t:.3f});'
                    f'tl.to("#ck{i} .bx svg",{{opacity:1,duration:.1}},{t:.3f});'
                    f'tl.fromTo("#ck{i} .bx",{{scale:1.25}},{{scale:1,duration:.25,ease:"back.out(3)"}},{t:.3f});')


def main(spec):
    j = Job(spec, 'split-screen')
    c = Comp(j)
    hz = j.horizontal
    if hz:
        # visuals on the left half, the speaker on the right half, the caption pill across the seam at the bottom
        top_box = 'left:0;top:0;width:960px;height:1080px'
        bot_box = 'left:960px;top:0;width:960px;height:1080px'
        stage = 'transform:translate(-6px,-39px) scale(.9);transform-origin:0 0'
        badge = 'left:0;width:960px;top:110px'
        h1 = "left:40px;width:880px;top:178px;font:800 72px/1.02 'Inter'"
        cap = f"left:0;width:1920px;top:{j.get('caption_top', 870)}px"
        z = float(j.get('zoom', 1.0))
        vw, vh = 1920 * z, 1080 * z
        vx = min(0, max(960 - vw, 480 - float(j.get('face_x', 960)) * z))
        vy = min(0, max(1080 - vh, float(j.get('video_top', (1080 - vh) / 2))))
        vid = f'position:absolute;left:{vx:.0f}px;top:{vy:.0f}px;width:{vw:.0f}px;height:{vh:.0f}px'
        cap_size = 58
    else:
        top_box = 'left:0;top:0;width:1080px;height:960px'
        bot_box = 'left:0;top:960px;width:1080px;height:960px'
        stage = ''
        badge = 'left:0;width:1080px;top:206px'
        h1 = "left:40px;width:1000px;top:276px;font:800 88px/1.02 'Inter'"
        cap = f"left:0;width:1080px;top:{j.get('caption_top', 918)}px"
        vid = f'position:absolute;left:0;top:{j.get("video_top", -430)}px;width:1080px;height:1920px'
        cap_size = 64
    c.css.append(f'''
#top{{{top_box};overflow:hidden;background:{T.PAPER}}}
#top:before{{content:'';position:absolute;inset:0;background-image:radial-gradient(rgba(11,11,15,.07) 1.6px,transparent 1.8px);background-size:36px 36px}}
#stage{{position:absolute;left:0;top:0;width:1080px;height:960px;{stage}}}
#badge{{{badge};text-align:center}}
#badge span{{display:inline-flex;align-items:center;gap:12px;padding:12px 24px 13px 18px;border-radius:999px;background:{T.ACCENT};color:#fff;
  font:700 34px/1 'Inter';letter-spacing:-.01em;box-shadow:0 10px 24px {T.rgba(T.ACCENT, .3)}}}
#h1{{{h1};text-align:center;color:{T.INK};letter-spacing:-.05em}}
#h1 em{{font-style:normal;color:{T.ACCENT}}}
#win{{left:110px;top:410px;width:860px;height:520px;border-radius:32px;background:{T.SURFACE};overflow:hidden;
  box-shadow:{T.SHADOW},0 0 0 1px rgba(11,11,15,.05)}}
#win .bar{{position:absolute;left:0;top:0;right:0;height:78px;display:flex;align-items:center;gap:10px;padding:0 26px;
  border-bottom:1px solid {T.LINE};background:{T.SURFACE};z-index:3}}
#win .dot{{width:14px;height:14px;border-radius:50%;background:{T.LINE}}}
#win .sr{{margin-left:20px;flex:1;height:46px;border-radius:23px;background:{T.PAPER};display:flex;align-items:center;padding:0 22px;
  font:500 26px 'Inter';color:{T.MUTED};white-space:nowrap;overflow:hidden}}
#lib{{position:absolute;left:26px;top:100px;display:grid;grid-template-columns:repeat(4,190px);gap:14px}}
.lc{{position:relative;width:190px;height:238px;border-radius:14px;overflow:hidden;background:{T.LINE};transform-origin:50% 50%}}
.lc img{{width:190px;height:238px;object-fit:cover}}
.chip{{position:absolute;left:10px;bottom:10px;padding:5px 11px;border-radius:10px;background:{T.ACCENT};color:#fff;font:700 22px 'Inter';
  box-shadow:0 3px 8px rgba(0,0,0,.2)}}
#pick{{position:absolute;border:5px solid {T.ACCENT};border-radius:18px;box-shadow:0 18px 40px {T.rgba(T.ACCENT, .35)}}}
#btn{{left:330px;top:820px;padding:20px 34px;border-radius:40px;background:{T.INK};color:#fff;font:700 32px 'Inter';white-space:nowrap;
  box-shadow:0 14px 34px rgba(0,0,0,.25);z-index:6}}
.sl{{position:absolute;width:150px;height:188px;border-radius:14px;overflow:hidden;box-shadow:0 10px 26px rgba(0,0,0,.25);z-index:5}}
.sl img{{width:150px;height:188px;object-fit:cover}}
#cur{{left:0;top:0;width:46px;height:46px;z-index:9;filter:drop-shadow(0 3px 5px rgba(0,0,0,.3))}}
#bot{{{bot_box};overflow:hidden;background:#000}}
.sc{{position:absolute;{cap};text-align:center;visibility:hidden;z-index:20}}
.sc span.p{{display:inline-block;padding:16px 32px 19px;border-radius:999px;background:{T.INK};font:800 {cap_size}px/1 'Inter';
  letter-spacing:-.03em;white-space:nowrap;box-shadow:0 12px 30px rgba(0,0,0,.35)}}
.sc span.w{{color:rgba(255,255,255,.4)}}
''')
    v = j.get('visual') or {}
    c.body.append('<div id="top" class="a">')
    if j.get('badge'):
        c.body.append(f'<div id="badge" class="a"><span>{STAR}{html.escape(j.get("badge"))}</span></div>')
    c.body.append(f'<div id="h1" class="a">{rich(j.get("headline", ""))}</div>')
    c.body.append('<div id="stage">')
    {'grid-pick': grid_pick, 'image': image, 'checklist': checklist}[v.get('type', 'grid-pick')](j, c, v)
    c.body.append(CURSOR + '</div></div>')
    c.body.append('<div id="bot" class="a">' + c.video(j.clip, vid, 'bg') + '</div>')
    c.js.append('''tl.fromTo("#win",{y:50,autoAlpha:0},{y:0,autoAlpha:1,duration:.4,ease:"power3.out"},0);
tl.fromTo(["#badge","#h1"],{y:20,autoAlpha:0},{y:0,autoAlpha:1,duration:.35,stagger:.08,ease:"power3.out"},0);''')
    # seam caption: a dark pill, each word brightens as it is said; key words turn the accent
    keys = {bare(k) for k in j.get('keys', [])}
    gs = groups(j.words, maxw=4, maxc=18)
    for i, g in enumerate(gs):
        t0 = max(0, g[0][1] - 0.04)
        t1 = gs[i + 1][0][1] - 0.04 if i + 1 < len(gs) else c.dur
        sp = ' '.join(f'<span class="w" id="sc{i}_{k}">{html.escape(w)}</span>' for k, (w, _) in enumerate(g))
        c.body.append(f'<div class="sc" id="sc{i}"><span class="p">{sp}</span></div>')
        c.js.append(f'tl.set("#sc{i}",{{visibility:"visible"}},{t0:.3f});tl.set("#sc{i}",{{visibility:"hidden"}},{t1:.3f});'
                    f'tl.fromTo("#sc{i} .p",{{scale:.94}},{{scale:1,duration:.14,ease:"power3.out"}},{t0:.3f});')
        for k, (w, t) in enumerate(g):
            col = T.ACCENT_LIGHT if w in keys else '#fff'
            c.js.append(f'tl.set("#sc{i}_{k}",{{color:"{col}"}},{max(t0, t - 0.02):.3f});')
    j.finish(c)


if __name__ == '__main__':
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    main(sys.argv[1])
