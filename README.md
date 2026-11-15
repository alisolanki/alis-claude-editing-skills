# Ali's Claude editing skills

Twelve video editing skills for Claude Code by **Ali Solanki**. Point Claude at a talking-head recording and it edits it around your words: short-form reels and shorts, or a full long-form video, in **vertical 9:16 or horizontal 16:9**. Everything renders on your own computer, in one minimal house style.

**House style:** Inter only, one accent colour (`#5000fa`), white captions with a soft shadow, key words on an accent pill, rounded cards, flat surfaces, quiet motion.

## The skills

**Long-form**

| Skill | What it does |
|---|---|
| `/long-form` | **Edits a whole video** (minutes to an hour). Shortens pauses (and optionally cuts um/uh), hides the jump cuts with alternating punch-ins, burns in captions, adds chapter cards, and splices in designed *moments* made by the workflows below. Also writes an `.srt` and a YouTube chapter list. |

**Talking-head workflows** (each works on vertical and horizontal clips, alone or as a long-form moment)

| Skill | What it makes |
|---|---|
| `/trial-reels` | **The same clip as 3 distinct versions** to A/B: a big title with karaoke captions, a post-card header with punch-in zooms, and a big stat with the clip in an accent frame. |
| `/behind-the-person` | **Graphics behind you.** You are cut out and stand in front of a panel (a post grid, a bar chart or a screenshot). Big words land on your chest and a profile card counts up. |
| `/explainer` | **You in a panel, visuals beside you.** Your head breaks out over the panel's edge while a before-to-after comparison (or a list) explains the point. |
| `/split-screen` | **The classic half-and-half.** A step badge, a headline and a window showing the step in one half, you in the other, captions on the seam. |
| `/ranking-list` | **A tier list.** Each item pops up when you name it and drops into its tier (S to F) on the verdict. |
| `/storytelling` | **Three image cards, a title and a subtitle**, all landing together over one continuous take. |

**Photographic styles** (4.2-second templates, vertical and horizontal)

| Skill | What it makes |
|---|---|
| [`/shape-shift`](skills/shape-shift/SKILL.md) | Circular photographic match cuts beside the speaker. |
| [`/picture-stack`](skills/picture-stack/SKILL.md) | Three image cards, then one expands into focus. |
| [`/scene-switch`](skills/scene-switch/SKILL.md) | Photographic backgrounds change behind a continuous speaker cutout. |
| [`/visual-notes`](skills/visual-notes/SKILL.md) | A complete image becomes a close-up of one meaningful detail. |
| [`/orbit-reel`](skills/orbit-reel/SKILL.md) | Image cards orbit in 3D, passing behind and in front of the speaker. |

[Build and customise the photographic styles](docs/style-showcase/README.md) · [Image credits](assets/style-showcase/README.md)

## Install

