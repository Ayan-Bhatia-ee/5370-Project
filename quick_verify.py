# quick_verify.py
import numpy as np
import matplotlib.pyplot as plt

traces = np.load('traces_hispeed/traces.npy')
pts = np.load('traces_hispeed/plaintexts.npy')
print(f"Shape: {traces.shape}")
print(f"Voltage range across all traces: {traces.min()*1000:.1f} to {traces.max()*1000:.1f} mV")

# Plot mean
mean = traces.mean(axis=0)

fig, axes = plt.subplots(3, 1, figsize=(14, 10))

# Mean of all 50 traces
axes[0].plot(mean * 1000, 'b-', linewidth=0.3)
axes[0].set_title(f'Mean of {len(traces)} traces — should show AES round structure')
axes[0].set_ylabel('Mean Power (mV)')
axes[0].grid(True)

# Overlay 5 raw traces (full)
for i in range(5):
    axes[1].plot(traces[i] * 1000, linewidth=0.2, alpha=0.5)
axes[1].set_title('5 raw traces overlaid (full window)')
axes[1].set_ylabel('Power (mV)')
axes[1].grid(True)

# Overlay 5 raw traces, zoomed to first 10k samples (first ~8 µs)
for i in range(5):
    axes[2].plot(traces[i, :10000] * 1000, linewidth=0.3, alpha=0.6)
axes[2].set_title('5 raw traces zoomed to first 10k samples')
axes[2].set_xlabel('Sample')
axes[2].set_ylabel('Power (mV)')
axes[2].grid(True)

plt.tight_layout()
plt.show()