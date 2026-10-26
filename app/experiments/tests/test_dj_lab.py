"""Known-signal evidence and real CLI regression checks for DJ operations."""
import copy
import json
from pathlib import Path
import tempfile
import unittest

import numpy as np

from app.experiments import dj_lab as dj,remix_lab as lab


class DspTests(unittest.TestCase):
    def test_echo_is_delayed_filtered_audio_with_no_dry_copy(self):
        x=np.zeros((dj.SR,2));x[2000:2020]=.1
        out=dj.beat_echo(x,.5,repeats=3,feedback=.4)
        delay=round(.5*.75*dj.SR)
        self.assertEqual(len(out),len(x)+3*delay)
        self.assertEqual(float(np.max(np.abs(out[:delay]))),0)
        first=float(np.max(np.abs(out[delay:2*delay])))
        second=float(np.max(np.abs(out[2*delay:3*delay])))
        self.assertAlmostEqual(second/first,.4,places=4)

    def test_echo_rejects_runaway_feedback(self):
        with self.assertRaises(ValueError):dj.beat_echo(np.zeros((dj.SR,2)),.5,feedback=1)

    def test_roll_uses_the_source_and_actual_timed_repetitions(self):
        b=.5;one=np.zeros((round(4*b*dj.SR),2),dtype=np.float32)
        one[1000:2000]=.2
        out,events=dj.roll(one,b)
        self.assertEqual(len(out),round(8*b*dj.SR))
        self.assertEqual(sum(e["loop_beats"] for e in events),8)
        self.assertEqual([e["loop_beats"] for e in events],[4,1,1,.5,.5,.25,.25,.25,.25])
        self.assertEqual(float(out[1000,0]),float(one[1000,0]))
        for beat in (4,5,6,6.5,7,7.25,7.5,7.75):
            self.assertGreater(float(out[round(beat*b*dj.SR)+1500,0]),.15)

    def test_roll_needs_a_complete_loop(self):
        with self.assertRaises(ValueError):dj.roll(np.zeros((100,2)),.5)

    def test_roll_fractional_tempo_has_exact_length(self):
        beat=60/122.882
        out,_=dj.roll(np.ones((round(4*beat*dj.SR),2),dtype=np.float32)*.1,beat)
        self.assertEqual(len(out),round(8*beat*dj.SR))

    def test_edge_ramps_do_not_add_gain_and_reach_zero(self):
        x=np.ones((dj.SR,2))*.2;y=dj.edge_ramp(x)
        self.assertEqual(np.max(y),.2)
        self.assertTrue(np.all(y[0]==0));self.assertTrue(np.all(y[-1]==0))

    def test_bus_outside_timeline_rejected(self):
        with self.assertRaises(ValueError):dj.add_bus(np.zeros((100,2)),np.zeros((30,2)),80)

    def test_tease_handover_has_overlap_repeats_and_monotonic_faders(self):
        beat=60/102
        t=np.arange(round(32*beat*dj.SR))/dj.SR
        source=np.column_stack([.1*np.sin(2*np.pi*440*t)]*2)
        out,a_gain,b_gain,events=dj.tease_blend(source,beat)
        self.assertEqual(len(out),len(source))
        self.assertTrue(np.all(np.diff(a_gain)<=1e-10))
        self.assertTrue(np.all(np.diff(b_gain)>=-1e-10))
        release=round(16*beat*dj.SR)
        self.assertAlmostEqual(b_gain[release],1,places=7)
        self.assertAlmostEqual(a_gain[release],0,places=5)
        self.assertEqual([e['repeat_beats'] for e in events],[2,2,1,1,.5,.5,.5,.5])
        self.assertGreater(np.max(np.abs(out[round(6*beat*dj.SR):round(7*beat*dj.SR)])),.02)
        np.testing.assert_allclose(out[release+dj.SR:],source[release+dj.SR:],atol=1e-5)
        with self.assertRaises(ValueError):dj.tease_blend(source[:100],beat)

    def test_periodicity_survives_a_breakdown(self):
        sr=11025;bpm=125;offset=.12
        x=np.zeros(sr*24,dtype=np.float32)
        tone=np.sin(2*np.pi*70*np.arange(1400)/sr)*np.exp(-np.arange(1400)/200)
        for at in np.arange(offset,23.8,60/bpm):
            if 8<at<12:continue
            i=round(at*sr);x[i:i+len(tone)]+=tone[:len(x)-i]
        candidates=dj.pulse_candidates(x)
        self.assertLess(abs(candidates[0]["bpm"]-bpm),.1)


