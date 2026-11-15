# Your media

Drop your own footage here and the five photographic templates use it by default (no spec override needed):

| File | What |
|---|---|
| `speaker.mp4` | your vertical talking head, 1080x1920, 30 fps, at least 4.3 s |
| `speaker_cut.webm` | its alpha cutout: `kit/.venv/bin/python kit/cutout.py speaker.mp4 speaker_cut.webm` |
| `speaker-16x9.mp4` | your horizontal talking head, 1920x1080, 30 fps, at least 4.3 s |
| `speaker-16x9_cut.webm` | its alpha cutout |

These files are ignored by git, so your footage never ends up in the public repo.
