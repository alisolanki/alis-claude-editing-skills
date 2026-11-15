#!/usr/bin/env python3
"""Long-form editing: whole talking-head videos (minutes to hours), horizontal 16:9 or vertical 9:16.

    python kit/longform.py tighten <video> [--max-gap 0.45] [--pad 0.12] [--cut-fillers]
        -> <video>.tight.mp4 + <video>.tight.transcript.json   (pauses shortened, word times remapped, cut points kept)
    python kit/longform.py build <spec.json>
        -> <out>.mp4, <out>.srt, <out>.chapters.txt, <out>.sheet.jpg

The build cuts the timeline into segments and encodes each one once:
  - plain stretches of the take, with optional punch-in zooms (alternating on cuts or sentences hides jump cuts),
    burned-in house captions and chapter cards drawn as a flipbook of transparent PNGs (no libass needed);
  - "moments": short stretches rendered by another skill (explainer, split-screen, behind-the-person,
    ranking-list, storytelling) and spliced back in at the exact frame, over the original audio.
The audio is never cut between segments (PCM until the final AAC encode), so joins are seamless.
"""
import argparse
import hashlib
import json
import math
import os
import re
import shutil
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

KIT = Path(__file__).resolve().parent
sys.path.insert(0, str(KIT))
import theme as T  # noqa: E402
from reel import (FORMATS, FPS, SAFE, bare, duration, frame_vf, groups, has_audio, load_words,  # noqa: E402
                  pick_format, sheet, snap)

MOMENT_SKILLS = ('explainer', 'split-screen', 'behind-the-person', 'ranking-list', 'storytelling')
FILLERS = {'um', 'uh', 'erm', 'er', 'ah', 'hmm', 'mm', 'uhm', 'umm'}
SKILLS = KIT.parent / 'skills'


def run(cmd):
    r = subprocess.run([str(c) for c in cmd], capture_output=True, text=True)
    if r.returncode:
        sys.exit(f'command failed: {" ".join(map(str, cmd))[:400]}\n{r.stderr[-2000:]}')
    return r


