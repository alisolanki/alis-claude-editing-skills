#!/usr/bin/env python3
"""ranking-list: a tier list (S to F). Vertical: on the speaker's chest. Horizontal: beside the speaker.
Each item pops up when it is named, then drops into its row when the speaker gives the verdict.

    <kit>/.venv/bin/python build.py spec.json

Spec (see SKILL.md):
  video, start, end, out, format
  title: "BEST CONTENT\\nFORMATS"            title on an accent block at the top
  items: [{name, tier, pop, drop, images | icon, color}, ...]
  table_top, table_left, item_top, caption_top     positions on the canvas
"""
import html
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'kit'))
from reel import Job, Comp, karaoke, rich  # noqa: E402
import theme as T  # noqa: E402

TIERS = list(zip('SABCDEF', T.ramp(7)))      # one accent, fading down the tiers
ICONS = {
    'play': '<div class="rl"></div>',
    'none': '',
}


def main(spec):
    j = Job(spec, 'ranking-list')
    c = Comp(j)
    tiers = [tuple(t) for t in j.get('tiers', TIERS)]
    names = [t for t, _ in tiers]
    hz = j.horizontal
    TW, RH = 800, 62
    TX = j.get('table_left', j.pick(140, 1920 - 120 - TW))
    TY = j.get('table_top', j.pick(1100, max(170, (1080 - RH * len(tiers)) // 2)))
    IY = j.get('item_top', TY + 30)
    CY = j.get('caption_top', j.pick(TY - 78, 880))
    ttl_box = "left:120px;width:900px;top:90px;text-align:left" if hz else "left:0;width:1080px;top:236px;text-align:center"
    c.css.append(f'''
#ttl{{{ttl_box}}}
#ttl span{{display:inline-block;font:800 {j.pick(76, 70)}px/1.04 'Inter';color:#fff;letter-spacing:-.045em;background:{j.get("title_color", T.ACCENT)};
  padding:.06em .22em .12em;border-radius:.2em;box-shadow:0 14px 40px {T.rgba(T.ACCENT, .35)}}}
#tb{{left:{TX}px;top:{TY}px;width:{TW}px;height:{RH*len(tiers)+10}px;background:{T.NIGHT};padding:5px;border-radius:22px;overflow:hidden;
  box-shadow:{T.SHADOW_DARK}}}
.row{{position:relative;height:{RH}px;display:flex;border-bottom:3px solid {T.NIGHT}}}
.row .lb{{width:76px;height:{RH-3}px;display:grid;place-items:center;font:800 34px 'Inter';border-radius:14px}}
.row .rb{{flex:1;background:{T.NIGHT_SURFACE};margin-left:5px;border-radius:14px}}
.row .fl{{position:absolute;left:81px;right:0;top:0;bottom:3px;background:{T.rgba(T.ACCENT, .45)};opacity:0;border-radius:14px}}
.itm{{position:absolute;left:250px;top:{IY}px;width:580px;height:340px;border-radius:26px;overflow:hidden;visibility:hidden;
  transform-origin:0 0;box-shadow:0 0 0 4px rgba(255,255,255,.95),{T.SHADOW_DARK}}}
.itm .nm{{position:absolute;left:0;right:0;bottom:34px;text-align:center;font:800 72px/1 'Inter';color:#fff;
  letter-spacing:-.045em;text-shadow:0 4px 20px rgba(0,0,0,.3)}}
.itm img.one{{position:absolute;left:0;top:0;width:580px;height:340px;object-fit:cover}}
.itm img.one+.nm{{background:linear-gradient(180deg,transparent,rgba(0,0,0,.7));padding:40px 0 0;bottom:0;height:150px}}
.fan{{position:absolute;top:34px;width:118px;height:148px;border-radius:7px;overflow:hidden;box-shadow:0 6px 18px rgba(0,0,0,.5)}}
.fan img{{width:118px;height:148px;object-fit:cover}}
.rl{{position:absolute;left:236px;top:40px;width:108px;height:150px;border-radius:26px;border:7px solid #fff}}
.rl:after{{content:'';position:absolute;left:36px;top:46px;border-left:36px solid #fff;border-top:22px solid transparent;border-bottom:22px solid transparent}}
.rc span.p{{text-shadow:0 3px 14px rgba(0,0,0,.75);padding:0}}
''')
    c.body.append(c.video(j.clip, f'position:absolute;left:0;top:0;width:{c.W}px;height:{c.H}px', 'bg'))
    c.body.append(f'<div id="ttl" class="a">{"<br>".join(f"<span>{rich(l)}</span>" for l in str(j.get("title", "")).split(chr(10)))}</div>')
    rows = ''.join(f'<div class="row" id="row{t}"><div class="lb" style="background:{col};color:{T.on(col)}">{html.escape(t)}</div><div class="rb"></div>'
                   f'<div class="fl"></div></div>' for t, col in tiers)
    c.body.append(f'<div id="tb" class="a">{rows}</div>')
    c.js.append('''tl.fromTo("#ttl",{y:-30,autoAlpha:0},{y:0,autoAlpha:1,duration:.3,ease:"power3.out"},0);
tl.fromTo("#tb",{y:40,autoAlpha:0},{y:0,autoAlpha:1,duration:.3,ease:"power3.out"},0);''')

    used = {}
    for n, it in enumerate(j.get('items') or []):
        tier = it['tier']
        if tier not in names:
            sys.exit(f'item {it["name"]}: tier {tier} is not one of {names}')
        k = used.get(tier, 0)
        used[tier] = k + 1
        imgs = j.images(it.get('images'))
        col = it.get('color', [T.ACCENT, T.ACCENT_DEEP, '#24242c', T.mix(T.ACCENT, '#24242c', .5)][n % 4])
        if len(imgs) >= 2:
            vis = ''.join(f'<div class="fan" style="left:{150+q*95}px;transform:rotate({(q-1)*9}deg) translateY({abs(q-1)*10}px)">'
                          f'<img src="{c.asset(s)}"></div>' for q, s in enumerate(imgs[:3]))
        elif len(imgs) == 1:
            vis = f'<img class="one" src="{c.asset(imgs[0])}">'
        else:
            vis = ICONS.get(it.get('icon', 'none'), '')
        # on a close-up the chest sits low: shrink the card so it never dips into Instagram's bottom UI
        f = max(0.6, min(1.0, (j.safe[1] - IY) / 340))
        left = TX + (TW - 580) / 2 + 580 * (1 - f) / 2
        c.body.append(f'<div class="itm" id="it{n}" style="left:{left:.0f}px;background:radial-gradient(ellipse at 50% 20%,{col} 0%,{T.NIGHT} 110%)">'
                      f'{vis}<div class="nm">{html.escape(it["name"])}</div></div>')
        i = names.index(tier)
        sx, sy, sc = TX + 5 + 76 + 8 + k * 128, TY + 5 + i * RH + 6, (RH - 15) / 340
        pop = j.t(it.get('pop'), 0.06)
        drop = j.t(it.get('drop'), pop + 1.1)
        c.js.append(f'''tl.set("#it{n}",{{visibility:"visible"}},{pop:.3f});
tl.fromTo("#it{n}",{{scale:{.5*f:.3f},x:{145*f:.1f},y:{85*f:.1f},autoAlpha:0}},{{scale:{f:.3f},x:0,y:0,autoAlpha:1,duration:.26,ease:"back.out(1.7)",transformOrigin:"0 0"}},{pop:.3f});
tl.to("#it{n}",{{x:{sx-left:.1f},y:{sy-IY},scale:{sc:.4f},duration:.34,ease:"power3.in",transformOrigin:"0 0"}},{drop:.3f});
tl.fromTo("#row{tier} .fl",{{opacity:.9}},{{opacity:0,duration:.5,immediateRender:false}},{drop + 0.34:.3f});''')
    # spoken-word caption just under the chin, on top of everything
    karaoke(c, j.words, CY, 'rc', maxc=j.pick(16, 26), size=j.pick(50, 52), plate=False, font="800 {s}px/1 'Inter'",
            grey='#ffffff', white='#ffffff', left=j.pick(0, 0), width=j.pick(1080, TX - 40))
    j.finish(c)


if __name__ == '__main__':
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    main(sys.argv[1])
