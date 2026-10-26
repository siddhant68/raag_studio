import test from 'node:test';
import assert from 'node:assert/strict';
import {timing,validateSelection,USE_CASES,timeLabel} from './dj_logic.mjs';
const p={preset:'echo_reveal',a_bpm:120,b_bpm:100,target_bpm:110,a_cue_s:0,b_cue_s:0,a_beats:32,b_beats:32};
const a={status:'ready',duration_s:90};
test('fixed-tempo preview and eight-beat overlap timing',()=>{
 assert.equal(timing(p).duration,64*60/110);
 assert.ok(Math.abs(timing({...p,preset:'bass_swap'}).reveal-24*60/110)<1e-10);
});
test('tempo portal keeps both original tempos',()=>{
 const t=timing({...p,preset:'echo_reset'});
 assert.equal(t.reveal,16);assert.equal(t.duration,35.2);
});
test('short source cannot silently pad its selected phrase',()=>{
 assert.match(validateSelection(p,a,{...a,duration_s:10}),/past the end/);
});
test('large tempo gaps propose a reset instead of extreme stretching',()=>{
 assert.match(validateSelection({...p,target_bpm:160},a,a),/Tempo portal/);
 assert.equal(validateSelection({...p,target_bpm:160,preset:'echo_reset'},a,a),null);
});
test('source cues and tempos must be finite',()=>{
 assert.match(validateSelection({...p,a_cue_s:NaN},a,a),/valid start/);
 assert.match(validateSelection({...p,b_bpm:Infinity},a,a),/tempo/);
});
test('use cases have short reels and distinct techniques',()=>{
 assert.equal(USE_CASES.reel.aBeats,16);assert.equal(USE_CASES.genre.preset,'echo_reset');
});
test('time labels remain readable',()=>{assert.equal(timeLabel(78.6),'1:18');assert.equal(timeLabel(NaN),'—');});

test('tease blends overlap for sixteen beats and release at the outgoing end',()=>{
 const plan={...p,preset:'tease_blend'};
 const t=timing(plan);
 assert.equal(t.reveal,32*60/110);
 assert.equal(t.overlapStart,16*60/110);
 assert.ok(Math.abs(t.duration-48*60/110)<1e-10);
 assert.match(validateSelection({...plan,b_beats:16},a,a),/24 beats/);
 assert.equal(USE_CASES.club.preset,'tease_blend');
});
