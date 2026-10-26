"""Known-signal and adversarial tests for the isolated offline editing prototype.

Run with the inventoried analysis Python (unittest; no model imports/downloads).
These fixture sounds are test signals, never demo music or musical acceptance.
"""
import copy
import json
import math
import shutil
import tempfile
import unittest
from pathlib import Path

import numpy as np
from scipy import signal

from app.experiments import remix_lab as lab


class AudioChecks(unittest.TestCase):
    def setUp(self):
        self.sr = 48000
        t = np.arange(self.sr * 2) / self.sr
        self.x = np.column_stack([.1 * np.sin(2 * np.pi * 440 * t)] * 2)

    def test_decode_shape_and_duration(self):
        self.assertEqual(lab.waveform_checks(self.x, len(self.x))["failures"], [])

    def test_silence_rejected(self):
        self.assertIn("silence", lab.waveform_checks(np.zeros_like(self.x))["failures"])

    def test_clipping_rejected(self):
        self.assertIn("sample_clipping", lab.waveform_checks(np.clip(self.x * 20, -1, 1))["failures"])

    def test_truncation_rejected(self):
        self.assertIn("duration", lab.waveform_checks(self.x[:-4800], len(self.x))["failures"])

    def test_nonfinite_rejected(self):
        self.x[0, 0] = np.nan
        self.assertIn("invalid_audio", lab.waveform_checks(self.x)["failures"])

    def test_empty_rejected(self):
        self.assertIn("invalid_audio", lab.waveform_checks(np.zeros((0, 2)))["failures"])

    def test_antiphase_rejected(self):
        self.x[:, 1] *= -1
        self.assertIn("mono_cancellation", lab.waveform_checks(self.x)["failures"])

    def test_retention_survives_fixed_gain(self):
        self.assertTrue(lab.retention(self.x, self.x * .18)["pass"])

    def test_retention_rejects_missing_hook(self):
        self.assertFalse(lab.retention(self.x, np.zeros_like(self.x))["pass"])

    def test_retention_rejects_inverted_source(self):
        self.assertFalse(lab.retention(self.x, -self.x)["pass"])

    def test_retention_rejects_cropped_hook(self):
        self.assertFalse(lab.retention(self.x, self.x[:-1])["pass"])

    def test_retention_rejects_different_tone(self):
        t = np.arange(len(self.x)) / self.sr
        y = np.column_stack([np.sin(2 * np.pi * 550 * t)] * 2)
        self.assertFalse(lab.retention(self.x, y)["pass"])

    def test_retention_accepts_quiet_competing_sound(self):
        rng = np.random.default_rng(4)
        self.assertTrue(lab.retention(self.x, self.x + .01 * rng.standard_normal(self.x.shape))["pass"])

    def test_seam_clean_vs_step(self):
        self.assertFalse(lab.seam_check(self.x, self.sr)["flag"])
        self.x[self.sr:] += .6
        self.assertTrue(lab.seam_check(self.x, self.sr)["flag"])

    def test_split_bands_recombine(self):
        low, high = lab.split_bands(self.x)
        self.assertLess(np.max(np.abs(low + high - self.x)), 1e-15)

    def test_high_band_actually_rejects_low_bass(self):
        t = np.arange(lab.SR * 2) / lab.SR
        x = np.column_stack([.1 * np.sin(2 * np.pi * 70 * t)] * 2)
        _, high = lab.split_bands(x)
        # Exclude filter edge transients; unity recombination alone misses this bug.
        ratio = np.sqrt(np.mean(high[4800:-4800] ** 2) / np.mean(x[4800:-4800] ** 2))
        self.assertLess(20 * math.log10(ratio), -40)

    def test_bass_ownership_vs_competition(self):
        t = np.arange(len(self.x)) / self.sr
        low = np.column_stack([.1 * np.sin(2 * np.pi * 70 * t)] * 2)
        self.assertTrue(lab.bass_conflict(low, low, 0, len(low))["flag"])
        self.assertFalse(lab.bass_conflict(low, low * .01, 0, len(low))["flag"])

    def test_pulses_small_latency_pass(self):
        expected = np.arange(32) * .5
        self.assertTrue(lab.pulse_alignment(expected + .002, expected)["pass"])

    def test_tempo_drift_rejected(self):
        expected = np.arange(32) * .5
        self.assertFalse(lab.pulse_alignment(expected * 1.02, expected)["pass"])

    def test_half_beat_error_rejected(self):
        expected = np.arange(32) * .5
        self.assertFalse(lab.pulse_alignment(expected + .25, expected)["pass"])

    def test_missing_pulses_fail_closed(self):
        self.assertFalse(lab.pulse_alignment([], [0])["pass"])

    def test_pulse_nan_fail_closed(self):
        self.assertFalse(lab.pulse_alignment([np.nan], [0])["pass"])

    def test_drums_are_actual_repeatable_components(self):
        a, events = lab.drum_components(96, .1)
        b, _ = lab.drum_components(96, .1)
        for k in a:
            np.testing.assert_array_equal(a[k], b[k])
        self.assertGreater(np.max(np.abs(a["kick"])), .01)
        self.assertFalse(any(60 <= e["beat"] < 64 for e in events))
        self.assertTrue(any(e["beat"] == 64 and e["bus"] == "kick" for e in events))


