#!/usr/bin/env python3
"""long-form: a whole talking-head video (horizontal or vertical) edited end to end.

    <kit>/.venv/bin/python build.py spec.json          see SKILL.md; the engine is kit/longform.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'kit'))
from longform import Long  # noqa: E402

if __name__ == '__main__':
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    Long(sys.argv[1]).build()
