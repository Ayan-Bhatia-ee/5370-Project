import numpy as np
import matplotlib.pyplot as plt

traces = np.load('traces/traces.npy')
plaintexts = np.load('traces/plaintexts.npy')

print(f"Number of traces: {traces.shape[0]}")
print(f"Samples per trace: {traces.shape[1]}")
print(f"First plaintext: {plaintexts[0].tolist()}")
print(f"Last plaintext: {plaintexts[-1].tolist()}")

fig, axes = plt.subplots(2, 1, figsize=(14, 8))

# Plot first 10 traces overlaid
for i in range(min(10, len(traces))):
    axes[0].plot(traces[i] * 1000, linewidth=0.3, alpha=0.6)
axes[0].set_ylabel('Power (mV)')
axes[0].set_title(f'First {min(10, len(traces))} traces overlaid')
axes[0].grid(True)

# Mean trace — should reveal AES structure
axes[1].plot(traces.mean(axis=0) * 1000, 'b-', linewidth=0.5)
axes[1].set_xlabel('Sample index')
axes[1].set_ylabel('Mean Power (mV)')
axes[1].set_title(f'Mean of all {len(traces)} traces — look for 10 AES rounds')
axes[1].grid(True)

plt.tight_layout()
plt.show()