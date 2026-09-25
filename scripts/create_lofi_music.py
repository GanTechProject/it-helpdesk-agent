import math
import struct
import wave
import numpy as np

SAMPLE_RATE = 44100
DURATION = 45.0  # seconds
BPM = 88.0
BEAT_DUR = 60.0 / BPM
BAR_DUR = BEAT_DUR * 4

# Chord frequencies (Hz): Ebmaj7, Cm9, Fm7, Bb7
CHORDS = [
    # Ebmaj7 (Eb3, G3, Bb3, D4)
    [155.56, 196.00, 233.08, 293.66],
    # Cm9 (C3, Eb3, G3, Bb3, D4)
    [130.81, 155.56, 196.00, 233.08, 293.66],
    # Fm7 (F3, Ab3, C4, Eb4)
    [174.61, 207.65, 261.63, 311.13],
    # Bb7 (Bb2, D3, F3, Ab3, C4)
    [116.54, 146.83, 174.61, 207.65, 261.63],
]

BASS_NOTES = [
    # Eb2, C2, F2, Bb1
    77.78, 65.41, 87.31, 58.27
]

total_samples = int(SAMPLE_RATE * DURATION)
audio_left = np.zeros(total_samples, dtype=np.float32)
audio_right = np.zeros(total_samples, dtype=np.float32)

t = np.arange(total_samples) / SAMPLE_RATE

# 1. Vinyl Crackle & Ambient Hiss
np.random.seed(42)
crackle = np.random.normal(0, 0.008, total_samples)
# Subtle pops
pops = (np.random.random(total_samples) > 0.9998).astype(np.float32) * np.random.uniform(0.05, 0.15, total_samples)
ambient = crackle + pops
audio_left += ambient
audio_right += ambient

# Helper for envelope
def env(t_arr, attack=0.01, decay=0.3):
    ret = np.zeros_like(t_arr)
    att_mask = (t_arr >= 0) & (t_arr < attack)
    dec_mask = t_arr >= attack
    ret[att_mask] = t_arr[att_mask] / attack
    ret[dec_mask] = np.exp(-(t_arr[dec_mask] - attack) / decay)
    return np.maximum(0, ret)

# 2. Synthesize Chords & Rhytm Loops
num_bars = int(np.ceil(DURATION / BAR_DUR))

