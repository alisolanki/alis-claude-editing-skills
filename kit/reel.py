#!/usr/bin/env python3
"""Shared kit for the editing skills: clip prep, word timings, captions, HyperFrames comps, render and checks.

    python kit/reel.py words <video> [--start S] [--end E]            # word@start per sentence + when it ends (transcribes on first use)
    python kit/reel.py frame <video> <t> <out.jpg> [--format F]       # one frame with x/y rulers, to find eyes, chin and face centre
    python kit/reel.py sheet <video.mp4> <out.jpg> [n]                # contact sheet with the platform safe zone drawn
    python kit/reel.py probe <video>                                  # size, duration and the format "auto" would pick

Two canvases: "vertical" (1080x1920, reels, shorts, vertical long-form) and "horizontal" (1920x1080, YouTube-style
long-form). A spec's "format" picks one; "auto" (the default) follows the source's shape.

Every skill's build.py is `Job(spec) -> Comp -> finish()`: the spec is a JSON file the skill's SKILL.md describes,
with paths relative to the spec file and times either in seconds (local to "start") or a spoken word to anchor on
("carousel", "carousel#2" for its second time, "carousel+0.2" for a little after it).
"""
import argparse
import glob
import html
import json
import math
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

KIT = Path(__file__).resolve().parent
sys.path.insert(0, str(KIT))
import theme  # noqa: E402

FPS = 30
HYPERFRAMES = 'hyperframes@0.8.34'
FORMATS = {'vertical': (1080, 1920), 'horizontal': (1920, 1080)}
# (top, bottom, side): text and graphics stay inside. Vertical: Instagram/TikTok/Shorts UI covers the top ~220 px
# and the bottom ~420 px. Horizontal: the YouTube player's title bar, controls and progress bar.
SAFE = {'vertical': (220, 1500, 100), 'horizontal': (80, 960, 120)}
W, H = FORMATS['vertical']                                  # kept for older imports
SAFE_TOP, SAFE_BOTTOM, SAFE_SIDE = SAFE['vertical']


def frame_vf(w, h):
    return f'scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h},setsar=1'


FRAME_VF = frame_vf(W, H)


def video_size(path):
    s = json.loads(subprocess.check_output(['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries',
                                            'stream=width,height:stream_side_data=rotation', '-of', 'json', str(path)]))['streams'][0]
    w, h = int(s['width']), int(s['height'])
    rot = next((abs(int(float(d.get('rotation', 0)))) for d in s.get('side_data_list', []) if 'rotation' in d), 0)
    return (h, w) if rot in (90, 270) else (w, h)


def pick_format(fmt, video=None):
    """'vertical' | 'horizontal' | 'auto' (follow the source's shape)"""
    fmt = (fmt or 'auto').lower()
    fmt = {'9:16': 'vertical', 'portrait': 'vertical', '16:9': 'horizontal', 'landscape': 'horizontal'}.get(fmt, fmt)
    if fmt == 'auto':
        if video is None:
            return 'vertical'
        w, h = video_size(video)
        return 'horizontal' if w > h else 'vertical'
    if fmt not in FORMATS:
        sys.exit(f'format must be vertical, horizontal or auto, not {fmt}')
    return fmt


def snap(t):
    """a time on the 30 fps frame grid"""
    return round(float(t) * FPS) / FPS


FONT_CSS = """
@font-face{font-family:'Inter';font-weight:400;src:url(fonts/inter-400-normal.woff2) format('woff2')}
@font-face{font-family:'Inter';font-weight:500;src:url(fonts/inter-500-normal.woff2) format('woff2')}
@font-face{font-family:'Inter';font-weight:600;src:url(fonts/inter-600-normal.woff2) format('woff2')}
@font-face{font-family:'Inter';font-weight:700;src:url(fonts/inter-700-normal.woff2) format('woff2')}
@font-face{font-family:'Inter';font-weight:800;src:url(fonts/inter-800-normal.woff2) format('woff2')}
@font-face{font-family:'Archivo Black';src:url(fonts/archivo-black-400-normal.woff2) format('woff2')}
@font-face{font-family:'DM Serif Display';font-style:italic;src:url(fonts/dm-serif-display-400-italic.woff2) format('woff2')}
@font-face{font-family:'Instrument Serif';src:url(fonts/InstrumentSerif-400-normal.woff2) format('woff2')}
@font-face{font-family:'Instrument Serif';font-style:italic;src:url(fonts/InstrumentSerif-400-italic.woff2) format('woff2')}
@font-face{font-family:'Pixelify Sans';font-weight:500;src:url(fonts/PixelifySans-500-normal.woff2) format('woff2')}
@font-face{font-family:'Pixelify Sans';font-weight:700;src:url(fonts/PixelifySans-700-normal.woff2) format('woff2')}
@font-face{font-family:'TikTok Sans';font-weight:100 900;src:url(fonts/TikTokSans.ttf) format('truetype')}
"""


