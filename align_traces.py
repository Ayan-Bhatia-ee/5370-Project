import numpy as np
import matplotlib.pyplot as plt

traces = np.load('traces/traces.npy').copy()
plaintexts = np.load('traces/plaintexts.npy').copy()
print(f"Original shape: {traces.shape}")

# Use the first trace as reference for alignment
# Pick a window containing strong features (AES computation region)
ref_window_start = 1100
ref_window_end = 4600
reference = traces[0, ref_window_start:ref_window_end]

# Cross-correlate each trace with the reference and find the best alignment
max_shift = 400  # samples of drift we'll allow
aligned = np.zeros_like(traces)
shifts = []

for i in range(len(traces)):
    # Search for best shift
    best_corr = -np.inf
    best_shift = 0
    for shift in range(-max_shift, max_shift + 1):
        s_start = ref_window_start + shift
        s_end = ref_window_end + shift
        if s_start < 0 or s_end > traces.shape[1]:
            continue
        segment = traces[i, s_start:s_end]
        # normalize
        ref_c = reference - reference.mean()
        seg_c = segment - segment.mean()
        ref_norm = np.linalg.norm(ref_c)
        seg_norm = np.linalg.norm(seg_c)
        if ref_norm == 0 or seg_norm == 0:
            continue
        corr = np.dot(ref_c, seg_c) / (ref_norm * seg_norm)
        if corr > best_corr:
            best_corr = corr
            best_shift = shift
    
    # Apply shift by rolling (wrap-around is OK since we'll trim later)
    aligned[i] = np.roll(traces[i], -best_shift)
    shifts.append(best_shift)
    
    if (i + 1) % 200 == 0:
        print(f"  Aligned {i+1}/{len(traces)}")

shifts = np.array(shifts)
print(f"\nShifts: min={shifts.min()}, max={shifts.max()}, std={shifts.std():.2f}")

# Save aligned traces
np.save('traces/traces_aligned.npy', aligned)
np.save('traces/plaintexts_aligned.npy', plaintexts)
print("Saved aligned traces")

# Plot mean before/after alignment
fig, axes = plt.subplots(2, 1, figsize=(14, 8))
axes[0].plot(traces.mean(axis=0) * 1000, 'b-', linewidth=0.5)
axes[0].set_title('Mean trace BEFORE alignment')
axes[0].set_ylabel('mV')
axes[0].grid(True)

axes[1].plot(aligned.mean(axis=0) * 1000, 'g-', linewidth=0.5)
axes[1].set_title('Mean trace AFTER alignment')
axes[1].set_xlabel('Sample')
axes[1].set_ylabel('mV')
axes[1].grid(True)

plt.tight_layout()
plt.show()

# Histogram of shifts
fig, ax = plt.subplots(figsize=(10, 5))
ax.hist(shifts, bins=50)
ax.set_xlabel('Shift applied (samples)')
ax.set_ylabel('Count')
ax.set_title('Distribution of alignment shifts')
ax.grid(True)
plt.tight_layout()
plt.show()