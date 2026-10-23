"""Lyric duration fit (PRD 5.3, AT-M1-08).

Heuristic from one data point (Thodi: 26 lines over 152 s). An estimate, and the
UI must say so. Never repeats or deletes lines on its own.
"""
from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field

SECONDS_PER_LINE = 5.8
MIN_SECONDS, MAX_SECONDS = 45, 240
SHORT_LINES, LONG_LINES = 8, 40
SKETCH_RANGE = (45, 60)
_TAG_LINE = re.compile(r"^\s*\[[^\[\]]{1,40}\]\s*$")


@dataclass
class LyricFit:
    status: str                      # ok | too_short | too_long
    line_count: int
    suggested_seconds: int
    estimate: bool = True
    options: list[dict] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


def count_lyric_lines(text: str) -> int:
    """Non-blank lines that are not [Section] tag lines."""
    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    return sum(1 for ln in lines if ln.strip() and not _TAG_LINE.match(ln))


def suggested_seconds(lines: int) -> int:
    raw = round(SECONDS_PER_LINE * lines / 4) * 4
    return max(MIN_SECONDS, min(MAX_SECONDS, raw))


def fit_lyrics(text_or_lines: str | int, requested_duration_s: int | None = None) -> LyricFit:
    lines = text_or_lines if isinstance(text_or_lines, int) else count_lyric_lines(text_or_lines)
    secs = suggested_seconds(lines)
    options: list[dict] = []
    warnings: list[str] = []

    if lines < SHORT_LINES:
        status = "too_short"
        sketch = max(SKETCH_RANGE[0], min(SKETCH_RANGE[1], secs))
        options = [
            {"id": "sketch", "label": f"Make a short sketch of about {sketch} seconds", "duration_s": sketch},
            {"id": "repeat", "label": "Repeat some of my lines (you choose which; recorded in the plan)",
             "requires_user_approval": True, "auto": False},
            {"id": "add_lines", "label": "Go back and add more lines"},
        ]
        warnings.append(f"{lines} lyric line(s) is short for a full song; the engine may pad or improvise.")
    elif lines > LONG_LINES:
        status = "too_long"
        capped = lines * SECONDS_PER_LINE > MAX_SECONDS
        options = [
            {"id": "use_cap", "label": f"Use the {MAX_SECONDS} second maximum", "duration_s": MAX_SECONDS},
            {"id": "shorten", "label": "Go back and shorten the lyric"},
        ]
        warnings.append(f"{lines} lines are a lot: at the usual pace they need about "
                        f"{round(SECONDS_PER_LINE * lines)} s, over the {MAX_SECONDS} s cap."
                        if capped else f"{lines} lines is dense; the singing may feel rushed.")
    else:
        status = "ok"

    if requested_duration_s is not None and status == "ok" and abs(requested_duration_s - secs) > 16:
        warnings.append(f"Your length ({requested_duration_s} s) differs from the estimate for "
                        f"{lines} lines (about {secs} s).")
        options.append({"id": "use_estimate", "label": f"Use about {secs} seconds", "duration_s": secs})
    return LyricFit(status=status, line_count=lines, suggested_seconds=secs, options=options, warnings=warnings)
