# quick_check.py
import numpy as np
import matplotlib.pyplot as plt

traces = np.load('traces_hispeed/traces.npy')
print(f"Shape: {traces.shape}")

# Plot mean — should show CLEAR AES structure now
mean = traces.mean(axis=0)
fig, ax = plt.subplots(figsize=(14, 5))
ax.plot(mean * 1000, 'b-', linewidth=0.5)
ax.set_xlabel('Sample')
ax.set_ylabel('mV')
ax.set_title(f'Mean of {len(traces)} traces (hispeed capture)')
ax.grid(True)
plt.tight_layout()
plt.show()

# Overlay 5 raw traces zoomed to first bit
fig, ax = plt.subplots(figsize=(14, 5))
for i in range(5):
    ax.plot(traces[i, :5000] * 1000, linewidth=0.3, alpha=0.7)
ax.set_xlabel('Sample')
ax.set_ylabel('mV')
ax.set_title('First 5 traces overlaid, first 5000 samples')
ax.grid(True)
plt.tight_layout()
plt.show()