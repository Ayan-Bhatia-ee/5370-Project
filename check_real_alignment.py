import numpy as np
import matplotlib.pyplot as plt

traces = np.load('traces/traces.npy')  # use ORIGINAL, unaligned
print(f"Shape: {traces.shape}")

# Overlay 10 raw traces to see if they actually align well
fig, axes = plt.subplots(3, 1, figsize=(14, 10))

# Full view
for i in range(10):
    axes[0].plot(traces[i] * 1000, linewidth=0.3, alpha=0.5)
axes[0].set_title('10 raw traces overlaid (full)')
axes[0].set_ylabel('mV')
axes[0].grid(True)

# Around the trigger rising edge (should be near sample 1000)
for i in range(10):
    axes[1].plot(range(950, 1100), traces[i, 950:1100] * 1000, linewidth=0.5, alpha=0.7)
axes[1].set_title('Around trigger rising edge (samples 950-1100)')
axes[1].set_ylabel('mV')
axes[1].grid(True)

# Around the trigger falling edge (should be near sample 4850)
for i in range(10):
    axes[2].plot(range(4700, 5000), traces[i, 4700:5000] * 1000, linewidth=0.5, alpha=0.7)
axes[2].set_title('Around trigger falling edge (samples 4700-5000)')
axes[2].set_xlabel('Sample index')
axes[2].set_ylabel('mV')
axes[2].grid(True)

plt.tight_layout()
plt.show()

# Check what's at the RISING edge (start of AES)
# This is what matters most for CPA (first round is here)
rising_edges = []
for t in traces[:500]:
    # find first sample where value drops below some threshold (negative spike)
    edge_region = t[950:1050]
    rising_edges.append(np.argmin(edge_region) + 950)

rising_edges = np.array(rising_edges)
print(f"\nRising-edge-like position in first 500 traces:")
print(f"  min={rising_edges.min()}, max={rising_edges.max()}, std={rising_edges.std():.2f}")