def base_css(w, h):
    return FONT_CSS + f"""*{{margin:0;padding:0;box-sizing:border-box}}
html,body{{width:{w}px;height:{h}px;overflow:hidden;background:#000}}
#root{{position:relative;width:{w}px;height:{h}px;overflow:hidden;font-family:'Inter',sans-serif;
  -webkit-font-smoothing:antialiased;font-feature-settings:'ss01','cv11'}}
video{{display:block;object-fit:fill}}
.a{{position:absolute}}
.hid{{visibility:hidden}}
img{{display:block}}
"""


BASE_CSS = base_css(W, H)


def run(cmd, **kw):
    return subprocess.run([str(c) for c in cmd], check=True, **kw)


def duration(path):
    return float(subprocess.check_output(['ffprobe', '-v', 'error', '-show_entries', 'format=duration',
                                          '-of', 'default=nw=1:nk=1', str(path)]))


def bare(w):
    """a word as captions show it: lowercase, no punctuation (numbers keep their commas)"""
    keep = ''.join(c for c in w.lower() if c.isalnum() or c in "'’,-").strip('-')
    return keep.replace(',', '') if not keep.replace(',', '').isdigit() else keep


def rich(s):
    """escape, then *word* -> <em>word</em> and newlines -> <br>"""
    s = html.escape(str(s))
    s = re.sub(r'\*(.+?)\*', r'<em>\1</em>', s, flags=re.S)
    return s.replace('\n', '<br>')


# ---------------------------------------------------------------- the job: spec + clip + words
class Job:
    def __init__(self, spec_path, skill):
        self.spec_file = Path(spec_path).resolve()
        self.s = json.loads(self.spec_file.read_text())
        self.base = self.spec_file.parent
        self.skill = skill
        self.video = self.path(self.s['video'])
        if not self.video.exists():
            sys.exit(f'video not found: {self.video}')
        self.fmt = pick_format(self.s.get('format'), self.video)
        self.W, self.H = FORMATS[self.fmt]
        self.horizontal = self.fmt == 'horizontal'
        self.safe = SAFE[self.fmt]
        self.start = snap(self.s.get('start', 0))
        self.end = float(self.s.get('end') or duration(self.video))
        self.out = self.path(self.s.get('out') or f'{self.video.stem}.{skill}.mp4')
        self.out.parent.mkdir(parents=True, exist_ok=True)
        self.work = self.out.parent / '.work' / self.out.stem
        self.work.mkdir(parents=True, exist_ok=True)
        self.clip = prep_clip(self.video, self.start, self.end, self.work, self.W, self.H)
        self.dur = math.floor(duration(self.clip) * FPS - 1) / FPS
        tr = self.s.get('transcript')
        self.words = load_words(self.video, self.start, self.end, self.path(tr) if tr else None)

    def get(self, key, default=None):
        return self.s.get(key, default)

    def pick(self, vertical, horizontal):
        """a layout value for this job's canvas"""
        return horizontal if self.horizontal else vertical

    def path(self, v):
        p = Path(os.path.expanduser(str(v)))
        return p if p.is_absolute() else (self.base / p).resolve()

    def images(self, v):
        """a list of paths, or one glob ("covers/*.jpg"), -> sorted list of existing paths"""
        if not v:
            return []
        items = v if isinstance(v, list) else [v]
        out = []
        for it in items:
            p = str(self.path(it))
            hits = sorted(glob.glob(p)) if any(ch in p for ch in '*?[') else [p]
            for h in hits:
                if not Path(h).exists():
                    sys.exit(f'image not found: {h}')
                out.append(Path(h))
        return out

    def t(self, v, default=None):
        """seconds (local to start), or a spoken word to anchor on: "word", "word#2", "word+0.2", "two words" """
        if v is None:
            if default is None:
                raise ValueError('a time is missing')
            return float(default)
        if isinstance(v, (int, float)):
            return float(v)
        m = re.match(r'^(.+?)(?:#(\d+))?([+-]\d*\.?\d+)?$', str(v).strip())
        target = [bare(x) for x in m.group(1).split()]
        nth = int(m.group(2) or 1)
        shift = float(m.group(3) or 0)
        seen = 0
        bw = [bare(w) for w, _, _ in self.words]
        for i in range(len(bw)):
            if bw[i:i + len(target)] == target:
                seen += 1
                if seen == nth:
                    return round(max(0.0, self.words[i][1] + shift), 3)
        said = ' '.join(f'{w}@{t:.2f}' for w, t, _ in self.words)
        raise ValueError(f'"{v}" is not said in this clip. Words: {said}')

    def cutout(self, model=None):
        out = self.work / 'cutout.webm'
        stamp = self.work / 'cutout.ok'
        if out.exists() and stamp.exists() and stamp.read_text() == str(self.clip.stat().st_mtime):
            return out
        sys.path.insert(0, str(KIT))
        from cutout import cutout
        cutout(self.clip, out, model or self.get('cutout_model', 'mobilenetv3'))
        stamp.write_text(str(self.clip.stat().st_mtime))
        return out

    def finish(self, comp, out=None):
        out = Path(out or self.out)
        comp.write()
        comp.render(out)
        sh = out.with_name(out.stem + '.sheet.jpg')
        sheet(out, sh)
        ui = 'the YouTube player' if self.horizontal else 'the Instagram / TikTok UI'
        print(f'\nDONE  {out}\ncheck {sh}  (red = covered by {ui})')
        return out


