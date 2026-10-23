# Thodi Der Aur: a new, fixed 16-bar arrangement, performed by Sonic Pi.
# 76 BPM, D major. Original melodic fills; no song recordings are sampled.
use_bpm 76
use_random_seed 231026
use_debug false
voicings = [
  [:d4,:fs4,:a4,:e5],[:d4,:fs4,:a4,:e5],
  [:d4,:fs4,:a4,:e5],[:b3,:d4,:fs4,:cs5],
  [:g3,:b3,:d4,:a4],[:a3,:d4,:e4,:a4],
  [:a3,:d4,:fs4,:a4],[:b3,:d4,:fs4,:a4],
  [:g3,:b3,:d4,:a4],[:a3,:cs4,:e4,:b4],
  [:b3,:d4,:fs4,:a4],[:fs3,:a3,:cs4,:e4],
  [:g3,:b3,:d4,:a4],[:a3,:cs4,:e4,:b4],
  [:d4,:fs4,:a4,:e5],[:d4,:fs4,:a4,:e5]
]
roots = [:d2,:d2,:d2,:b1,:g2,:a2,:fs2,:b1,:g2,:a2,:b1,:fs2,:g2,:a2,:d2,:d2]

in_thread(name: :piano_arpeggio) do
  with_fx :reverb, room: 0.75, mix: 0.17 do
    use_synth :piano
    16.times do |bar|
      c=voicings[bar]
      amp=bar<2 ? 0.42 : (bar>=14 ? 0.38 : 0.51)
      [0,2,1,3,2,1,3,2].each_with_index do |index,step|
        play c[index], release: 1.25, amp: amp*(step==0 ? 1.05 : 0.78), pan: -0.13
        sleep 0.5
      end
    end
  end
end

in_thread(name: :warm_pad) do
  use_synth :hollow
  with_fx :reverb, room: 0.85, mix: 0.30 do
    16.times do |bar|
      play voicings[bar], attack: 0.45, sustain: 2.25, release: 1.0,
        amp: bar<2 || bar>=14 ? 0.085 : 0.12, pan: 0.12
      sleep 4
    end
  end
end

in_thread(name: :bass) do
  use_synth :sine
  16.times do |bar|
    if bar<2 || bar==15
      play roots[bar], attack: 0.025, sustain: 2.4, release: 1.0, amp: 0.33
      sleep 4
    else
      play roots[bar], attack: 0.015, sustain: 0.85, release: 0.45, amp: 0.43
      sleep 2.5
      play note(roots[bar])+12, attack: 0.01, sustain: 0.30, release: 0.3, amp: 0.24
      sleep 1.5
    end
  end
end

in_thread(name: :soft_pulse) do
  16.times do |bar|
    if bar<2 || bar>=14 || bar==10
      sleep 4
    else
      8.times do |step|
        sample :bd_haus, amp: 0.32, cutoff: 85 if [0,5].include?(step)
        sample :perc_snap, amp: 0.18, pan: 0.04 if [2,6].include?(step)
        sample :drum_cymbal_closed, amp: step.even? ? 0.055 : 0.035,
          finish: 0.20, rate: 1.2, pan: 0.24
        sleep 0.5
      end
    end
  end
end

in_thread(name: :intro_and_coda_fill) do
  use_synth :pluck
  with_fx :reverb, room: 0.8, mix: 0.24 do
    [[:fs4,0.75],[:a4,0.75],[:b4,0.5],[:a4,1],[:e5,1],
     [:d5,1.5],[:a4,0.5],[:fs4,1],[:e4,1]].each do |n,d|
      play n, release: 1.4, amp: 0.22, pan: 0.22
      sleep d
    end
    sleep 48
    [[:fs4,1],[:e4,1],[:d4,2],[:a3,1],[:d4,3]].each do |n,d|
      play n, release: 1.7, amp: 0.16, pan: 0.22
      sleep d
    end
  end
end

sleep 64
puts "Fixed 16-bar backing complete. Allow the reverb tail to finish."