class RealRendering(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
        t=np.arange(dj.SR*10)/dj.SR
        x=np.column_stack([.1*np.sin(2*np.pi*220*t)]*2)
        lab.write(self.root/"source.wav",x)
        s={"path":str(self.root/"source.wav"),"sha256":lab.sha(self.root/"source.wav"),"bpm":120.,"cue_s":.1,"beats":8,"kind":"stereo_mix"}
        self.plan={"schema":"raag-dj-plan/1","preset":"echo_reveal","target_bpm":120.,"a":s,"b":copy.deepcopy(s)}

    def tearDown(self):self.tmp.cleanup()

    def test_truncated_source_fails_before_any_output(self):
        self.plan["a"]["cue_s"]=9
        with self.assertRaisesRegex(ValueError,"past the source"):dj.render(self.plan,self.root/"out")
        self.assertFalse((self.root/"out").exists())

    def test_changed_hash_fails(self):
        self.plan["b"]["sha256"]="f"*64
        with self.assertRaisesRegex(ValueError,"hash"):dj.validate_plan(self.plan)

    def test_unsupported_technique_fails(self):
        self.plan["preset"]="invent_stems"
        with self.assertRaises(ValueError):dj.validate_plan(self.plan)

    def test_tempo_gap_requires_explicit_reset(self):
        self.plan["target_bpm"]=160
        with self.assertRaisesRegex(ValueError,"15%"):dj.validate_plan(self.plan)
        self.plan["preset"]="echo_reset";dj.validate_plan(self.plan)

    def test_nonfinite_tempo_is_not_accepted(self):
        self.plan["target_bpm"]=float("nan")
        with self.assertRaises(ValueError):dj.validate_plan(self.plan)

    def test_real_tease_render_timing_and_actual_overlapping_buses(self):
        self.plan['preset']='tease_blend'
        for role in ('a','b'):
            self.plan[role]['bpm']=180
            self.plan[role]['beats']=24
        self.plan['target_bpm']=180
        result=dj.render(self.plan,self.root/'tease')
        self.assertAlmostEqual(result['duration_s'],32/3,places=4)
        self.assertAlmostEqual(result['reveal_s'],8,places=4)
        self.assertAlmostEqual(result['overlap_start_s'],8/3,places=4)
        a=lab.decode(self.root/'tease/bus_a.wav');b=lab.decode(self.root/'tease/bus_b.wav')
        middle=round(4*dj.SR)
        self.assertGreater(np.max(np.abs(a[middle:middle+1000])),.001)
        self.assertGreater(np.max(np.abs(b[middle:middle+1000])),.001)
        self.assertTrue((self.root/'tease/incoming_repeat_schedule.json').is_file())
        self.plan['a']['beats']=8
        with self.assertRaisesRegex(ValueError,'24 beats'):dj.validate_plan(self.plan)

    def test_real_render_preserves_source_and_exports_level_matched_arms(self):
        before=lab.sha(self.root/"source.wav")
        result=dj.render(self.plan,self.root/"take")
        self.assertEqual(before,lab.sha(self.root/"source.wav"))
        self.assertAlmostEqual(result["duration_s"],8,places=3)
        self.assertEqual(result["reveal_s"],4)
        for arm in ("master","control"):
            self.assertEqual(result["checks"][arm]["failures"],[])
            self.assertLessEqual(result["levels"][arm]["mp3"]["input_tp"],-1)
        levels=result["levels"]
        self.assertLess(abs(levels["master"]["mp3"]["input_i"]-levels["control"]["mp3"]["input_i"]),.2)
        self.assertEqual(result["models"],[])
        self.assertGreater(np.max(np.abs(lab.decode(self.root/"take/bus_fx.wav"))),.001)
        with self.assertRaises(FileExistsError):dj.render(self.plan,self.root/"take")


if __name__=="__main__":unittest.main()