You need macOS or Linux with **ffmpeg**, **Node.js 22+** and **Python 3.9+**, plus a free **[Groq API key](https://console.groq.com/keys)** for transcripts. The photographic templates don't need the key.

```bash
brew install ffmpeg node        # if you don't have them
export GROQ_API_KEY=gsk_...     # add it to ~/.zshrc so it sticks
git clone https://github.com/alisolanki/alis-claude-editing-skills.git ~/alis-claude-editing-skills
cd ~/alis-claude-editing-skills && ./install.sh --cutout
```

`install.sh` links every skill into `~/.claude/skills/` (so they show up as `/long-form`, `/explainer` and so on) and runs the one-time setup: a Python environment in `kit/.venv`, GSAP, caption fonts, a HyperFrames warm-up and (with `--cutout`) the matting model. To update later: `git pull && ./install.sh`.

It's also packaged as a Claude Code plugin. Inside Claude Code:
```
/plugin marketplace add alisolanki/alis-claude-editing-skills
/plugin install editing-skills@alis-claude-editing-skills
```
Plugin skills are namespaced (`/editing-skills:explainer`). The git clone above is the route tested end to end.

## Use

Open Claude Code anywhere and point it at a clip:

```
/long-form ~/Videos/episode-12.mp4 tighten it, chapters, two explainer moments
/explainer ~/Downloads/my-clip.mp4
/trial-reels ~/Downloads/my-reel.mp4 use the hook
/split-screen ~/Downloads/landscape-tutorial.mp4 format horizontal
/behind-the-person ~/Downloads/clip.mp4, my posts are in ~/Desktop/posts
```

The workflows follow the same steps:
1. Transcribe the clip with word timings (Groq Whisper).
2. Pick a stretch (or, for long-form, the chapters and moments) and look at a frame to find your eyes, chin and face centre.
3. Write a small JSON spec next to your clip. Every visual is anchored to a spoken word, so it lands when you say it.
4. Render with [HyperFrames](https://github.com/heygen-com/hyperframes) (HTML and GSAP to MP4, 30 fps, your voice kept). Long-form encodes the plain stretches directly with ffmpeg, so an hour-long video stays fast.
5. Check a contact sheet with the platform's safe zones tinted red (Instagram/TikTok UI on vertical, the YouTube player on horizontal), and fix what's off.

You get `my-clip.explainer.mp4` (and its `.sheet.jpg`) next to the clip. A short workflow renders in about 15 to 40 seconds; the cutout skills add about 0.1 s per frame.

Bring your own images (posts, screenshots, analytics) for the visuals that need them. Every skill also has visuals that need none.

## Vertical or horizontal

Every spec takes `"format"`: `"vertical"` (1080x1920), `"horizontal"` (1920x1080) or `"auto"` (the default, follows the source). Each workflow has its own horizontal layout rather than a letterboxed vertical one:

| Skill | Vertical | Horizontal |
|---|---|---|
| explainer | panel at the bottom, visuals on top | panel on the right (or left), visuals beside it |
| split-screen | visuals over speaker | visuals left, speaker right |
| behind-the-person | tall panel behind the head | wide panel behind the head, card bottom-left |
| ranking-list | table on the chest | table beside the speaker |
| storytelling | cards across the top | cards on one side, face shifted to the other |
| trial-reels | title / header / stat over the clip | the same three, laid out for 16:9 |

`python kit/reel.py probe <video>` shows what `auto` picks.

## Re-theming

All colours come from [`kit/theme.py`](kit/theme.py). Change `ACCENT` there, or try one without editing anything:

```bash
EDIT_ACCENT='#ff3b30' kit/.venv/bin/python skills/explainer/build.py my-clip.explainer.json
```

The photographic templates carry the accent hex directly in their HTML.

## How it's built

```
skills/<name>/SKILL.md     what Claude follows: steps, the spec, taste rules
skills/<name>/build.py     spec.json -> HyperFrames composition -> mp4
kit/reel.py                shared: formats, clip prep, word anchors, captions, render, safe-zone checks
kit/longform.py            long-form: tighten, segments, punch-ins, caption/chapter flipbook, moments, srt, chapters
kit/theme.py               the house style: accent, neutrals, radii, shadows
kit/transcribe.py          Groq Whisper with word timestamps
kit/cutout.py              speaker cutout (RobustVideoMatting, ONNX on the CPU) -> VP9 alpha webm
kit/style_template.py      builds the photographic templates (vertical and 16:9)
kit/fonts.py               TTF copies of the bundled fonts for the long-form captions
kit/setup.sh               one-time setup
```

To add a skill, copy a folder in `skills/` and change its `build.py`. The workflows use `Job(spec) -> Comp -> finish()`; `job.horizontal` and `job.pick(vertical, horizontal)` give each layout its two shapes. Then run `./install.sh` again.

## Credits

- [HyperFrames](https://github.com/heygen-com/hyperframes) by HeyGen renders the compositions.
- [GSAP](https://gsap.com) drives the animation. It is fetched at setup, not included here.
- [RobustVideoMatting](https://github.com/PeterL1n/RobustVideoMatting) by Shanchuan Lin et al. (GPL-3.0) does the cutout. The model is downloaded at setup, not included here.
- Transcription is Whisper on [Groq](https://groq.com).
- The fonts are Inter, Archivo Black, DM Serif Display, Instrument Serif, Pixelify Sans and TikTok Sans, all under the SIL Open Font License.

Made by Ali Solanki. Code and authored instructions are MIT licensed (see [LICENSE](LICENSE)); [image rights are separate](assets/style-showcase/README.md#rights).
