# Technical results

Breakage checks only (decoding, length, format, clipping, silence, loudness). They say nothing about whether the music is good.

Silence: a warning above 5% of the take, a failure above 40%. Listening copies target -16.0 LUFS with a true-peak ceiling of -1.5 dBTP (checked at or below -1.0).

| # | Title | Render | Checks | Decodes | Length (req/actual s) | Rate / ch | Clipped | Silence | Native LUFS / TP | Copy LUFS / TP | Wall s |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | River waking up | rendered | passed | True | 120 / 120.0 | 48000 / 2 | 0.0000% | 2.1% | -15.2 / -1.5 | -16.2 / -2.3 | 39.0 |
| 2 | Midnight café | rendered | passed | True | 90 / 90.0 | 48000 / 2 | 0.0000% | 3.9% | -16.1 / -1.4 | -16.2 / -1.8 | 25.9 |
| 3 | Rise of the mountain | rendered | passed | True | 120 / 120.0 | 48000 / 2 | 0.0000% | 4.4% | -14.1 / -1.5 | -16.2 / -3.6 | 32.2 |
| 4 | Lanterns in the rain | rendered | warning (silence) | True | 90 / 90.0 | 48000 / 2 | 0.0000% | 6.8% | -16.2 / -1.5 | -16.2 / -2.0 | 26.7 |
| 5 | थोड़ी देर और | rendered | passed | True | 150 / 150.0 | 48000 / 2 | 0.0000% | 1.0% | -15.0 / -1.5 | -16.2 / -2.8 | 31.4 |
| 6 | बात अधूरी | rendered | passed | True | 120 / 120.0 | 48000 / 2 | 0.0000% | 2.0% | -15.6 / -1.3 | -16.2 / -1.9 | 23.5 |
| 7 | यहीं कहीं | rendered | passed | True | 150 / 150.0 | 48000 / 2 | 0.0000% | 2.0% | -14.6 / -1.4 | -16.2 / -3.0 | 31.7 |
| 8 | Run Toward the Light | rendered | passed | True | 120 / 120.0 | 48000 / 2 | 0.0000% | 1.8% | -14.8 / -1.4 | -16.2 / -3.0 | 24.8 |
| 9 | My Own Sunrise | rendered | passed | True | 120 / 120.0 | 48000 / 2 | 0.0000% | 1.9% | -15.3 / -1.1 | -16.2 / -2.0 | 29.3 |
| 10 | आज की रात | rendered | passed | True | 120 / 120.0 | 48000 / 2 | 0.0000% | 2.2% | -14.8 / -1.2 | -16.2 / -3.0 | 28.4 |
| 11 | After the Rain | rendered | passed | True | 150 / 150.0 | 48000 / 2 | 0.0000% | 2.1% | -14.1 / -1.4 | -16.2 / -3.5 | 29.0 |
| 12 | अपनी राह | rendered | passed | True | 120 / 120.0 | 48000 / 2 | 0.0000% | 1.6% | -13.6 / -1.5 | -16.2 / -4.0 | 30.3 |

## Independent local verification

Independent ffprobe and full ffmpeg decoding, loudnorm input measurements, astats sample peaks and silencedetect were run on every native file and listening copy. Detailed measurements and hashes: [independent_qc.json](independent_qc.json). No musical verdict is inferred from these measurements.

| # | Native / copy duration (s) | Copy LUFS | Copy true peak (dBTP) | Native / copy silence | Issues |
| --- | --- | --- | --- | --- | --- |
| 1 | 120.000 / 120.000 | -16.27 | -2.29 | 2.08% / 2.33% | none |
| 2 | 90.000 / 90.000 | -16.26 | -1.77 | 3.88% / 3.88% | none |
| 3 | 120.000 / 120.000 | -16.27 | -3.59 | 4.42% / 4.42% | none |
| 4 | 90.000 / 90.000 | -16.26 | -2.04 | 6.76% / 6.55% | none |
| 5 | 150.000 / 150.000 | -16.26 | -2.80 | 0.96% / 0.99% | none |
| 6 | 120.000 / 120.000 | -16.25 | -1.94 | 1.99% / 2.03% | none |
| 7 | 150.000 / 150.000 | -16.26 | -2.97 | 1.97% / 1.98% | none |
| 8 | 120.000 / 120.000 | -16.26 | -3.02 | 1.84% / 1.89% | none |
| 9 | 120.000 / 120.000 | -16.26 | -2.00 | 1.85% / 1.90% | none |
| 10 | 120.000 / 120.000 | -16.26 | -3.02 | 2.23% / 2.28% | none |
| 11 | 150.000 / 150.000 | -16.25 | -3.49 | 2.09% / 2.09% | none |
| 12 | 120.000 / 120.000 | -16.25 | -4.00 | 1.63% / 1.67% | none |

New attempts: 12; rendered: 12; failed: 0; ledger 19 → 31. Checkpoints unchanged in every successful engine record; outbound network attempts: []. All successful takes used MPS with the native MLX DiT backend, turbo checkpoint, saved seed, shift 3.0, eight steps, thinking false and no 5Hz LM.

Requested listening-copy target: -16 LUFS ±0.5 LU, true peak ≤ -1.5 dBTP. Any discrepancy is listed above without changing audio or rerendering. Silence warnings use >5%; mostly-silent failure uses >40%. Full-scale clipping is absent when the measured decoded sample peak stays below 0 dBFS.
