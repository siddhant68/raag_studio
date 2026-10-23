"""Runs the DOM-free JS logic tests (app/tests/js/logic.test.mjs) with `node --test`. No npm, no network."""
import shutil
import subprocess
from pathlib import Path

import pytest

JS_DIR = Path(__file__).resolve().parent / "js"
NODE = shutil.which("node")


@pytest.mark.skipif(NODE is None, reason="node is not installed")
def test_ui_logic_unit_tests_pass_under_node():
    done = subprocess.run([NODE, "--test", str(JS_DIR / "logic.test.mjs")], capture_output=True, text=True, timeout=120)
    assert done.returncode == 0, done.stdout[-3000:] + done.stderr[-2000:]
    assert "# fail 0" in done.stdout or "ℹ fail 0" in done.stdout
