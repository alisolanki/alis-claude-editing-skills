---
name: split-screen
description: Edits a talking-head clip into the classic half-and-half. Visuals and animation fill one half (a step badge, a bold headline and a window showing the point), the speaker fills the other, and a dark caption pill sits on the seam. Vertical stacks visuals over speaker; horizontal puts visuals left and speaker right. Use when the user runs /split-screen or asks for a split screen, "visuals on top, me on the bottom", "screen on the left, me on the right" or a tutorial-step video.
---

# /split-screen

```
┌──────────────────────┐
│       [Step 1]       │
│ Find a viral carousel│  bold headline, one word in the accent
│ ┌──────────────────┐ │
│ │ window: grid with │ │  grid-pick | image | checklist
│ │ a cursor pick     │ │
├─[ THEN I PICK ONE ]──┤  caption pill on the seam (y 918)
│                      │
│   speaker, bottom    │  the clip, moved so the face sits here
└──────────────────────┘
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
1. **Clip.** Any talking head, vertical or horizontal.
2. **Words.** Run `"$PY" "$KIT/reel.py" words <video>`. It prints one sentence per line with `[ends …]` (when its last word ends), so use that as `end`. Pick a 4 to 8 second stretch of whole sentences that walks through ONE step ("I use this tool… then I pick one… then I hit this button").
3. **Face.** Run `"$PY" "$KIT/reel.py" frame <video> <t> frame.jpg` and read the y of the eyes (call it E).
   - The bottom half shows the clip from y `-video_top` to `-video_top + 960`.
   - Set `video_top` so the eyes land about 300 px into the bottom half: `video_top = 300 - E` (eyes at 730 gives -430; a close-up with eyes at 935 gives -635).
   - The chin must stay above y 1500, where Instagram's caption UI starts.
   - Horizontal: the speaker fills the right half. Read the x of the face centre as `face_x` (it is centred in that half) and use `zoom` (1.0 to 1.4) to fill it with a closer shot. `video_top` moves the take up or down.
4. **Spec.** Write `<clip>.split-screen.json` (below). Paths in a spec are relative to the spec file. Times are seconds from `start`, or spoken words.
5. **Build.** Run `"$PY" "$SKILL_DIR/build.py" <spec.json>`.
6. **Check.** Look at `<out>.sheet.jpg`:
   - The headline is clear of the top 220 px.
   - The caption pill fits on one line.
   - The face is whole in the bottom half.
   - Each action lands on its word.
7. **Hand over** the mp4 path.

## Spec
```json
{
  "video": "my-clip.mp4", "start": 32.0, "end": 37.2,
  "badge": "Step 1",
  "headline": "Find a *viral* carousel",
  "video_top": -430,
  "visual": {
    "type": "grid-pick", "search": "viral carousels · sorted by outlier score",
    "images": "library/*.jpg", "chips": ["12.4×", "8.7×", "15.1×"], "chips_at": "viral",
    "pick": 5, "pick_at": "one",
    "button": "Get slides + prompt", "button_at": "then#2", "click_at": "button",
    "fan": ["slide-2.jpg", "slide-3.jpg", "slide-4.jpg"]
  }
}
```
The visual takes one of three `type`s:
- **`grid-pick`**: a browser window with a 4-column grid of 8 to 16 images and optional accent `chips`. It scrolls, a cursor clicks cell `pick` at `pick_at`, the rest dim, a `button` pops, and the `fan` slides fly out.
- **`image`**: `{"type": "image", "src": "screenshot.png", "bar": "app.com", "scroll": 120}`, a screenshot in the window that pans.
- **`checklist`**: `{"type": "checklist", "bar": "the plan", "items": [{"text": "Find a *viral* post", "at": "find"}, ...]}`. Up to 4 rows, each ticking in the accent as it is said.

The other fields:
- **Captions** come from the transcript: up to 4 words, each brightening as it is said; words in `keys` brighten to the accent. Move them with `caption_top`: 918 vertical (on the seam), 870 horizontal (across the bottom of the seam).

## Taste
- The top half shows what the words say, at the moment they say it. The cursor clicks on "pick", and the button presses on "button".
- One step per clip, and the badge numbers it ("Step 1", "Step 2"…). Make one reel per step for a series.
- Use the user's real screens and images. Chips and numbers come from the user, never made up.
