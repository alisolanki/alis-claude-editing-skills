#!/usr/bin/env python3
"""trial-reels: the same clip as 3 visually distinct versions, to post as trial reels (or A/B thumbnails-in-motion
for long-form) and see which look wins.

    <kit>/.venv/bin/python build.py spec.json        -> <out>-1.mp4, <out>-2.mp4, <out>-3.mp4

  1  Title + karaoke:  a big white title (key lines on an accent pill), Clean Karaoke captions (dim to white)
  2  Post header:      a white post card (avatar, name, the hook as a headline), punch-in zooms, bold captions
  3  Stat frame:       a dark dot-grid backdrop, one big stat, the clip in an accent frame, quiet captions

Works on both canvases: "format": "vertical" (1080x1920) or "horizontal" (1920x1080); "auto" follows the source.

Spec (see SKILL.md):
  video, start, end, out, format
  v1: {title: ["carousels are an", "*instagram*", "*cheat code*"]}           *line* = bigger, on the accent
  v2: {avatar, name, sub, headline, keys: [...], punches: [1.16, "views"]}
  v3: {stat: "2×", line: "the views of reels", pulse_at: "twice"}
"""
import html
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'kit'))
from reel import Job, Comp, bare, caption_css, karaoke, rich, word_caps  # noqa: E402
import theme as T  # noqa: E402


def full(c):
    return f'position:absolute;left:0;top:0;width:{c.W}px;height:{c.H}px'


def v1(j, s):
    c = Comp(j, 'v1')
    hz = j.horizontal
    left, top, width, align = (120, 90, 1100, 'left') if hz else (0, 238, 1080, 'center')
    size, big = (78, 104) if hz else (84, 112)
    c.css.append(f'''
#yt{{left:{left}px;width:{width}px;top:{top}px;text-align:{align};font:800 {size}px/1.04 'Inter';color:#fff;letter-spacing:-.045em;
  text-shadow:0 2px 6px rgba(0,0,0,.3),0 10px 40px rgba(0,0,0,.35)}}
#yt em{{font-style:normal;font-size:{big}px;display:inline-block;background:{T.ACCENT};color:#fff;text-shadow:none;
  padding:0 .16em .06em;border-radius:.18em;margin:.05em 0}}
''')
    c.body.append(c.video(j.clip, full(c), 'bg'))
    c.body.append(f'<div id="yt" class="a">{"<br>".join(rich(l) for l in s.get("title", []))}</div>')
    karaoke(c, j.words, s.get('caption_top', j.pick(1400, 850)), 'kc', size=j.pick(56, 54))
    c.js.append('tl.fromTo("#yt",{y:24,autoAlpha:0},{y:0,autoAlpha:1,duration:.32,ease:"power3.out"},0);')
    return c


def v2(j, s):
    c = Comp(j, 'v2')
    hz = j.horizontal
    origin = j.pick('540px 820px', '960px 430px')
    hd_left, hd_top, hd_w = (120, 80, 820) if hz else (110, 236, 860)
    cap_top = s.get('caption_top', j.pick(1260, 820))
    c.css.append(f'''
#vw{{left:0;top:0;width:{c.W}px;height:{c.H}px;transform-origin:{origin}}}
#hd{{left:{hd_left}px;top:{hd_top}px;width:{hd_w}px;padding:30px 36px 34px;border-radius:{T.RADIUS}px;background:{T.SURFACE};box-shadow:{T.SHADOW}}}
#hd .u{{display:flex;align-items:center;gap:16px;margin-bottom:18px}}
#hd .u img{{width:64px;height:64px;border-radius:50%;object-fit:cover}}
#hd .u i{{width:64px;height:64px;border-radius:50%;background:{T.ACCENT};flex:none}}
#hd .u b{{font:700 30px/1.1 'Inter';color:{T.INK};letter-spacing:-.01em}}#hd .u span{{font:500 25px 'Inter';color:{T.MUTED};display:block}}
#hd .q{{font:700 {j.pick(50, 46)}px/1.12 'Inter';color:{T.INK};letter-spacing:-.035em}}
#hd .bar{{position:absolute;left:36px;top:0;width:56px;height:6px;border-radius:0 0 6px 6px;background:{T.ACCENT}}}
''')
    c.css.append(caption_css('hz', cap_top, c.W, size=j.pick(84, 72)))
    c.body.append('<div id="vw" class="a">' + c.video(j.clip, full(c), 'bg') + '</div>')
    av = j.images(s['avatar'])[0] if s.get('avatar') else None
    img = f'<img src="{c.asset(av)}">' if av else '<i></i>'
    c.body.append(f'<div id="hd" class="a"><div class="bar"></div><div class="u">{img}<div><b>{html.escape(s.get("name", ""))}</b>'
                  f'<span>{html.escape(s.get("sub", ""))}</span></div></div><div class="q">{html.escape(s.get("headline", ""))}</div></div>')
    keys = s.get('keys', [])
    word_caps(c, j.words, 'hz', '', maxw=2, maxc=18, keys=keys, pop=(1.18, 0.14))
    punches = s.get('punches')
    if punches is None:      # default: punch in on the first key words, at least 1.5 s apart
        kb, punches, last = {bare(k) for k in keys}, [], -9
        for w, t, _ in j.words:
            if bare(w) in kb and t - last >= 1.5 and t < c.dur - 0.6:
                punches.append(t)
                last = t
            if len(punches) == 3:
                break
    c.js.append('tl.fromTo("#hd",{y:-30,autoAlpha:0},{y:0,autoAlpha:1,duration:.34,ease:"power3.out"},0);'
                'tl.set("#vw",{scale:1.12},0);')
    # a slow drift in, then each punch: snap in on the word, ease back out (one tween at a time, never overlapping)
    free = 0.0
    for p in sorted(j.t(p) for p in punches):
        if p < free + 0.3 or p > c.dur - 0.3:
            continue
        back = min(c.dur - 0.5, p + 0.8)
        c.js.append(f'tl.to("#vw",{{scale:1.17,duration:{p - free - 0.02:.3f},ease:"none"}},{free:.3f});'
                    f'tl.to("#vw",{{scale:1.28,duration:.12,ease:"power2.out"}},{p:.3f});'
                    f'tl.to("#vw",{{scale:1.15,duration:.5,ease:"power2.inOut"}},{back:.3f});')
        free = back + 0.5
    return c