def prep_clip(video, start, end, work, w=1080, h=1920):
    """the segment as a WxH, 30 fps, frame-accurate clip (cached)"""
    out = work / 'clip.mp4'
    key = json.dumps([str(video), os.path.getmtime(video), start, end, w, h])
    stamp = work / 'clip.key'
    if out.exists() and stamp.exists() and stamp.read_text() == key:
        return out
    run(['ffmpeg', '-v', 'error', '-y', '-ss', f'{start:.3f}', '-i', video, '-t', f'{end - start:.3f}',
         '-vf', f'{frame_vf(w, h)},fps={FPS}', '-c:v', 'libx264', '-preset', 'fast', '-crf', '14', '-pix_fmt', 'yuv420p',
         '-c:a', 'aac', '-b:a', '192k', '-ar', '48000', '-movflags', '+faststart', out])
    stamp.write_text(key)
    return out


def load_words(video, start, end, transcript=None):
    """[(word, local_start, local_end)] for the words said between start and end"""
    tp = transcript or Path(video).with_name(Path(video).stem + '.transcript.json')
    if not Path(tp).exists():
        sys.path.insert(0, str(KIT))
        from transcribe import transcribe
        print('transcribing (one time)...', flush=True)
        transcribe(video, tp)
    d = json.loads(Path(tp).read_text())
    ws = d.get('words') or [w for s in d.get('segments', []) for w in s.get('words', [])]
    # Whisper sometimes starts a sentence's first word before the last word of the previous one has ended
    # ("this.@7.02-7.44 For@6.90"): push such starts to the previous end so words stay in order
    fixed, prev_end = [], 0.0
    for w in ws:
        st = max(float(w['start']), prev_end)
        en = max(float(w['end']), st + 0.05)
        fixed.append((w['word'].strip(), st, en))
        prev_end = en
    out = []
    for w, st, en in fixed:
        if start - 0.05 <= st < end - 0.08:
            out.append((w, round(max(st, start) - start, 3), round(min(en, end) - start, 3)))
    return out


