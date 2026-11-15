#!/usr/bin/env python3
"""explainer: the speaker sits in a rounded panel on a light backdrop, the head breaking out over its top edge,
and the rest of the frame explains the point with visuals (a before/after comparison or a short list).

    <kit>/.venv/bin/python build.py spec.json

Vertical: the panel sits low and the visuals sit on top. Horizontal: the panel sits on the right (or left, with
"side") and the visuals fill the other side.

Spec (see SKILL.md):
  video, start, end, out, format
  title: "Steal what *works*"                        (*word* = accent)
  eye_y: 750                                         speaker's eye line on the canvas (the panel's top edge)
  face_x: 960                                        horizontal only: the x of the face centre in the source
  visual: {type: compare | list, ...}
  keys: ["viral", "recreate"]                        caption words set on the accent pill
"""
import html
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'kit'))
from reel import Job, Comp, caption_css, cover_html, rich, word_caps  # noqa: E402
import theme as T  # noqa: E402

ACC = T.ACCENT


def text_card(big, small, dark):
    bg, fg, sub = (T.ACCENT, '#fff', 'rgba(255,255,255,.72)') if dark else (T.SURFACE, T.INK, T.MUTED)
    return (f'<div class="tcard" style="background:{bg};color:{fg}"><div class="tb{" on" if dark else ""}">{rich(big)}</div>'
            f'<div class="ts" style="color:{sub}">{html.escape(small)}</div></div>')


def compare(j, c, v, G):
    """G: the geometry of the visual area for this canvas"""
    L, R = v.get('left') or {}, v.get('right') or {}
    limgs = j.images(L.get('images'))
    if limgs:
        strip = ''.join(f'<img src="{c.asset(s)}">' for s in limgs[:3])
    elif L.get('big'):
        strip = text_card(L['big'], L.get('small', ''), dark=False)
    else:
        sys.exit('visual.left needs images, or big (+ small) for a text card')
    if R.get('big') and not R.get('image'):
        right = text_card(R['big'], R.get('small', ''), dark=True)
    elif R.get('text'):
        right = cover_html(c, 270, (j.images(R.get('image')) or [None])[0], R['text'], R.get('cta', 'SWIPE →'))
    elif R.get('image'):
        right = f'<img src="{c.asset(j.images(R.get("image"))[0])}" style="width:270px;height:338px;object-fit:cover;border-radius:18px">'
    else:
        sys.exit('visual.right needs image, image + text, or big (+ small) for a text card')
    lx, rx, cy = G['lx'], G['rx'], G['cy']
    chip = f'<div id="vch" class="hid">{html.escape(L["chip"])}</div>' if L.get('chip') else ''
    c.css.append(f'''#lc{{left:{lx}px;top:{cy}px}}#rc0,#rc{{left:{rx}px;top:{cy}px}}
#arw{{left:{lx + 270:.0f}px;top:{cy + 85}px;width:{rx - lx - 270:.0f}px;height:120px;overflow:visible}}''')
    aw = rx - lx - 270
    c.body.append(f'''<div class="lab" id="lab0" style="left:{lx}px;top:{cy - 45}px">{html.escape(L.get("label", "Before"))}</div>
<div class="lab" id="lab1" style="left:{rx}px;top:{cy - 45}px;color:{ACC}">{html.escape(R.get("label", "After"))}</div>
<div class="cv" id="lc"><div class="strip">{strip}</div>{chip}</div>
<div id="rc0" class="a hid">?</div>
<div id="rc" class="a">{right}</div>
<svg id="arw" class="a" viewBox="0 0 {aw:.0f} 120"><path id="arp" d="M14 64 C {aw*.3:.0f} -12, {aw*.7:.0f} -12, {aw-16:.0f} 60" fill="none" stroke="{ACC}" stroke-width="7"
 stroke-linecap="round" stroke-dasharray="{aw*1.4:.0f}" stroke-dashoffset="{aw*1.4:.0f}"/><path id="arh" d="M{aw-24:.1f} 31.1 L{aw-16:.0f} 60 L{aw-45.8:.1f} 56.6" fill="none" stroke="{ACC}"
 stroke-width="7" stroke-linecap="round" stroke-linejoin="round" opacity="0"/></svg>''')
    la = j.t(L.get('at'), 0.3)
    ra = j.t(R.get('at'), c.dur * 0.55)
    aa = j.t(v.get('arrow_at'), ra + 0.6)
    rv = j.t(R.get('reveal_at'), aa + 0.28)
    c.js.append(f'tl.fromTo(["#lab0","#lc"],{{y:30,autoAlpha:0}},{{y:0,autoAlpha:1,duration:.32,stagger:.05,ease:"power3.out"}},{la:.3f});')
    if chip:
        ch = j.t(L.get('chip_at'), la + 0.8)
        c.js.append(f'tl.set("#vch",{{visibility:"visible"}},{ch:.3f});'
                    f'tl.fromTo("#vch",{{scale:.4,autoAlpha:0}},{{scale:1,autoAlpha:1,duration:.22,ease:"back.out(2.5)"}},{ch:.3f});')
    for k, s in enumerate((L.get('swipe_at') or [])[:max(0, len(limgs[:3]) - 1)]):
        c.js.append(f'tl.to("#lc .strip",{{x:{-270 * (k + 1)},duration:.3,ease:"power2.inOut"}},{j.t(s):.3f});')
    c.js.append(f'''tl.set("#rc0",{{visibility:"visible"}},{ra:.3f});
tl.fromTo(["#lab1","#rc0"],{{y:30,autoAlpha:0}},{{y:0,autoAlpha:1,duration:.3,stagger:.05,ease:"power3.out"}},{ra:.3f});
tl.fromTo("#lab0",{{color:"{T.MUTED}"}},{{color:"{T.INK}",duration:.2}},{ra:.3f});
tl.to("#arp",{{strokeDashoffset:0,duration:.38,ease:"power2.inOut"}},{aa:.3f});
tl.to("#arh",{{opacity:1,duration:.08}},{aa+0.34:.3f});
tl.to("#rc",{{clipPath:"inset(0 0% 0 0)",duration:.34,ease:"power3.out"}},{rv:.3f});
tl.fromTo("#rc",{{scale:1.06}},{{scale:1,duration:.4,ease:"power3.out"}},{rv:.3f});''')