class RealToolIntegration(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        t = np.arange(lab.SR * 4) / lab.SR
        x = np.column_stack([.1 * np.sin(2 * np.pi * 440 * t)] * 2)
        lab.write(self.root / "source.wav", x)
        self.x = x
        self.plan = {"schema": lab.SCHEMA, "operation": "single_source_remix", "bpm": 120,
            "meter": 4, "output_beats": 8,
            "sources": {"s": {"path": "source.wav", "sha256": lab.sha(self.root / "source.wav"),
                                "kind": "stereo_mix", "beats_s": np.arange(9).astype(float).tolist()}},
            "clips": [{"id": "one", "source": "s", "source_beats": [0, 4], "at_beat": 0,
                       "gain": [[0, 1], [4, 1]], "low_gain": [[0, 1], [4, 1]], "high_gain": [[0, 1], [4, 1]]}],
            "hooks": [{"id": "test_tone_only", "clip": "one", "local_beats": [.1, 3.9]}]}
        # Four-second source with .5 s pulse intervals, eight intervals.
        self.plan["sources"]["s"]["beats_s"] = (np.arange(9) * .5).tolist()

    def tearDown(self):
        self.tmp.cleanup()

    def test_source_hash_mismatch_rejected(self):
        self.plan["sources"]["s"]["sha256"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "hash"):
            lab.render(self.plan, self.root, self.root / "bad")
        self.assertFalse((self.root / "bad").exists())

    def test_nonmonotonic_grid_rejected(self):
        self.plan["sources"]["s"]["beats_s"][2] = .1
        with self.assertRaisesRegex(ValueError, "beat map"):
            lab.validate_plan(self.plan, self.root)

    def test_source_range_rejected(self):
        self.plan["clips"][0]["source_beats"] = [0, 80]
        with self.assertRaisesRegex(ValueError, "range"):
            lab.validate_plan(self.plan, self.root)

    def test_outside_source_annotation_rejected(self):
        self.plan["sources"]["s"]["beats_s"][-1] = 99
        with self.assertRaisesRegex(ValueError, "outside source"):
            lab.validate_plan(self.plan, self.root)

    def test_clip_past_end_rejected(self):
        self.plan["clips"][0]["at_beat"] = 7
        with self.assertRaisesRegex(ValueError, "timeline"):
            lab.validate_plan(self.plan, self.root)

    def test_bad_automation_rejected(self):
        self.plan["clips"][0]["gain"] = [[0, 1], [0, 0]]
        with self.assertRaisesRegex(ValueError, "automation"):
            lab.validate_plan(self.plan, self.root)

    def test_duplicate_clip_rejected(self):
        self.plan["clips"].append(copy.deepcopy(self.plan["clips"][0]))
        with self.assertRaisesRegex(ValueError, "duplicate"):
            lab.validate_plan(self.plan, self.root)

    def test_unsafe_clip_id_rejected(self):
        self.plan["clips"][0]["id"] = "../source"
        with self.assertRaisesRegex(ValueError, "unsafe clip"):
            lab.validate_plan(self.plan, self.root)

    def test_nan_tempo_rejected(self):
        self.plan["bpm"] = float("nan")
        with self.assertRaisesRegex(ValueError, "bpm"):
            lab.validate_plan(self.plan, self.root)

    def test_unknown_operation_rejected(self):
        self.plan["operation"] = "model_cover"
        with self.assertRaisesRegex(ValueError, "operation"):
            lab.validate_plan(self.plan, self.root)

    def test_hook_outside_clip_rejected(self):
        self.plan["hooks"][0]["local_beats"] = [0, 88]
        with self.assertRaisesRegex(ValueError, "hook range"):
            lab.validate_plan(self.plan, self.root)

    def test_write_never_overwrites(self):
        with self.assertRaises(FileExistsError):
            lab.write(self.root / "source.wav", self.x)

    def test_render_real_edit_and_independent_audit(self):
        original = lab.sha(self.root / "source.wav")
        folder = lab.render(self.plan, self.root, self.root / "render")
        checked = lab.audit(folder)
        self.assertEqual(checked["failures"], [])
        self.assertTrue(checked["hash_matches_render"])
        self.assertFalse(checked["professional_release_ready"])
        self.assertTrue(checked["hook_checks"][0]["pass"])
        self.assertEqual(lab.sha(self.root / "source.wav"), original)
        self.assertIsNone(json.loads((folder / "render.json").read_text())["generative_model"])

    def test_render_never_overwrites(self):
        (self.root / "prior").mkdir()
        with self.assertRaises(FileExistsError):
            lab.render(self.plan, self.root, self.root / "prior")

    def test_changed_native_fails_audit_hash(self):
        folder = lab.render(self.plan, self.root, self.root / "render")
        p = folder / "native_mix.wav"
        x = lab.decode(p)
        p.unlink()
        lab.write(p, x * .9)
        self.assertIn("native_hash_mismatch", lab.audit(folder)["failures"])

    def test_true_peak_and_listening_gain(self):
        stats = lab.listening_copy(self.root / "source.wav", self.root / "listen.wav", target=-20)
        self.assertLess(abs(stats["after"]["input_i"] + 20), .1)
        self.assertLessEqual(stats["after"]["input_tp"], -1.5)

    def test_r3_pitch_independent_of_duration(self):
        y = lab.warp(self.x, np.arange(9) * .5, .45, self.root / "warp", pitch=2)
        self.assertLessEqual(abs(len(y) - round(3.6 * lab.SR)), 1)
        f, power = signal.periodogram(y[lab.SR:3 * lab.SR, 0], fs=lab.SR)
        hz = f[np.argmax(power)]
        cents = 1200 * math.log2(hz / (440 * 2 ** (2 / 12)))
        self.assertLess(abs(cents), 10)

    def test_irregular_onsets_reach_target_grid(self):
        times = np.array([0, .49, 1.03, 1.51, 2.04, 2.48, 3.05, 3.53, 4.])
        x = np.zeros_like(self.x)
        for at in times[1:-1]:
            i = round(at * lab.SR)
            x[i:i + 24] = .6 * np.hanning(24)[:, None]
        y = lab.warp(x, times, .45, self.root / "irregular")
        observed, expected = [], np.arange(1, 8) * .45
        for at in expected:
            lo, hi = round((at - .12) * lab.SR), round((at + .12) * lab.SR)
            observed.append((lo + np.argmax(np.sum(y[lo:hi] ** 2, axis=1))) / lab.SR)
        self.assertTrue(lab.pulse_alignment(observed, expected)["pass"])


if __name__ == "__main__":
    unittest.main()