# ---------------------------------------------------------------- the composition
class Comp:
    def __init__(self, job, name='main', voice=True, dur=None):
        self.job, self.dur = job, dur or job.dur
        self.W, self.H = job.W, job.H
        self.dir = job.work / f'comp_{name}'
        self.css, self.body, self.js = [base_css(self.W, self.H)], [], []
        self.track = 0
        self.files = {}
        if voice and has_audio(job.clip):
            self.body.append(f'<audio id="voice" src="{self.asset(job.clip)}" data-start="0" data-media-start="0" '
                             f'data-duration="{self.dur:.3f}" data-track-index="{self.nt()}" data-volume="1"></audio>')

    def nt(self):
        self.track += 1
        return self.track

    def asset(self, path):
        """register a file and return its path inside the comp"""
        path = Path(path).resolve()
        if path not in self.files:
            self.files[path] = f'assets/{len(self.files):02d}_{re.sub(r"[^A-Za-z0-9._-]", "_", path.name)}'
        return self.files[path]

    def video(self, path, style, vid, start=0, media_start=0, dur=None, cls=''):
        dur = self.dur - start if dur is None else dur
        return (f'<video id="{vid}" class="{cls}" src="{self.asset(path)}" muted playsinline data-start="{start:.3f}" '
                f'data-media-start="{media_start:.3f}" data-duration="{dur:.3f}" data-track-index="{self.nt()}" '
                f'style="{style}"></video>')

    def write(self):
        gsap = KIT / 'vendor' / 'gsap.min.js'
        if not gsap.exists():
            sys.exit(f'missing {gsap}: run kit/setup.sh once')
        if self.dir.exists():
            shutil.rmtree(self.dir)
        (self.dir / 'assets').mkdir(parents=True)
        shutil.copytree(KIT / 'fonts', self.dir / 'fonts')
        (self.dir / 'vendor').mkdir()
        shutil.copy(gsap, self.dir / 'vendor' / 'gsap.min.js')
        for src, rel in self.files.items():
            try:
                os.link(src, self.dir / rel)
            except OSError:
                shutil.copy(src, self.dir / rel)
        (self.dir / 'hyperframes.json').write_text(json.dumps({'$schema': 'https://hyperframes.heygen.com/schema/hyperframes.json',
                                                               'media': {'autoProxy': True}}, indent=2))
        (self.dir / 'index.html').write_text(f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><style>{''.join(self.css)}</style></head>
<body>
<div id="root" data-composition-id="main" data-start="0" data-duration="{self.dur:.3f}" data-fps="{FPS}" data-width="{self.W}" data-height="{self.H}">
{chr(10).join(self.body)}
<script src="vendor/gsap.min.js"></script>
<script>
(function () {{
const gsap = window.gsap;
const tl = gsap.timeline({{ paused: true }});
{chr(10).join(self.js)}
tl.set({{}}, {{}}, {self.dur:.3f});
window.__timelines = window.__timelines || {{}};
window.__timelines["main"] = tl;
}})();
</script>
</div>
</body>
</html>''')

    def render(self, out):
        out = Path(out)
        if out.exists():
            out.unlink()
        print(f'rendering {out.name} ...', flush=True)
        r = subprocess.run(['npx', '--yes', HYPERFRAMES, 'render', str(self.dir), '-o', str(out), '--fps', str(FPS), '-q', 'high'],
                           capture_output=True, text=True)
        if not out.exists():
            sys.exit(f'render failed:\n{r.stdout[-3000:]}\n{r.stderr[-3000:]}')
        print('\n'.join(l for l in r.stdout.splitlines() if 'rendered in' in l or '✗' in l))


# ---------------------------------------------------------------- captions
def chunks(ws, maxc=22, maxw=4):
    """greedy one-line chunks: at most maxc characters and maxw words, broken at punctuation"""
    out, cur = [], []
    for w, t, *_ in ws:
        b = bare(w)
        if not b:
            continue
        if cur and (len(' '.join(x for x, _ in cur + [(b, 0)])) > maxc or len(cur) >= maxw):
            out.append(cur)
            cur = []
        cur.append((b, t))
        if w.endswith(('.', ',', '?', '!')) and len(cur) >= 2:
            out.append(cur)
            cur = []
    if cur:
        out.append(cur)
    return out


def karaoke(c, ws, top, cid='kc', maxc=22, size=56, plate=True, font="700 {s}px/1 'Inter'", grey='rgba(255,255,255,.42)',
            white='#fff', upper=False, lead=0.04, end=None, left=0, width=None):
    """Clean Karaoke: one line, lowercase, no punctuation, each word turns from dim to white as it is said"""
    end = c.dur if end is None else end
    width = c.W if width is None else width
    cs = chunks(ws, maxc)
    c.css.append(f'''.{cid}{{position:absolute;left:{left}px;width:{width}px;top:{top}px;text-align:center;visibility:hidden}}
.{cid} span.p{{display:inline-block;padding:14px 26px 17px;border-radius:20px;{'background:rgba(11,11,15,.78);' if plate else ''}
font:{font.format(s=size)};letter-spacing:-.025em;white-space:nowrap;{'text-transform:uppercase;' if upper else ''}}}
.{cid} span.w{{color:{grey}}}''')
    for i, ch in enumerate(cs):
        t0 = max(0, ch[0][1] - lead)
        t1 = cs[i + 1][0][1] - lead if i + 1 < len(cs) else end
        spans = ' '.join(f'<span class="w" id="{cid}{i}_{j}">{html.escape(w)}</span>' for j, (w, _) in enumerate(ch))
        c.body.append(f'<div class="{cid}" id="{cid}{i}"><span class="p">{spans}</span></div>')
        c.js.append(f'tl.set("#{cid}{i}",{{visibility:"visible"}},{t0:.3f});tl.set("#{cid}{i}",{{visibility:"hidden"}},{t1:.3f});')
        for j, (w, t) in enumerate(ch):
            c.js.append(f'tl.set("#{cid}{i}_{j}",{{color:"{white}"}},{max(t0, t - 0.02):.3f});')


def groups(ws, maxw=3, maxc=15):
    """short caption groups (TikTok style): 1-3 words, at most maxc characters, broken at punctuation"""
    out, cur = [], []
    for w, t, *_ in ws:
        b = bare(w)
        if not b:
            continue
        if cur and (len(cur) >= maxw or len(' '.join(x for x, _ in cur + [(b, 0)])) > maxc):
            out.append(cur)
            cur = []
        cur.append((b, t))
        if w.endswith(('.', ',', '?', '!')):
            out.append(cur)
            cur = []
    if cur:
        out.append(cur)
    return out


def caption_css(cid, top, width, size=64, left=0, align='center', dark=False):
    """the house caption: Inter 800, tight, white with a soft shadow; key words sit on an accent pill"""
    fg, sh = (theme.INK, 'none') if dark else ('#fff', '0 2px 4px rgba(0,0,0,.35),0 6px 28px rgba(0,0,0,.45)')
    return (f".{cid}{{position:absolute;left:{left}px;width:{width}px;top:{top}px;text-align:{align};visibility:hidden;"
            f"font:800 {size}px/1.08 'Inter';color:{fg};letter-spacing:-.03em;text-shadow:{sh}}}"
            f".{cid} .k{{background:{theme.ACCENT};color:#fff;text-shadow:none;padding:.02em .2em .08em;border-radius:.22em;"
            f"-webkit-box-decoration-break:clone;box-decoration-break:clone}}")


def word_caps(c, ws, cid, css, maxw=3, maxc=15, keys=(), key_tag='span class="k"', pop=None, lead=0.04, karaoke_dim=None):
    """one div per caption group, shown from its first word to the next group. keys = words to mark (class k or <em>).
    pop = (from_scale, duration) for a small pop on each group. karaoke_dim = colour for words not said yet."""
    keys = {bare(k) for k in keys}
    c.css.append(css)
    gs = groups(ws, maxw, maxc)
    close = key_tag.split()[0]
    for i, g in enumerate(gs):
        t0 = max(0, g[0][1] - lead)
        t1 = gs[i + 1][0][1] - lead if i + 1 < len(gs) else c.dur
        parts = []
        for j, (w, t) in enumerate(g):
            txt = html.escape(w)
            if w in keys:
                txt = f'<{key_tag}>{txt}</{close}>'
            parts.append(f'<span class="w" id="{cid}{i}_{j}">{txt}</span>' if karaoke_dim else txt)
            if karaoke_dim:
                c.js.append(f'tl.set("#{cid}{i}_{j}",{{color:"#fff"}},{max(t0, t - 0.02):.3f});')
        c.body.append(f'<div class="{cid}" id="{cid}{i}">{" ".join(parts)}</div>')
        c.js.append(f'tl.set("#{cid}{i}",{{visibility:"visible"}},{t0:.3f});tl.set("#{cid}{i}",{{visibility:"hidden"}},{t1:.3f});')
        if pop:
            c.js.append(f'tl.fromTo("#{cid}{i}",{{scale:{pop[0]}}},{{scale:1,duration:{pop[1]},ease:"back.out(2)"}},{t0:.3f});')
    if karaoke_dim:
        c.css.append(f'.{cid} span.w{{color:{karaoke_dim}}}')


# ---------------------------------------------------------------- shared pieces
def cover_html(c, w, image=None, text='', cta='SWIPE →', cls='cover', extra=''):
    """a carousel-cover card, 4:5: photo, dark fade, big text (*word* sits on an accent pill), small CTA"""
    s = w / 280
    bg = f'url({c.asset(image)}) center/cover' if image else f'linear-gradient(160deg,{theme.ACCENT},{theme.ACCENT_DEEP})'
    t = rich(text).replace('<em>', f'<span style="background:{theme.ACCENT};padding:0 {3*s:.0f}px;border-radius:{4*s:.0f}px">').replace('</em>', '</span>')
    return f'''<div class="{cls}" {extra} style="width:{w}px;height:{w*1.25:.0f}px;position:relative;overflow:hidden;border-radius:{10*s:.0f}px;
background:#222 {bg}">
<div class="a" style="inset:0;background:linear-gradient(180deg,rgba(0,0,0,0) 30%,rgba(0,0,0,.72) 100%)"></div>
<div class="a" style="left:{14*s:.0f}px;right:{14*s:.0f}px;bottom:{38*s:.0f}px;font:800 {27*s:.1f}px/1.04 'Inter';color:#fff;
letter-spacing:-.03em;text-align:center;text-shadow:0 {2*s:.0f}px {8*s:.0f}px rgba(0,0,0,.35)">{t}</div>
<div class="a" style="left:0;right:0;bottom:{14*s:.0f}px;text-align:center;font:700 {10*s:.1f}px 'Inter';color:#fff;letter-spacing:.12em">{html.escape(cta)}</div>
</div>'''


def count_js(target_ids, to, at, dur=0.62, fmt='comma', prefix=''):
    """count a number up from 0 into one or more elements (fmt: comma | time | plain)"""
    if fmt == 'time':
        f = "Math.floor(s/60)+':'+String(s%60).padStart(2,'0')"
    elif fmt == 'comma':
        f = "s.toLocaleString('en-US')"
    else:
        f = 'String(s)'
    sets = ''.join(f"document.getElementById('{i}').textContent={json.dumps(prefix)}+{f};" for i in target_ids)
    v = 'cnt' + target_ids[0].replace('-', '_')
    return (f'const {v}={{v:0}};tl.to({v},{{v:{to},duration:{dur},ease:"power2.out",onUpdate:()=>{{const s=Math.round({v}.v);'
            f'{sets}}}}},{at:.3f});')


def parse_number(v):
    """"10,000" -> (10000, 'comma'); "4:12" -> (252, 'time'); "12" -> (12, 'plain'); otherwise None"""
    v = str(v).strip()
    if re.fullmatch(r'\d+:\d\d', v):
        m, s = v.split(':')
        return int(m) * 60 + int(s), 'time'
    if re.fullmatch(r'\d{1,3}(,\d{3})+', v):
        return int(v.replace(',', '')), 'comma'
    if re.fullmatch(r'\d+', v):
        return int(v), 'comma' if len(v) > 3 else 'plain'
    return None


# ---------------------------------------------------------------- checks
def has_audio(path):
    out = subprocess.check_output(['ffprobe', '-v', 'error', '-select_streams', 'a', '-show_entries', 'stream=index',
                                   '-of', 'csv=p=0', str(path)], text=True)
    return bool(out.strip())


def frame(video, t, out, fmt='auto'):
    """one frame on the job's canvas (1080x1920 or 1920x1080) with rulers every 100 px, to read the eyes, chin and face centre"""
    from PIL import Image, ImageDraw, ImageFont
    fmt = pick_format(fmt, video)
    w, h = FORMATS[fmt]
    tmp = Path(out).with_suffix('.raw.png')
    run(['ffmpeg', '-v', 'error', '-y', '-ss', f'{t:.3f}', '-i', video, '-frames:v', '1', '-vf', frame_vf(w, h), tmp])
    im = Image.open(tmp).convert('RGB')
    d = ImageDraw.Draw(im)
    try:
        font = ImageFont.load_default(size=40)
    except TypeError:
        font = ImageFont.load_default()
    col = (255, 214, 0)          # a ruler, not branding: bright on any footage
    for y in range(100, h, 100):
        d.line((0, y, w if y % 500 == 0 else 70, y), fill=col, width=3 if y % 500 else 4)
        d.text((80, y - 22), str(y), fill=col, font=font, stroke_width=3, stroke_fill=(0, 0, 0))
    for x in range(200, w, 200):
        d.line((x, 0, x, h if x % 1000 == 0 else 50), fill=col, width=3)
        d.text((x + 6, 56), str(x), fill=col, font=font, stroke_width=3, stroke_fill=(0, 0, 0))
    im.resize((w // 2, h // 2)).save(out, quality=90)
    tmp.unlink()


def sheet(video, out, n=8):
    """contact sheet of a finished video; the parts the platform UI covers are tinted red"""
    from PIL import Image, ImageDraw
    d = duration(video)
    vw, vh = video_size(video)
    fmt = 'horizontal' if vw > vh else 'vertical'
    fw, fh = FORMATS[fmt]
    top, bottom, side = SAFE[fmt]
    tw, th = (384, 216) if fmt == 'horizontal' else (270, 480)
    cols = 4 if fmt == 'horizontal' else n
    rows = math.ceil(n / cols)
    im = Image.new('RGB', (tw * cols, (th + 30) * rows), 'black')
    dr = ImageDraw.Draw(im)
    tmp = Path(out).with_suffix('.f.png')
    for i in range(n):
        t = d * (i + 0.5) / n
        run(['ffmpeg', '-v', 'error', '-y', '-ss', f'{t:.3f}', '-i', video, '-frames:v', '1', '-vf', f'scale={tw}:{th}', tmp])
        f = Image.open(tmp).convert('RGBA')
        ov = Image.new('RGBA', f.size, (0, 0, 0, 0))
        od = ImageDraw.Draw(ov)
        k = tw / fw
        for box in ((0, 0, tw, top * k), (0, bottom * k, tw, th), (0, 0, side * k, th), (tw - side * k, 0, tw, th)):
            od.rectangle(box, fill=(255, 0, 0, 46))
        x, y = (i % cols) * tw, (i // cols) * (th + 30)
        im.paste(Image.alpha_composite(f, ov).convert('RGB'), (x, y + 30))
        dr.text((x + 6, y + 8), f'{t:.2f}s', fill=(255, 255, 255))
    im.save(out, quality=88)
    tmp.unlink()


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = ap.add_subparsers(dest='cmd', required=True)
    a = sp.add_parser('words')
    a.add_argument('video')
    a.add_argument('--start', type=float, default=0)
    a.add_argument('--end', type=float)
    a.add_argument('--transcript')
    b = sp.add_parser('frame')
    b.add_argument('video')
    b.add_argument('t', type=float)
    b.add_argument('out')
    b.add_argument('--format', default='auto')
    pr = sp.add_parser('probe')
    pr.add_argument('video')
    s = sp.add_parser('sheet')
    s.add_argument('video')
    s.add_argument('out')
    s.add_argument('n', type=int, nargs='?', default=8)
    x = ap.parse_args()
    if x.cmd == 'words':
        end = x.end or duration(x.video)
        ws = load_words(x.video, x.start, end, x.transcript)
        # one sentence per line; times are local to --start; [ends] is when the sentence's last word ends,
        # so start + that is a clean "end" for a spec
        line = []
        for w, t, e in ws:
            line.append(f'{w}@{t:.2f}')
            if w.endswith(('.', '?', '!')):
                print(' '.join(line) + f'   [ends {e:.2f}]')
                line = []
        if line:
            print(' '.join(line) + f'   [ends {ws[-1][2]:.2f}]')
    elif x.cmd == 'frame':
        frame(x.video, x.t, x.out, x.format)
        print('wrote', x.out)
    elif x.cmd == 'probe':
        w, h = video_size(x.video)
        f = pick_format('auto', x.video)
        print(f'{w}x{h}  {duration(x.video):.2f}s  audio={"yes" if has_audio(x.video) else "no"}  format=auto -> {f} '
              f'({FORMATS[f][0]}x{FORMATS[f][1]}, safe top/bottom/side {SAFE[f]})')
    else:
        sheet(x.video, x.out, x.n)
        print('wrote', x.out)


if __name__ == '__main__':
    main()