def listing(j, c, v, G):
    items = v.get('items') or []
    rows = ''.join(f'<div class="li" id="li{i}"><b>{i + 1}</b><span>{rich(it["text"])}</span></div>' for i, it in enumerate(items))
    rh = min(118, G['lh'] // max(1, len(items)))
    c.css.append(f'''#lst{{left:{G['lx']}px;top:{G['ly'] + (G['lh'] - rh * len(items)) // 2}px;width:{G['lw']}px}}
.li{{display:flex;align-items:center;gap:26px;height:{rh}px;font:700 50px/1.05 'Inter';color:{T.INK};letter-spacing:-.035em}}
.li b{{width:72px;height:72px;border-radius:22px;background:{ACC};color:#fff;display:grid;place-items:center;font:800 36px 'Inter';flex:none}}
.li em{{font-style:normal;color:{ACC}}}''')
    c.body.append(f'<div id="lst" class="a">{rows}</div>')
    for i, it in enumerate(items):
        t = j.t(it.get('at'), 0.4 + i * 0.7)
        c.js.append(f'tl.fromTo("#li{i}",{{x:-40,autoAlpha:0}},{{x:0,autoAlpha:1,duration:.32,ease:"power3.out"}},{t:.3f});')


def main(spec):
    j = Job(spec, 'explainer')
    c = Comp(j)
    if j.horizontal:
        side = j.get('side', 'right')
        SC = float(j.get('scale', 0.9))
        VW, VH = c.W * SC, c.H * SC
        PW, PB = 740, 1000
        PX = 1920 - 120 - PW if side == 'right' else 120
        VX = PX + PW / 2 - float(j.get('face_x', 960)) * SC
        VX = min(PX, max(PX + PW - VW, VX))           # keep the panel filled
        VY = PB - VH
        PT = VY + float(j.get('eye_y', 400)) * SC
        area = 120 if side == 'right' else PX + PW + 80
        aw = PX - 80 - area if side == 'right' else 1800 - area
        G = dict(lx=area + 20, rx=area + aw - 290, cy=380, ly=270, lh=560, lw=aw)
        ttl = f"left:{area}px;width:{aw}px;top:110px;text-align:left;font:800 80px/1 'Inter'"
        cap = caption_css('kx', j.get('caption_top', 850), PW - 40, size=58, left=PX + 20)
    else:
        SC, VX, VY = 0.82, 97, 316
        VW, VH = 1080 * SC, 1920 * SC
        PW, PB = VW, 1830
        PX = VX
        PT = VY + float(j.get('eye_y', 750)) * SC        # the panel's top edge sits on the eye line, so the head breaks out
        G = dict(lx=110, rx=700, cy=385, ly=330, lh=430, lw=840)
        ttl = "left:0;width:1080px;top:206px;text-align:center;font:800 88px/1 'Inter'"
        cap = caption_css('kx', j.get('caption_top', 1420), 1080, size=68)
    c.css.append(f'''
#bk{{left:0;top:0;width:{c.W}px;height:{c.H}px;background:radial-gradient(ellipse at 50% 20%,#ffffff 0%,{T.PAPER} 55%,#ececf1 100%)}}
#ttl{{{ttl};color:{T.INK};letter-spacing:-.05em}}
#ttl span{{display:inline-block}}
#ttl em{{font-style:normal;color:{ACC}}}
#pan{{left:{PX:.0f}px;top:{PT:.0f}px;width:{PW:.0f}px;height:{PB-PT:.0f}px;border-radius:48px;overflow:hidden;box-shadow:{T.SHADOW}}}
#pop{{left:{PX:.0f}px;top:{VY:.0f}px;width:{PW:.0f}px;height:{PT-VY:.0f}px;overflow:hidden}}
.lab{{position:absolute;font:700 24px 'Inter';letter-spacing:.14em;text-transform:uppercase;color:{T.MUTED};white-space:nowrap}}
.cv{{position:absolute;width:270px;height:338px;border-radius:18px;overflow:hidden;box-shadow:{T.SHADOW}}}
#lc .strip{{display:flex}}#lc img{{width:270px;height:338px;object-fit:cover;flex:none}}
#vch{{position:absolute;left:12px;top:12px;padding:6px 13px;border-radius:12px;background:{ACC};color:#fff;font:700 24px 'Inter'}}
#rc0{{width:270px;height:338px;border-radius:18px;border:3px dashed {T.LINE};display:grid;place-items:center;
  font:800 80px 'Inter';color:#c9c9d2;background:rgba(255,255,255,.5)}}
#rc{{clip-path:inset(0 100% 0 0)}}
.tcard{{width:270px;height:338px;border-radius:18px;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:14px;
  padding:24px;text-align:center;box-shadow:{T.SHADOW}}}
.tcard .tb{{font:800 64px/1 'Inter';letter-spacing:-.05em}}
.tcard .tb em{{font-style:normal;color:{ACC}}}.tcard .tb.on em{{color:#fff;text-decoration:underline;text-decoration-thickness:6px;text-underline-offset:8px}}
.tcard .ts{{font:600 24px/1.25 'Inter'}}
{cap}
''')
    c.body.append('<div id="bk" class="a"></div>')
    words = rich(j.get('title', '')).split(' ')
    c.body.append(f'<div id="ttl" class="a">{" ".join(f"<span>{w}</span>" for w in words)}</div>')
    v = j.get('visual') or {}
    {'compare': compare, 'list': listing}[v.get('type', 'compare')](j, c, v, G)
    cut = j.cutout()
    c.body.append('<div id="pan" class="a">' + c.video(j.clip, f'position:absolute;left:{VX-PX:.0f}px;top:{VY-PT:.0f}px;width:{VW:.0f}px;height:{VH:.0f}px', 'bg') + '</div>')
    c.body.append('<div id="pop" class="a">' + c.video(cut, f'position:absolute;left:{VX-PX:.0f}px;top:0;width:{VW:.0f}px;height:{VH:.0f}px', 'cut') + '</div>')
    word_caps(c, j.words, 'kx', '', maxw=3, maxc=16, keys=j.get('keys', []), pop=(0.94, 0.16))
    c.js.append('tl.fromTo("#ttl span",{y:40,autoAlpha:0},{y:0,autoAlpha:1,duration:.3,stagger:.07,ease:"power3.out"},0);')
    j.finish(c)


if __name__ == '__main__':
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    main(sys.argv[1])
