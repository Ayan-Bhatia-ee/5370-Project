import numpy as np
import matplotlib.pyplot as plt

traces = np.load('traces/traces.npy')
print(f"Number of traces: {traces.shape[0]}")

# Use falling edge as alignment reference (it's cleaner, bigger spike)
# Search near sample 4850
search_start = 4500
search_end = 5200

# For each trace, find position of max positive value in that window
edge_positions = np.argmax(traces[:, search_start:search_end], axis=1) + search_start

print(f"Falling edge positions: min={edge_positions.min()}, max={edge_positions.max()}, "
      f"std={edge_positions.std():.2f}")

# Histogram
fig, ax = plt.subplots(figsize=(12, 5))
ax.hist(edge_positions, bins=50)
ax.set_xlabel('Sample index of falling edge spike')
ax.set_ylabel('Count')
ax.set_title(f'Trigger falling edge positions across {len(edge_positions)} traces')
ax.grid(True)
plt.tight_layout()
plt.show()

# Now overlay first 5 traces zoomed to AES region
fig, ax = plt.subplots(figsize=(14, 5))
for i in range(5):
    ax.plot(traces[i, 1000:5000] * 1000, linewidth=0.4, alpha=0.7, label=f'Trace {i}')
ax.set_xlabel('Sample offset (from 1000)')
ax.set_ylabel('mV')
ax.set_title('First 5 traces in AES region — should look similar')
ax.legend()
ax.grid(True)
plt.tight_layout()
plt.show()