def fmt_time(t, srt=False):
    t = max(0.0, t)
    h, m, s = int(t // 3600), int(t % 3600 // 60), t % 60
    if srt:
        return f'{h:02d}:{m:02d}:{int(s):02d},{int(round((s - int(s)) * 1000)) % 1000:03d}'
    return f'{h}:{m:02d}:{int(s):02d}' if h else f'{m}:{int(s):02d}'


# ---------------------------------------------------------------- segments
def encode_segment(src, a, d, out, w=None, h=None, vf_extra='', overlay=None, video_src=None, audio=True):
    """one piece of the timeline: H.264 video, PCM audio, exactly round(d*30) frames, into an .mkv"""
    frames = max(1, round(d * FPS))
    cmd = ['ffmpeg', '-v', 'error', '-y']
    if video_src:                              # a rendered moment: its picture, the source's audio
        cmd += ['-i', video_src, '-ss', f'{a:.4f}', '-i', src]
        vin, ain = '0:v', '1:a'
    else:
        cmd += ['-ss', f'{a:.4f}', '-i', src]
        vin, ain = '0:v', '0:a'
    chain = [f'[{vin}]fps={FPS}']
    if w and not video_src:
        chain.append(frame_vf(w, h))
    if vf_extra:
        chain.append(vf_extra)
    graph = ','.join(chain) + '[v]'
    last = '[v]'
    if overlay:
        idx = 2 if video_src else 1
        cmd += ['-f', 'concat', '-safe', '0', '-i', overlay]
        graph += f';[{idx}:v]fps={FPS},format=rgba[o];[v][o]overlay=0:0:eof_action=pass:format=auto[vo]'
        last = '[vo]'
    graph += f';{last}format=yuv420p[out]'
    cmd += ['-filter_complex', graph, '-map', '[out]']
    if audio:
        cmd += ['-map', ain, '-c:a', 'pcm_s16le', '-ar', '48000', '-ac', '2', '-t', f'{frames / FPS:.4f}']
    cmd += ['-frames:v', str(frames), '-r', str(FPS), '-c:v', 'libx264', '-preset', 'medium', '-crf', '16',
            '-pix_fmt', 'yuv420p', '-g', str(FPS * 2), out]
    run(cmd)
    return out


def concat(parts, out, audio=True, loudness=None):
    lst = Path(out).with_suffix('.concat.txt')
    lst.write_text(''.join(f"file '{Path(p).resolve()}'\n" for p in parts))
    cmd = ['ffmpeg', '-v', 'error', '-y', '-f', 'concat', '-safe', '0', '-i', lst, '-c:v', 'copy']
    if audio:
        af = ['-af', f'loudnorm=I={loudness}:TP=-1.5:LRA=11'] if loudness is not None else []
        cmd += af + ['-c:a', 'aac', '-b:a', '192k', '-ar', '48000']
    cmd += ['-movflags', '+faststart', out]
    run(cmd)
    lst.unlink()
    return out


def parallel(jobs, workers=None):
    workers = workers or max(1, min(4, (os.cpu_count() or 4) // 2))
    with ThreadPoolExecutor(workers) as ex:
        for i, _ in enumerate(ex.map(lambda f: f(), jobs), 1):
            if i % 10 == 0 or i == len(jobs):
                print(f'  {i}/{len(jobs)} segments', flush=True)


# ---------------------------------------------------------------- tighten
def tighten(video, max_gap=0.45, pad=0.12, cut_fillers=False, out=None):
    """shorten every pause longer than max_gap to about 2*pad; optionally drop um/uh. Writes the tight video and a
    transcript on the new timeline (with "cuts": where each join landed), so the build can hide joins with punch-ins."""
    video = Path(video).resolve()
    out = Path(out) if out else video.with_name(video.stem + '.tight.mp4')
    total = duration(video)
    pad = min(pad, max_gap / 2)
    words = load_words(video, 0, total)
    speech = [w for w in words if not (cut_fillers and bare(w[0]) in FILLERS)]
    if not speech:
        sys.exit('no speech found to tighten around')
    regions = []
    for w, st, en in speech:
        if regions and st - regions[-1][1] <= max_gap:
            regions[-1][1] = max(regions[-1][1], en)
        else:
            regions.append([st, en])
    ranges = []
    for a, b in regions:
        a, b = math.floor(max(0, a - pad) * FPS) / FPS, min(total, math.ceil((b + pad) * FPS) / FPS)
        if ranges and a <= ranges[-1][1] + 1e-6:
            ranges[-1][1] = max(ranges[-1][1], b)
        else:
            ranges.append([a, b])
    kept = sum(b - a for a, b in ranges)
    print(f'tighten: {total:.1f}s -> {kept:.1f}s ({len(ranges)} pieces, {total - kept:.1f}s of pauses removed)', flush=True)
    work = out.with_name('.work') / out.stem
    work.mkdir(parents=True, exist_ok=True)
    aud = has_audio(video)
    parts = [work / f'p{i:05d}.mkv' for i in range(len(ranges))]
    parallel([lambda i=i, r=r: encode_segment(video, r[0], r[1] - r[0], parts[i], audio=aud) for i, r in enumerate(ranges)])
    concat(parts, out, audio=aud)
    # remap the words onto the new timeline
    new, cuts, off = [], [], 0.0
    for k, (a, b) in enumerate(ranges):
        if k:
            cuts.append(round(off, 3))
        for w, st, en in words:
            if a - 1e-3 <= st < b and not (cut_fillers and bare(w) in FILLERS):
                new.append({'word': w, 'start': round(st - a + off, 3), 'end': round(min(en, b) - a + off, 3)})
        off += round((b - a) * FPS) / FPS
    tr = out.with_name(out.stem + '.transcript.json')
    tr.write_text(json.dumps({'text': ' '.join(x['word'] for x in new), 'words': new, 'cuts': cuts,
                              'source': str(video), 'ranges': ranges, 'duration': off}, indent=1, ensure_ascii=False))
    shutil.rmtree(work, ignore_errors=True)
    print(f'wrote {out}\nwrote {tr}')
    return out


# ---------------------------------------------------------------- overlay flipbook (captions + chapter cards)
class Flipbook:
    """the overlay as a list of states; each distinct state is one transparent PNG"""

    def __init__(self, w, h, work):
        from PIL import ImageFont
        sys.path.insert(0, str(KIT))
        from fonts import ttf
        self.w, self.h = w, h
        self.dir = work / 'overlay'
        self.dir.mkdir(parents=True, exist_ok=True)
        self.bold = lambda s: ImageFont.truetype(str(ttf('inter-800-normal.woff2')), s)
        self.semi = lambda s: ImageFont.truetype(str(ttf('inter-600-normal.woff2')), s)
        self.cache = {}

    def caption(self, words, said, keys, size, cy, maxw):
        """one line, centred on cy; words already said in white, the rest dimmed; key words on an accent pill"""
        from PIL import Image, ImageDraw, ImageFilter
        f = self.bold(size)
        space = f.getlength(' ')
        widths = [f.getlength(w) for w in words]
        while sum(widths) + space * (len(words) - 1) > maxw and size > 24:
            size -= 4
            f = self.bold(size)
            space = f.getlength(' ')
            widths = [f.getlength(w) for w in words]
        total = sum(widths) + space * (len(words) - 1)
        x = (self.w - total) / 2
        asc, desc = f.getmetrics()
        y = cy - (asc + desc) / 2
        im = Image.new('RGBA', (self.w, self.h), (0, 0, 0, 0))
        sh = Image.new('L', (self.w, self.h), 0)
        sd = ImageDraw.Draw(sh)
        d = ImageDraw.Draw(im)
        xs = []
        for wd, ww in zip(words, widths):
            xs.append(x)
            x += ww + space
        for i, (wd, ww) in enumerate(zip(words, widths)):
            if wd in keys:
                p = size * 0.18
                d.rounded_rectangle((xs[i] - p, y + size * 0.06, xs[i] + ww + p, y + asc + desc * 0.6), radius=size * 0.22,
                                    fill=T.ACCENT_RGB + (255,))
            else:
                sd.text((xs[i], y + size * 0.06), wd, font=f, fill=150)
        sh = sh.filter(ImageFilter.GaussianBlur(size * 0.16))
        shadow = Image.new('RGBA', (self.w, self.h), (0, 0, 0, 0))
        shadow.putalpha(sh)
        im = Image.alpha_composite(shadow, im)
        d = ImageDraw.Draw(im)
        for i, wd in enumerate(words):
            a = 255 if (i < said or wd in keys) else 110
            d.text((xs[i], y), wd, font=f, fill=(255, 255, 255, a))
        return im

    def card(self, num, title, fmt):
        """a chapter card: accent number tile + title on a dark rounded plate"""
        from PIL import Image, ImageDraw
        s = 1.0 if fmt == 'horizontal' else 1.15
        fn, ft = self.bold(round(34 * s)), self.bold(round(44 * s))
        tw = ft.getlength(title)
        tile, padx, ph = round(76 * s), round(28 * s), round(104 * s)
        wdt = round(14 * s + tile + padx + tw + padx)
        im = Image.new('RGBA', (wdt, ph), (0, 0, 0, 0))
        d = ImageDraw.Draw(im)
        d.rounded_rectangle((0, 0, wdt - 1, ph - 1), radius=round(26 * s), fill=(11, 11, 15, 205))
        t0 = (ph - tile) // 2
        d.rounded_rectangle((t0, t0, t0 + tile, t0 + tile), radius=round(18 * s), fill=T.ACCENT_RGB + (255,))
        n = f'{num:02d}'
        d.text((t0 + (tile - fn.getlength(n)) / 2, t0 + tile / 2), n, font=fn, fill=(255, 255, 255, 255), anchor='lm')
        d.text((t0 + tile + padx, ph / 2), title, font=ft, fill=(255, 255, 255, 255), anchor='lm')
        return im

    def state(self, key, parts):
        """parts: [(image, x, y, alpha)] composited in order -> png path (cached by key)"""
        if key in self.cache:
            return self.cache[key]
        from PIL import Image
        im = Image.new('RGBA', (self.w, self.h), (0, 0, 0, 0))
        for p, x, y, a in parts:
            if a < 1:
                p = p.copy()
                p.putalpha(p.getchannel('A').point(lambda v: int(v * a)))
            im.alpha_composite(p, (int(x), int(y)))
        path = self.dir / f'{hashlib.md5(repr(key).encode()).hexdigest()[:16]}.png'
        im.save(path, compress_level=1)
        self.cache[key] = path
        return path


def build_overlay_timeline(words, total, fmt, cap, chapters):
    """[(t0, t1, caption_key | None, chapter_key | None)] covering [0, total], change points on the frame grid"""
    events = []                                  # (t0, t1, kind, payload)
    if cap.get('burn', True):
        maxw, maxc = (cap.get('max_words', 5), cap.get('max_chars', 30)) if fmt == 'horizontal' else (cap.get('max_words', 3), cap.get('max_chars', 18))
        gs = groups(words, maxw, maxc)
        flat = [(bare(w), t, e) for w, t, e in words if bare(w)]
        idx = 0
        for i, g in enumerate(gs):
            idx += len(g)
            last_end = flat[idx - 1][2] if idx - 1 < len(flat) else g[-1][1] + 0.4
            t0 = max(0.0, g[0][1] - 0.04)
            nxt = gs[i + 1][0][1] - 0.04 if i + 1 < len(gs) else total
            t1 = min(nxt, last_end + 0.6)
            text = tuple(w for w, _ in g)
            if cap.get('karaoke', False):
                for j, (w, t) in enumerate(g):
                    a = max(t0, t - 0.02)
                    b = max(t0, g[j + 1][1] - 0.02) if j + 1 < len(g) else t1
                    events.append((a, b, 'cap', (text, j + 1)))
                if g[0][1] - 0.02 > t0:
                    events.append((t0, g[0][1] - 0.02, 'cap', (text, 0)))
            else:
                events.append((t0, t1, 'cap', (text, len(g))))
    for n, ch in enumerate(chapters, 1):
        t0, hold = ch['t'], float(ch.get('duration', 3.2))
        steps = 6
        for s in range(steps):                       # slide + fade in
            events.append((t0 + s / FPS, t0 + (s + 1) / FPS, 'ch', (n, (s + 1) / steps)))
        events.append((t0 + steps / FPS, t0 + hold - steps / FPS, 'ch', (n, 1.0)))
        for s in range(steps):                       # fade out
            events.append((t0 + hold - (steps - s) / FPS, t0 + hold - (steps - s - 1) / FPS, 'ch', (n, 1 - (s + 1) / steps)))
    pts = sorted({0.0, snap(total)} | {snap(min(max(e[0], 0), total)) for e in events} | {snap(min(max(e[1], 0), total)) for e in events})
    out = []
    for a, b in zip(pts, pts[1:]):
        if b - a < 0.5 / FPS:
            continue
        mid = (a + b) / 2
        c = next((e[3] for e in events if e[2] == 'cap' and e[0] <= mid < e[1]), None)
        h = next((e[3] for e in events if e[2] == 'ch' and e[0] <= mid < e[1]), None)
        if out and out[-1][2] == c and out[-1][3] == h and abs(out[-1][1] - a) < 1e-6:
            out[-1] = (out[-1][0], b, c, h)
        else:
            out.append((a, b, c, h))
    return out


# ---------------------------------------------------------------- build
class Long:
    def __init__(self, spec_path):
        self.spec_file = Path(spec_path).resolve()
        self.s = json.loads(self.spec_file.read_text())
        self.base = self.spec_file.parent
        self.video = self.path(self.s['video'])
        if not self.video.exists():
            sys.exit(f'video not found: {self.video}')
        self.fmt = pick_format(self.s.get('format'), self.video)
        self.W, self.H = FORMATS[self.fmt]
        self.start = snap(self.s.get('start', 0))
        self.end = float(self.s.get('end') or duration(self.video))
        self.total = math.floor((self.end - self.start) * FPS) / FPS
        self.out = self.path(self.s.get('out') or f'{self.video.stem}.edited.mp4')
        self.work = self.out.parent / '.work' / self.out.stem
        self.work.mkdir(parents=True, exist_ok=True)
        tr = self.s.get('transcript')
        self.transcript = self.path(tr) if tr else self.video.with_name(self.video.stem + '.transcript.json')
        self.words = load_words(self.video, self.start, self.end, self.transcript)
        meta = json.loads(self.transcript.read_text())
        self.cuts = [c - self.start for c in meta.get('cuts', []) if self.start < c < self.end]
        self.audio = has_audio(self.video)

    def path(self, v):
        p = Path(os.path.expanduser(str(v)))
        return p if p.is_absolute() else (self.base / p).resolve()

    def t(self, v):
        """seconds on the source timeline, or a spoken word ("pricing", "pricing#2", "pricing-0.5") -> local seconds"""
        if isinstance(v, (int, float)):
            return float(v) - self.start
        m = re.match(r'^(.+?)(?:#(\d+))?([+-]\d*\.?\d+)?$', str(v).strip())
        target, nth, shift = [bare(x) for x in m.group(1).split()], int(m.group(2) or 1), float(m.group(3) or 0)
        bw, seen = [bare(w) for w, _, _ in self.words], 0
        for i in range(len(bw)):
            if bw[i:i + len(target)] == target:
                seen += 1
                if seen == nth:
                    return max(0.0, self.words[i][1] + shift)
        sys.exit(f'"{v}" is not said in this video')

    # -- moments
    def render_moments(self):
        out = []
        for k, m in enumerate(self.s.get('moments') or []):
            skill = m.get('skill')
            if skill not in MOMENT_SKILLS:
                sys.exit(f'moment {k}: skill must be one of {", ".join(MOMENT_SKILLS)}')
            a, b = snap(self.t(m['start'])), snap(self.t(m['end']))
            if b - a < 1.0:
                sys.exit(f'moment {k}: too short ({b - a:.2f}s)')
            sub = {x: y for x, y in m.items() if x not in ('skill', 'start', 'end')}
            mp4 = self.work / f'moment{k:02d}.{skill}.mp4'
            sub.update(video=str(self.video), start=a + self.start, end=b + self.start, format=self.fmt,
                       transcript=str(self.transcript), out=str(mp4))
            sp = self.base / f'.{self.out.stem}.moment{k:02d}.{skill}.json'   # next to the spec, so relative image paths still work
            sp.write_text(json.dumps(sub, indent=1))
            key = hashlib.md5((sp.read_text() + str(os.path.getmtime(self.video))).encode()).hexdigest()
            stamp = mp4.with_suffix('.key')
            if not (mp4.exists() and stamp.exists() and stamp.read_text() == key):
                print(f'moment {k}: {skill} at {fmt_time(a)}-{fmt_time(b)}', flush=True)
                r = subprocess.run([sys.executable, str(SKILLS / skill / 'build.py'), str(sp)])
                if r.returncode or not mp4.exists():
                    sys.exit(f'moment {k} ({skill}) failed to render; its spec is {sp}')
                stamp.write_text(key)
            frames = int(json.loads(subprocess.check_output(['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-count_packets',
                                                                '-show_entries', 'stream=nb_read_packets', '-of', 'json', str(mp4)]))['streams'][0]['nb_read_packets'])
            out.append((a, a + frames / FPS, mp4, skill))
        out.sort()
        for (a1, b1, *_), (a2, *_r) in zip(out, out[1:]):
            if a2 < b1:
                sys.exit('moments overlap; give each its own stretch')
        return out

    # -- zoom plan
    def zoom_plan(self):
        """[(t0, t1, scale)] on the local timeline; 1.0 means no zoom"""
        pts = []
        pi = self.s.get('punch_ins')
        if pi:
            every = pi.get('every', 'cut')
            if every == 'cut':
                pts = list(self.cuts)
                if not pts:
                    print('note: punch_ins.every = "cut" but the transcript has no cuts (run tighten first); using sentences')
                    every = 'sentence'
            if every == 'sentence':
                pts = [e + 0.05 for w, _, e in self.words if w.endswith(('.', '?', '!'))]
            elif isinstance(every, (int, float)):
                starts = [t for _, t, _ in self.words]
                pts, t = [], float(every)
                while t < self.total:
                    pts.append(min(starts, key=lambda s: abs(s - t)) if starts else t)
                    t += float(every)
            pts = sorted({snap(p) for p in pts if 0.5 < p < self.total - 0.5})
            min_len = float(pi.get('min_hold', 2.0))
            kept, last = [], 0.0
            for p in pts:
                if p - last >= min_len:
                    kept.append(p)
                    last = p
            scale = float(pi.get('scale', 1.12))
            bounds = [0.0] + kept + [self.total]
            plan = [(a, b, scale if i % 2 else 1.0) for i, (a, b) in enumerate(zip(bounds, bounds[1:]))]
        else:
            plan = [(0.0, self.total, 1.0)]
        for z in self.s.get('zooms') or []:                     # explicit zooms win
            a, b, sc = snap(self.t(z['start'])), snap(self.t(z['end'])), float(z.get('scale', 1.2))
            new = []
            for x, y, s in plan:
                if y <= a or x >= b:
                    new.append((x, y, s))
                    continue
                if x < a:
                    new.append((x, a, s))
                if y > b:
                    new.append((b, y, s))
            new.append((a, b, sc))
            plan = sorted(new)
        return plan

    def zoom_vf(self, scale):
        if scale <= 1.001:
            return ''
        fx, fy = self.s.get('face') or [self.W / 2, self.H * (0.4 if self.fmt == 'horizontal' else 0.36)]
        cw, ch = round(self.W / scale / 2) * 2, round(self.H / scale / 2) * 2
        x = min(self.W - cw, max(0, round(fx - cw / 2)))
        y = min(self.H - ch, max(0, round(fy - ch / 2)))
        return f'crop={cw}:{ch}:{x}:{y},scale={self.W}:{self.H}:flags=lanczos,setsar=1'

    # -- chapters, captions
    def chapters(self):
        out = []
        for c in self.s.get('chapters') or []:
            out.append({'t': snap(self.t(c['at'])), 'title': c['title'], 'duration': c.get('duration', 3.2),
                        'card': c.get('card', self.s.get('chapter_cards', True))})
        return sorted(out, key=lambda c: c['t'])

    def write_srt(self, path):
        cap = self.s.get('captions') or {}
        maxw, maxc = (7, 42) if self.fmt == 'horizontal' else (4, 22)
        gs = groups(self.words, cap.get('srt_words', maxw), maxc)
        lines = []
        for i, g in enumerate(gs):
            a = g[0][1]
            b = gs[i + 1][0][1] if i + 1 < len(gs) else self.total
            b = min(b, a + 6)
            lines.append(f'{i + 1}\n{fmt_time(a, True)} --> {fmt_time(b, True)}\n{" ".join(w for w, _ in g)}\n')
        path.write_text('\n'.join(lines))

    def write_chapters(self, path, chapters):
        rows = [(c['t'], c['title']) for c in chapters]
        if rows and rows[0][0] > 0.5:
            rows.insert(0, (0.0, self.s.get('intro_title', 'Intro')))
        path.write_text(''.join(f'{fmt_time(t)} {title}\n' for t, title in rows))

    def build(self):
        moments = self.render_moments()
        plan = self.zoom_plan()
        chapters = self.chapters()
        cap = self.s.get('captions')
        cap = {'burn': False} if cap is False else (cap or {})
        keys = {bare(k) for k in cap.get('keys', [])}
        size = cap.get('size', 60 if self.fmt == 'horizontal' else 68)
        top, bottom, side = SAFE[self.fmt]
        cy = cap.get('y', bottom - 90 if self.fmt == 'horizontal' else 1380)
        maxw = self.W - 2 * side - 40

        # segment boundaries: moments and zoom changes
        pieces = []
        for a, b, s in plan:
            pieces.append((a, b, s))
        for a, b, mp4, skill in moments:          # carve the moments out of the plan
            new = []
            for x, y, s in pieces:
                if not isinstance(s, (int, float)) or y <= a or x >= b:
                    new.append((x, y, s))
                    continue
                if x < a:
                    new.append((x, a, s))
                if y > b:
                    new.append((b, y, s))
            new.append((a, b, ('moment', mp4)))
            pieces = sorted(new, key=lambda p: p[0])
        pieces = [(snap(a), snap(b), s) for a, b, s in pieces if snap(b) - snap(a) >= 1 / FPS]

        # overlay flipbook (captions off inside moments: the moment carries its own)
        book = Flipbook(self.W, self.H, self.work)
        card_imgs = {}
        tl = build_overlay_timeline(self.words, self.total, self.fmt, cap, [c for c in chapters if c['card']])
        card_x, card_y = (side, top + 20) if self.fmt == 'horizontal' else (side, top + 40)
        num_of = {i + 1: c for i, c in enumerate([c for c in chapters if c['card']])}

        def png(capk, chk):
            parts, key = [], (capk, chk)
            if capk:
                text, said = capk
                parts.append((book.caption(list(text), said, keys, size, cy, maxw), 0, 0, 1.0))
            if chk:
                n, a = chk
                if n not in card_imgs:
                    card_imgs[n] = book.card(n, num_of[n]['title'], self.fmt)
                ease = 1 - (1 - a) ** 3
                parts.append((card_imgs[n], card_x - 30 * (1 - ease), card_y, a))
            return book.state(key, parts) if parts else None

        blank = book.state(('blank',), [])
        print(f'overlay: {len(tl)} states', flush=True)

        def overlay_list(a, b, k):
            rows = []
            for x, y, capk, chk in tl:
                if y <= a or x >= b:
                    continue
                p = png(capk, chk) or blank
                rows.append((p, min(y, b) - max(x, a)))
            if all(p == blank for p, _ in rows):
                return None
            lst = self.work / f'ovl{k:04d}.txt'
            body = ''.join(f"file '{p}'\nduration {d:.4f}\n" for p, d in rows)
            lst.write_text('ffconcat version 1.0\n' + body + f"file '{rows[-1][0]}'\n")
            return lst

        jobs, parts = [], []
        for k, (a, b, s) in enumerate(pieces):
            seg = self.work / f'seg{k:04d}.mkv'
            parts.append(seg)
            src_a = a + self.start
            if isinstance(s, tuple):
                ovl = None
                chs = [c for c in chapters if c['card'] and a <= c['t'] < b]
                if chs:
                    print(f'note: a chapter card at {fmt_time(chs[0]["t"])} falls inside a moment and is skipped')
                jobs.append(lambda s=s, src_a=src_a, a=a, b=b, seg=seg: encode_segment(
                    self.video, src_a, b - a, seg, video_src=s[1], audio=self.audio))
            else:
                ovl = overlay_list(a, b, k)
                jobs.append(lambda s=s, src_a=src_a, a=a, b=b, seg=seg, ovl=ovl: encode_segment(
                    self.video, src_a, b - a, seg, self.W, self.H, self.zoom_vf(s), ovl, audio=self.audio))
        print(f'encoding {len(jobs)} segments ({self.fmt}, {self.W}x{self.H}, {fmt_time(self.total)})', flush=True)
        parallel(jobs)
        loud = self.s.get('loudness')
        concat(parts, self.out, audio=self.audio, loudness=loud)
        srt = self.out.with_suffix('.srt')
        self.write_srt(srt)
        chp = self.out.with_suffix('.chapters.txt')
        if chapters:
            self.write_chapters(chp, chapters)
        sh = self.out.with_name(self.out.stem + '.sheet.jpg')
        sheet(self.out, sh, 12)
        if not self.s.get('keep_work'):
            for p in parts:
                p.unlink(missing_ok=True)
        print(f'\nDONE  {self.out}  ({fmt_time(duration(self.out))})\ncaptions file {srt}' +
              (f'\nchapters      {chp}' if chapters else '') + f'\ncheck         {sh}')
        return self.out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = ap.add_subparsers(dest='cmd', required=True)
    t = sp.add_parser('tighten')
    t.add_argument('video')
    t.add_argument('--max-gap', type=float, default=0.45, help='pauses longer than this are shortened (s)')
    t.add_argument('--pad', type=float, default=0.12, help='silence kept on each side of a join (s)')
    t.add_argument('--cut-fillers', action='store_true', help='also cut um, uh, erm...')
    t.add_argument('--out')
    b = sp.add_parser('build')
    b.add_argument('spec')
    x = ap.parse_args()
    if x.cmd == 'tighten':
        tighten(x.video, x.max_gap, x.pad, x.cut_fillers, x.out)
    else:
        Long(x.spec).build()


if __name__ == '__main__':
    main()