def v3(j, s):
    c = Comp(j, 'v3')
    if j.horizontal:
        SC = 0.58
        VW, VH = c.W * SC, c.H * SC
        FL, FT, FW, FH = 1920 - 120 - VW, (1080 - VH) / 2, VW, VH
        px_css = f'#px{{left:120px;width:{FL - 180:.0f}px;top:{FT + 40:.0f}px;text-align:left;font:800 200px/.9 \'Inter\';color:{T.ACCENT_LIGHT};letter-spacing:-.06em}}'
        small = 'font:600 48px/1.15 \'Inter\';color:#f2f2f5;margin-top:22px;letter-spacing:-.03em;max-width:560px'
        vid_style = f'position:absolute;left:0;top:0;width:{VW:.0f}px;height:{VH:.0f}px'
        cap = (FT + FH - 120, FL, FW)
    else:
        SC = 0.78
        VW, VH = 1080 * SC, 1920 * SC
        FL, FT, FW, FH = (1080 - VW) / 2, 410, VW, 1898 - 410
        px_css = f'#px{{left:0;width:1080px;top:170px;text-align:center;font:800 190px/.9 \'Inter\';color:{T.ACCENT_LIGHT};letter-spacing:-.06em}}'
        small = 'font:600 50px/1.1 \'Inter\';color:#f2f2f5;margin-top:10px;letter-spacing:-.03em'
        vid_style = f'position:absolute;left:0;top:{FH - VH:.0f}px;width:{VW:.0f}px;height:{VH:.0f}px'
        cap = (s.get('caption_top', 1330), 0, 1080)
    c.css.append(f'''
#bk{{left:0;top:0;width:{c.W}px;height:{c.H}px;background:{T.NIGHT}}}
#bk:before{{content:'';position:absolute;inset:0;background-image:radial-gradient(rgba(255,255,255,.07) 1.6px,transparent 1.8px);background-size:36px 36px}}
#fr{{left:{FL:.0f}px;top:{FT:.0f}px;width:{FW:.0f}px;height:{FH:.0f}px;border-radius:36px;overflow:hidden;
  box-shadow:0 0 0 4px {T.ACCENT},{T.SHADOW_DARK}}}
{px_css}
#px small{{display:block;{small}}}
#tag{{left:{FL + 28:.0f}px;top:{FT + 28:.0f}px;padding:9px 16px 10px;border-radius:12px;background:rgba(11,11,15,.6);font:700 26px 'Inter';
  color:#fff;letter-spacing:.06em;display:flex;align-items:center;gap:10px}}
#tag i{{width:14px;height:14px;border-radius:50%;background:{T.ACCENT_LIGHT}}}
.pk span.p{{text-shadow:0 3px 10px rgba(0,0,0,.6)}}
''')
    c.body.append('<div id="bk" class="a"></div>')
    c.body.append('<div id="fr" class="a">' + c.video(j.clip, vid_style, 'bg') + '</div>')
    c.body.append(f'<div id="px" class="a"><span id="pxn" style="display:inline-block">{html.escape(s.get("stat", ""))}</span>'
                  f'<small>{html.escape(s.get("line", ""))}</small></div>')
    c.body.append('<div id="tag" class="a"><i id="dot"></i>REC</div>')
    top, left, width = cap
    karaoke(c, j.words, top, 'pk', maxc=20, size=j.pick(54, 48), plate=False, font="700 {s}px/1 'Inter'",
            grey='rgba(255,255,255,.4)', white='#fff', left=left, width=width)
    blinks = max(1, int(c.dur / 0.5))
    c.js.append(f'''tl.fromTo("#px",{{autoAlpha:0,y:-16}},{{autoAlpha:1,y:0,duration:.3,ease:"power3.out"}},0);
tl.fromTo("#fr",{{y:60,autoAlpha:0}},{{y:0,autoAlpha:1,duration:.4,ease:"power3.out"}},0);
tl.to("#dot",{{autoAlpha:.15,duration:.01,repeat:{blinks if blinks % 2 else blinks - 1},yoyo:true,repeatDelay:.49}},0);''')
    if s.get('pulse_at') is not None:
        c.js.append(f'tl.fromTo("#pxn",{{scale:1}},{{scale:1.12,duration:.12,yoyo:true,repeat:1,ease:"power2.out"}},{j.t(s["pulse_at"]):.3f});')
    return c


def main(spec):
    j = Job(spec, 'trial-reels')
    outs = []
    for n, make in enumerate((v1, v2, v3), 1):
        s = j.get(f'v{n}') or {}
        out = j.out.with_name(f'{j.out.stem}-{n}.mp4')
        outs.append(j.finish(make(j, s), out))
    print('\nthree versions:\n' + '\n'.join(f'  {o}' for o in outs))


if __name__ == '__main__':
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    main(sys.argv[1])
