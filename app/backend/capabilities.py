"""Lookup API for the honesty registry (capabilities.json)."""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

_PATH = Path(__file__).with_name("capabilities.json")
CONTROL_IDS = tuple(f"C{i}" for i in range(1, 26))
USER_FACING_CLASSES = ("b", "d")  # classes whose label must be shown next to the control


@lru_cache(maxsize=1)
def registry() -> dict:
    with open(_PATH, encoding="utf-8") as fh:
        return json.load(fh)


def control_ids() -> list[str]:
    return list(registry()["controls"])


def get_control(control_id: str) -> dict:
    try:
        return registry()["controls"][control_id]
    except KeyError:
        raise KeyError(f"unknown control id {control_id!r}") from None


def control_classes(control_id: str) -> list[str]:
    return list(get_control(control_id)["classes"])


def control_class(control_id: str) -> str:
    """Compact form such as 'a+d' (as in the PRD tables); 'n/a' for non-engine controls."""
    return "+".join(control_classes(control_id))


def ui_wording(control_id: str) -> str:
    return get_control(control_id)["ui_wording"]


def class_info(cls: str) -> dict:
    return registry()["classes"][cls]


def class_labels(control_id: str) -> list[dict]:
    """Labels the UI must show for this control (empty for n/a)."""
    return [dict(class_info(c), cls=c) for c in control_classes(control_id) if class_info(c)["label"]]


def needs_class_label(control_id: str) -> bool:
    return any(c in USER_FACING_CLASSES for c in control_classes(control_id))


def get_capability(key: str) -> dict:
    return registry()["capabilities"][key]


def language_badge(code: str) -> dict:
    """Badge for a C15 vocal language code: hi experimental, en untested, others experimental."""
    opts = registry()["options"]["C15"]
    opt = opts.get(code) or opts["other"]
    return {"code": code, "label": opt["label"], "badge": opt["badge"],
            "ui_wording": get_capability(opt["capability"])["ui_wording"]}


def validate_registry() -> list[str]:
    """Return a list of problems (empty when consistent)."""
    reg, problems = registry(), []
    for cid in CONTROL_IDS:
        c = reg["controls"].get(cid)
        if c is None:
            problems.append(f"missing control {cid}")
            continue
        for key in ("name", "classes", "ui_wording", "maps_to", "visible", "capability"):
            if key not in c:
                problems.append(f"{cid} lacks {key}")
        for cls in c.get("classes", []):
            if cls not in reg["classes"]:
                problems.append(f"{cid} has unknown class {cls}")
        for cap in c.get("capability", []):
            if cap not in reg["capabilities"]:
                problems.append(f"{cid} references unknown capability {cap}")
    extra = set(reg["controls"]) - set(CONTROL_IDS)
    if extra:
        problems.append(f"controls outside C1-C25: {sorted(extra)}")
    return problems
