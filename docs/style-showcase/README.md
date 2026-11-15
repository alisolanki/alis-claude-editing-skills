# Five photographic editing styles

Shape Shift, Picture Stack, Scene Switch, Visual Notes and Orbit Reel. Each is a runnable 4.2-second template in two shapes: `template.html` (vertical, 1080x1920) and `template-16x9.html` (horizontal, 1920x1080), with sharp source images included. No speaker footage is bundled: they run on yours.

## Your footage

Once, put your clips in `assets/my-media/` (ignored by git):

```bash
cp ~/my-vertical-clip.mp4   assets/my-media/speaker.mp4          # 1080x1920, 30 fps, 4.3 s or longer
cp ~/my-horizontal-clip.mp4 assets/my-media/speaker-16x9.mp4     # 1920x1080, 30 fps
bash kit/setup.sh --cutout
kit/.venv/bin/python kit/cutout.py assets/my-media/speaker.mp4      assets/my-media/speaker_cut.webm
kit/.venv/bin/python kit/cutout.py assets/my-media/speaker-16x9.mp4 assets/my-media/speaker-16x9_cut.webm
```

Crop deliberately first (`ffmpeg -vf "crop=...,scale=1080:1920"`): the templates can't track a face or repair an off-centre source. Generate the cutout from the exact same file, so size, frame rate and duration match. Review hair, hands and depth occlusion.

## Build

From the repository root:

```bash
python3 skills/orbit-reel/build.py                                   # vertical, using assets/my-media
python3 skills/orbit-reel/build.py my-spec.json                      # with a spec (below)
python3 skills/orbit-reel/build.py my-spec.json --prepare-only       # editable composition only
```

Output is `.work/orbit-reel.mp4`, with editable HTML in `.work/orbit-reel.composition/`. Needs Python 3.9+, ffmpeg/ffprobe and Node.js 22+/npm; no Groq key or transcript. On first use it fetches GSAP 3.15.0 into `kit/vendor/`; HyperFrames 0.8.214 is fetched by npx. To reuse an installed renderer, set `HYPERFRAMES_CLI` to its CLI JavaScript file.

Example spec, saved next to your media:

```json
{
  "out": "my-orbit.mp4",
  "format": "horizontal",
  "media_start": 0.04,
  "assets": {
    "speaker.mp4": "my-landscape.mp4",
    "speaker_cut.webm": "my-landscape-cutout.webm",
    "banana-heels.jpg": "my-first-image.jpg",
    "blue-stairs.jpg": "my-second-image.jpg"
  },
  "text": {"Put your ideas": "Show your work"}
}
```

- `format`: `vertical` (default) or `horizontal`. The asset keys are the same for both; horizontal media must be 1920x1080.
- Unspecified images use the bundled samples. Inspect every crop after replacing one.
- `text` performs literal HTML substitutions (values are escaped). Text that GSAP changes mid-clip is edited in the template itself.
- Shape Shift, Scene Switch and Visual Notes need a cutout. Orbit Reel needs the video and its matching cutout, replaced together. Picture Stack uses only the video.

## Scope

These are silent 4.2-second style starters, not the transcription-driven workflows. Longer clips, new image anchors, captions and audio need an intentional timeline edit in the HTML; changing only the duration is not enough.
