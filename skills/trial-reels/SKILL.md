---
name: trial-reels
description: Turns one talking-head clip into 3 visually distinct versions to post as trial reels (or to A/B a long-form intro), so you can see which look wins. Version 1 has a big white title with key lines on an accent block and karaoke captions, version 2 a white post-card header with punch-in zooms and bold captions, and version 3 a dark dot-grid backdrop with one big stat and the clip in an accent frame. Works on vertical (9:16) and horizontal (16:9) clips. Use when the user runs /trial-reels or asks for trial versions, variations or A/B looks of a clip.
---

# /trial-reels

```
 1 TITLE + KARAOKE      2 POST HEADER           3 STAT FRAME
┌──────────────┐      ┌──────────────┐       ┌──────────────┐
│ CAROUSELS ARE│      │(o) Name      │       │      2×      │
│  INSTAGRAM   │      │ The hook as a│       │ the views of │
│  CHEAT CODE  │      │ headline     │       │ ┌──────────┐ │
│    (face)    │      │  (face, zooms│       │ │● REC face│ │
│ dim→white    │      │  cheat code  │       │ │ captions │ │
└──────────────┘      └──────────────┘       └──────────────┘
```

## First use
This skill's folder is the "Base directory" Claude Code shows when it loads it.
```bash
SKILL_DIR="<base directory of this skill>"   # the path Claude Code printed as "Base directory for this skill"
KIT=$(python3 -c 'import os,sys;print(os.path.realpath(os.path.join(sys.argv[1],"..","..","kit")))' "$SKILL_DIR")
PY="$KIT/.venv/bin/python"; [ -x "$PY" ] || bash "$KIT/setup.sh"
```
`GROQ_API_KEY` must be set to transcribe. Needs ffmpeg and Node.

## Format
Every spec takes `"format"`: `"vertical"` (1080x1920: reels, shorts, vertical long-form), `"horizontal"` (1920x1080: YouTube and other long-form) or `"auto"` (default: follows the source's shape). Run `"$PY" "$KIT/reel.py" probe <video>` to see what auto picks. The sheet tints red what the platform covers: the Instagram/TikTok UI on vertical, the YouTube player chrome on horizontal. For a full-length video, use this skill as a **moment** inside `/long-form` instead of cutting the clip by hand.

## Steps
1. **Clip.** The user's finished reel or its hook. Whole clips work. The hook (first 5 to 10 s) is the usual test.
2. **Words.** Run `"$PY" "$KIT/reel.py" words <video>` and read the hook. Each sentence ends with `[ends …]`: use the last one you keep as `end`.
3. **Write three different packagings of the same idea.** Each version is a different promise, not just a different font:
   - **v1 title**: the claim, 3 lines, with the 1 or 2 key lines bigger (`*line*`).
   - **v2 headline**: the hook rewritten as a post headline ("The Instagram cheat code not many people know about"), plus the speaker's avatar and name. `keys` are the caption words to turn yellow (the punch-ins land on them).
   - **v3 stat**: the single number or comparison in the clip ("2×", "10K", "$0") plus a 3 to 5 word line.
4. **Spec.** Write `<clip>.trial-reels.json` (below). Paths in a spec are relative to the spec file.
5. **Build.** Run `"$PY" "$SKILL_DIR/build.py" <spec.json>`. It writes `<out>-1.mp4`, `<out>-2.mp4` and `<out>-3.mp4`, each with a sheet.
6. **Check.** Look at all three sheets:
   - The titles clear the red zones (top 220 px on vertical, top 80 px on horizontal).
   - The captions sit under the face, not on it.
   - The three versions look clearly different at a glance.
7. **Hand over** the three paths with one line each on what the version tests.

## Spec
```json
{
  "video": "my-reel.mp4", "start": 0, "end": 6.95,
  "v1": {"title": ["carousels are an", "*instagram*", "*cheat code*"]},
  "v2": {"avatar": "me.jpg", "name": "Your Name", "sub": "Instagram growth",
         "headline": "The Instagram cheat code not many people know about",
         "keys": ["cheat", "code", "twice", "views"], "punches": ["cheat", "twice"]},
  "v3": {"stat": "2×", "line": "the views of reels", "pulse_at": "twice"}
}
```
Optional fields:
- **`caption_top`** per version: vertical 1400 / 1260 / 1330 for v1 / v2 / v3; horizontal 850 / 820, and v3 sits inside the frame.
- **`avatar`** is optional: without it the card shows an accent dot.
- **`punches`**: defaults to the key words, at least 1.5 s apart.

## Taste
- Same clip, same words, three different first impressions. Change the promise, not just the paint.
- No invented numbers. The v3 stat must be something said in the clip.
- Post all three as trial reels on the same day and keep the one with the best 3-second hold.
