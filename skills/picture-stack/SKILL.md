---
name: picture-stack
description: A small cluster of photographs floats above the speaker in the original room, then one photograph takes focus. Vertical (9:16) and horizontal (16:9) versions. Use for /picture-stack or to apply this specific treatment to a talking-head clip.
---

# /picture-stack

Apply this treatment to a talking-head clip using the 4.2-second, 30 fps starter: `template.html` is vertical (1080x1920); `template-16x9.html` is horizontal (1920x1080), picked with `"format": "horizontal"` in the spec. The style and images are independent of the speaker’s words; follow the user’s chosen topic.

## Use

Resolve this skill folder from the base directory shown when the skill loads. Its `build.py` resolves the shared kit through that real path, including when installed as a symlink. Run:

```bash
python3 /path/to/skills/picture-stack/build.py /path/to/spec.json
```

No sample speaker is bundled. Supply the user’s footage through the spec’s `assets` (keys `speaker.mp4` / `speaker_cut.webm`, also used for the horizontal template with 1920x1080 files), or drop it into `assets/my-media/` once (see its README) and run with no spec. Output goes to the repository’s `.work/` directory. `--prepare-only` builds an editable composition without rendering. Python 3.9+, ffmpeg/ffprobe and Node.js 22+/npm are required. The first build downloads pinned GSAP 3.15.0 into the ignored vendor cache; rendering uses HyperFrames 0.8.214. No transcript or API key is needed for these short templates. [Spec and custom-footage instructions](../../docs/style-showcase/README.md).

## Adapt the treatment

Keep the original room and speaker continuous. Three photographic cards collect above the head; at 2.05s the first two leave and the third grows into the focus image. Tune `#p0`, `#p1`, `#p2` and `#q1` in the template. Preserve visible headroom and use small, purposeful rotations.

Asset keys: `banana-heels.jpg`, `speaker.mp4`, `pixel-burger.jpg`, `pixel-fruit.jpg`. Full-resolution example images and source credits are in [assets/style-showcase](../../assets/style-showcase/README.md).

This style uses the original room and requires no alpha cutout.

Keep the presenter visible from the first result frame. Use sharp photographs and clean type. Essential text and the face should clear platform overlays; let decorative imagery bleed rather than shrinking the entire composition. The template’s captions and image anchors are starting points, not automatic tracking.

## Review and deliver

The helper validates media dimensions/duration, prepares the composition, runs the renderer check, renders and fully decodes the MP4. Inspect the first frame, the main change and the ending. Check crop anchors, text readability. The default is silent; preserve or add speech, SFX or music only when the user requests them. Longer edits require extending the HTML timeline and source windows; changing only the duration is insufficient.

These are local Claude Code editing workflows. Third-party image rights are documented separately from the code license in the asset directory.

## House style

Inter only, one accent (`#5000fa`), white captions with a soft shadow, rounded cards and flat surfaces. Keep to one accent moment per beat; don’t add extra colours. To try another accent across the whole kit, set `EDIT_ACCENT=#rrggbb`, though these HTML templates carry the hex directly: change it in `template.html` / `template-16x9.html`.
