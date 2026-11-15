---
name: long-form
description: Edits a whole talking-head video (minutes to an hour, horizontal 16:9 for YouTube or vertical 9:16) end to end. Shortens pauses and optionally cuts um/uh, hides the jump cuts with alternating punch-in zooms, burns in clean captions with key words on an accent pill, adds chapter cards, and splices in designed "moments" made by the other skills (explainer, split-screen, behind-the-person, ranking-list, storytelling) at exactly the right frames. Also writes an .srt and a YouTube chapter list. Use when the user runs /long-form or asks to edit a full video, a podcast-style talking head, a YouTube video, a course lesson or any clip longer than about a minute.
---

# /long-form

```
 source ──tighten──▶ tight take ──build──▶ edited.mp4  + .srt + .chapters.txt + .sheet.jpg
                     (pauses cut,          ├ plain stretches: punch-ins on the cuts, captions, chapter cards
                      words remapped)      └ moments: explainer / split-screen / ... rendered and spliced in
```

## First use
This skill's folder is the "Base directory" Claude Code shows when it loads it.
```bash
SKILL_DIR="<base directory of this skill>"   # the path Claude Code printed as "Base directory for this skill"
KIT=$(python3 -c 'import os,sys;print(os.path.realpath(os.path.join(sys.argv[1],"..","..","kit")))' "$SKILL_DIR")
PY="$KIT/.venv/bin/python"; [ -x "$PY" ] || bash "$KIT/setup.sh" --cutout
```
`GROQ_API_KEY` must be set to transcribe (long videos go up in 10-minute chunks). Needs ffmpeg and Node.

## Steps
1. **Probe.** `"$PY" "$KIT/reel.py" probe <video>`: size, length, and the format `auto` will pick (wider than tall = horizontal 1920x1080, otherwise vertical 1080x1920). Ask only if the user wants the other shape (a horizontal source can be cut to vertical, which crops the centre).
2. **Tighten** (recommended for raw recordings, skip for already-edited footage):
   `"$PY" "$KIT/longform.py" tighten <video> [--max-gap 0.45] [--pad 0.12] [--cut-fillers]`
   It transcribes, keeps every word, shortens each pause longer than `--max-gap` to about `2 × --pad`, and writes `<video>.tight.mp4` plus `<video>.tight.transcript.json` (words on the new timeline, and `cuts`: where each join landed). Use the tight file from here on. `--cut-fillers` also removes um/uh/erm.
3. **Read it.** `"$PY" "$KIT/reel.py" words <video>` prints one sentence per line with times (on the tight timeline if you tightened). For long videos read it in parts with `--start/--end`. Note:
   - the **chapters**: where the topic turns (4 to 10 for a 10 to 20 minute video), each with a 2 to 5 word title;
   - 2 to 6 **moments**: 4 to 10 second stretches that make one concrete, visual point (a comparison, a step, a number, a ranking, a small story). Space them out; most of the video stays the plain take.
4. **Framing.** `"$PY" "$KIT/reel.py" frame <video> <t> frame.jpg` and look: note the face centre (for `face`, used by the punch-ins) and the eye line and face x for any moment that needs them (`eye_y`, `face_x`, `video_top`...).
5. **Spec.** Write `<video>.long-form.json` next to the video (below). Paths are relative to the spec file.
6. **Build.** `"$PY" "$SKILL_DIR/build.py" <spec.json>`. Moments render first (about 20 to 40 s each, cached), then the timeline is encoded in segments in parallel. A 15 minute 1080p video takes roughly as long as one or two ffmpeg passes over it.
7. **Check** `<out>.sheet.jpg` (12 frames, red = covered by the player or the reel UI), then spot-check each moment's join and one chapter card in the video itself. Fix the spec and rebuild; moments that didn't change are reused.
8. **Hand over** the mp4, the `.srt` (upload it to YouTube for searchable captions, even if they are burned in), and the `.chapters.txt` (paste into the description).

## Spec
```json
{
  "video": "episode.tight.mp4",
  "format": "auto",
  "out": "episode.edited.mp4",
  "face": [880, 400],
  "punch_ins": {"every": "cut", "scale": 1.12, "min_hold": 2.5},
  "zooms": [{"start": 312.4, "end": 318.0, "scale": 1.25}],
  "captions": {"keys": ["carousel", "viral"], "karaoke": false},
  "chapters": [
    {"at": 0, "title": "Why carousels win"},
    {"at": "the second thing", "title": "Finding a viral post"}
  ],
  "moments": [
    {"skill": "explainer", "start": 61.2, "end": 67.0,
     "title": "Steal what *works*", "eye_y": 400, "face_x": 880,
     "visual": {"type": "list", "items": [{"text": "Find a *viral* post", "at": "find"}, {"text": "Recreate it", "at": "recreate"}]}},
    {"skill": "split-screen", "start": 140.0, "end": 147.5, "face_x": 880, "zoom": 1.2,
     "badge": "Step 2", "headline": "Pick *one*", "visual": {"type": "image", "src": "screens/app.png"}}
  ],
  "loudness": -14
}
```
- **`video`**: the tight file, or the raw one. `start`/`end` (optional) use only part of it.
- **`format`**: `auto`, `horizontal` or `vertical`.
- **`face`**: `[x, y]` of the face on the canvas, the centre of every zoom. Default: centre, a little above middle.
- **`punch_ins`**: alternate between the plain shot and `scale` (1.08 to 1.18) at every `"cut"` (needs a tightened transcript; it hides the jump cuts), every `"sentence"`, or every N seconds (a number). `min_hold` (s) keeps zooms from flickering. Leave it out for no punch-ins.
- **`zooms`**: explicit holds at a scale, on top of the punch-ins. Use sparingly, for an emphatic line.
- **`captions`**: burned-in house captions: Inter ExtraBold, white with a soft shadow, `keys` on an accent pill. `karaoke: true` dims words until they are said. `y` and `size` move and resize them. `false` turns burned captions off (the `.srt` is still written). Inside moments the moment's own captions take over.
- **`chapters`**: `at` is seconds or a spoken word (`"pricing"`, `"pricing#2"`, `"pricing-0.5"`). Each gets a card (an accent number tile and the title) for about 3 s; `"card": false` on one, or `"chapter_cards": false` for all, keeps only the `.chapters.txt` entry. A first chapter that isn't at 0 gets an "Intro" line (`intro_title`).
- **`moments`**: `skill` + `start`/`end` (seconds, or words) + that skill's own fields, exactly as its SKILL.md describes (read it before writing one). Format, video and transcript are filled in for you. Moments cannot overlap. A cutout skill (explainer, behind-the-person) adds about 0.1 s per frame.
- **`loudness`**: normalise the final mix to this LUFS (-14 suits YouTube). Leave it out to keep the voice as recorded.
- **`keep_work`**: true keeps the encoded segments in `.work/`.

## Taste
- The take is the show. Captions and punch-ins carry the whole video; moments are seasoning (one every 1 to 3 minutes at most).
- Every moment illustrates the exact sentence under it, landing on the words that name it, and uses the user's real images, screens and numbers. Never invent results.
- Chapter titles are short and concrete ("Pricing", "The 3-step setup"), never clickbait.
- Horizontal: keep captions and cards inside the safe area (the sheet shows it); YouTube's progress bar covers the bottom 120 px when paused.
- Vertical long-form uses the same zones as reels; keep captions around y 1380.
