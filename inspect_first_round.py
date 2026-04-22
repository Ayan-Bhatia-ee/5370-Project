import numpy as np
import matplotlib.pyplot as plt

traces = np.load('traces/traces.npy')
plaintexts = np.load('traces/plaintexts.npy')

print(f"Shape: {traces.shape}")

# Find trigger edges in mean trace (big spikes)
mean = traces.mean(axis=0)

fig, axes = plt.subplots(3, 1, figsize=(14, 9))

# Full mean trace
axes[0].plot(mean * 1000, 'b-', linewidth=0.5)
axes[0].set_title('Mean of all traces (full)')
axes[0].set_ylabel('mV')
axes[0].grid(True)

# Zoom to find trigger rising edge (likely a spike near beginning)
axes[1].plot(mean[:1500] * 1000, 'b-', linewidth=0.7)
axes[1].set_title('First 1500 samples — should see trigger spike + start of AES')
axes[1].set_ylabel('mV')
axes[1].grid(True)

# A window right after trigger (where round 1 happens)
axes[2].plot(mean[500:2500] * 1000, 'b-', linewidth=0.7)
axes[2].set_title('Samples 500-2500 (should see AES round structure)')
axes[2].set_xlabel('Sample offset')
axes[2].set_ylabel('mV')
axes[2].grid(True)

plt.tight_layout()
plt.show()

# Check trigger jitter by finding the rising edge of the power spike in each trace
print("\nChecking alignment...")
# Find the position of max abs value in first 1000 samples for each trace
edge_positions = np.argmax(np.abs(traces[:, :1000]), axis=1)
print(f"Trigger edge position: min={edge_positions.min()}, max={edge_positions.max()}, "
      f"std={edge_positions.std():.1f}")
print(f"If std > 5, you have alignment issues")