for bar in range(num_bars):
    bar_start_t = bar * BAR_DUR
    chord = CHORDS[bar % len(CHORDS)]
    bass_freq = BASS_NOTES[bar % len(BASS_NOTES)]

    # Play chord on beat 1 and beat 2.5
    for stroke_offset in [0.0, BEAT_DUR * 1.5, BEAT_DUR * 3.0]:
        t_stroke = bar_start_t + stroke_offset
        if t_stroke >= DURATION:
            continue
        start_idx = int(t_stroke * SAMPLE_RATE)
        stroke_dur = BEAT_DUR * 1.8
        dur_samples = int(stroke_dur * SAMPLE_RATE)
        end_idx = min(total_samples, start_idx + dur_samples)
        if end_idx <= start_idx:
            continue

        stroke_t = np.arange(end_idx - start_idx) / SAMPLE_RATE

        # E-Piano Rhodes sound: sine + harmonics + tremolo modulation
        tremolo = 1.0 + 0.15 * np.sin(2 * np.pi * 4.5 * stroke_t)
        chord_wave = np.zeros(end_idx - start_idx, dtype=np.float32)

        for freq in chord:
            # Fund + 2nd + 3rd harmonic
            f_wave = np.sin(2 * np.pi * freq * stroke_t) + 0.35 * np.sin(2 * np.pi * freq * 2 * stroke_t) + 0.1 * np.sin(2 * np.pi * freq * 3 * stroke_t)
            chord_wave += f_wave

        chord_wave *= 0.08 * env(stroke_t, attack=0.02, decay=0.8) * tremolo

        audio_left[start_idx:end_idx] += chord_wave * 0.9
        audio_right[start_idx:end_idx] += chord_wave * 1.1

    # Bassline
    for bass_offset in [0.0, BEAT_DUR * 1.75, BEAT_DUR * 2.5]:
        t_bass = bar_start_t + bass_offset
        if t_bass >= DURATION:
            continue
        start_idx = int(t_bass * SAMPLE_RATE)
        dur_samples = int(BEAT_DUR * 1.2 * SAMPLE_RATE)
        end_idx = min(total_samples, start_idx + dur_samples)
        if end_idx <= start_idx:
            continue
        b_t = np.arange(end_idx - start_idx) / SAMPLE_RATE
        b_wave = np.sin(2 * np.pi * bass_freq * b_t) + 0.2 * np.sin(2 * np.pi * bass_freq * 2 * b_t)
        b_wave *= 0.22 * env(b_t, attack=0.015, decay=0.4)

        audio_left[start_idx:end_idx] += b_wave
        audio_right[start_idx:end_idx] += b_wave

    # 3. Lo-Fi Beat (Kick, Snare, Hi-Hats)
    for beat in range(4):
        beat_t = bar_start_t + beat * BEAT_DUR

        # KICK on beat 0 and beat 2.5
        kick_times = [0.0, 2.5 * BEAT_DUR] if beat in [0, 2] else []
        if beat == 2:
            kick_times = [2.5 * BEAT_DUR - 2 * BEAT_DUR]

        if beat in [0, 2]:
            k_start = int((bar_start_t + (0 if beat==0 else 2.5)*BEAT_DUR) * SAMPLE_RATE)
            k_dur = int(0.25 * SAMPLE_RATE)
            k_end = min(total_samples, k_start + k_dur)
            if k_end > k_start:
                kt = np.arange(k_end - k_start) / SAMPLE_RATE
                # Pitch sweep from 90Hz -> 40Hz
                freq_sweep = 40.0 + 50.0 * np.exp(-kt * 30.0)
                phase = 2 * np.pi * np.cumsum(freq_sweep) / SAMPLE_RATE
                kick = 0.45 * np.sin(phase) * np.exp(-kt * 15.0)
                audio_left[k_start:k_end] += kick
                audio_right[k_start:k_end] += kick

        # SNARE / RIMSHOT on beat 1 and beat 3
        if beat in [1, 3]:
            s_start = int(beat_t * SAMPLE_RATE)
            s_dur = int(0.18 * SAMPLE_RATE)
            s_end = min(total_samples, s_start + s_dur)
            if s_end > s_start:
                st = np.arange(s_end - s_start) / SAMPLE_RATE
                noise = np.random.normal(0, 0.18, len(st))
                body = 0.25 * np.sin(2 * np.pi * 180.0 * st)
                snare = (noise + body) * np.exp(-st * 22.0)
                audio_left[s_start:s_end] += snare * 0.95
                audio_right[s_start:s_end] += snare * 1.05

        # HI-HATS on 8th notes (swing)
        for hat_sub in [0.0, 0.5 * BEAT_DUR * 1.08]:  # Slight swing offset
            h_t_val = beat_t + hat_sub
            h_start = int(h_t_val * SAMPLE_RATE)
            h_dur = int(0.06 * SAMPLE_RATE)
            h_end = min(total_samples, h_start + h_dur)
            if h_end > h_start:
                ht = np.arange(h_end - h_start) / SAMPLE_RATE
                hat_noise = np.random.normal(0, 0.08, len(ht))
                # High pass simulation
                hat = hat_noise * np.exp(-ht * 60.0)
                vol = 0.12 if hat_sub == 0.0 else 0.07
                audio_left[h_start:h_end] += hat * vol
                audio_right[h_start:h_end] += hat * vol * 0.95

# Soft master limiter & smooth fade out
fade_out_dur = 2.5
fade_samples = int(fade_out_dur * SAMPLE_RATE)
fade_vec = np.ones(total_samples, dtype=np.float32)
fade_vec[-fade_samples:] = np.linspace(1.0, 0.0, fade_samples)

audio_left = np.tanh(audio_left * 1.2) * 0.85 * fade_vec
audio_right = np.tanh(audio_right * 1.2) * 0.85 * fade_vec

# Convert to 16-bit PCM WAV
audio_stereo = np.column_stack((audio_left, audio_right))
audio_int16 = (audio_stereo * 32767.0).astype(np.int16)

out_wav = "/config/.gemini/antigravity/scratch/it-helpdesk-agent/lofi_track.wav"
with wave.open(out_wav, "wb") as wf:
    wf.setnchannels(2)
    wf.setsampwidth(2)
    wf.setframerate(SAMPLE_RATE)
    wf.writeframes(audio_int16.tobytes())

print("Successfully generated lo-fi music track:", out_wav)
