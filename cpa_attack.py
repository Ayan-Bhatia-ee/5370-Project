import numpy as np
import matplotlib.pyplot as plt

# ===== AES S-box =====
SBOX = np.array([
    0x63,0x7c,0x77,0x7b,0xf2,0x6b,0x6f,0xc5,0x30,0x01,0x67,0x2b,0xfe,0xd7,0xab,0x76,
    0xca,0x82,0xc9,0x7d,0xfa,0x59,0x47,0xf0,0xad,0xd4,0xa2,0xaf,0x9c,0xa4,0x72,0xc0,
    0xb7,0xfd,0x93,0x26,0x36,0x3f,0xf7,0xcc,0x34,0xa5,0xe5,0xf1,0x71,0xd8,0x31,0x15,
    0x04,0xc7,0x23,0xc3,0x18,0x96,0x05,0x9a,0x07,0x12,0x80,0xe2,0xeb,0x27,0xb2,0x75,
    0x09,0x83,0x2c,0x1a,0x1b,0x6e,0x5a,0xa0,0x52,0x3b,0xd6,0xb3,0x29,0xe3,0x2f,0x84,
    0x53,0xd1,0x00,0xed,0x20,0xfc,0xb1,0x5b,0x6a,0xcb,0xbe,0x39,0x4a,0x4c,0x58,0xcf,
    0xd0,0xef,0xaa,0xfb,0x43,0x4d,0x33,0x85,0x45,0xf9,0x02,0x7f,0x50,0x3c,0x9f,0xa8,
    0x51,0xa3,0x40,0x8f,0x92,0x9d,0x38,0xf5,0xbc,0xb6,0xda,0x21,0x10,0xff,0xf3,0xd2,
    0xcd,0x0c,0x13,0xec,0x5f,0x97,0x44,0x17,0xc4,0xa7,0x7e,0x3d,0x64,0x5d,0x19,0x73,
    0x60,0x81,0x4f,0xdc,0x22,0x2a,0x90,0x88,0x46,0xee,0xb8,0x14,0xde,0x5e,0x0b,0xdb,
    0xe0,0x32,0x3a,0x0a,0x49,0x06,0x24,0x5c,0xc2,0xd3,0xac,0x62,0x91,0x95,0xe4,0x79,
    0xe7,0xc8,0x37,0x6d,0x8d,0xd5,0x4e,0xa9,0x6c,0x56,0xf4,0xea,0x65,0x7a,0xae,0x08,
    0xba,0x78,0x25,0x2e,0x1c,0xa6,0xb4,0xc6,0xe8,0xdd,0x74,0x1f,0x4b,0xbd,0x8b,0x8a,
    0x70,0x3e,0xb5,0x66,0x48,0x03,0xf6,0x0e,0x61,0x35,0x57,0xb9,0x86,0xc1,0x1d,0x9e,
    0xe1,0xf8,0x98,0x11,0x69,0xd9,0x8e,0x94,0x9b,0x1e,0x87,0xe9,0xce,0x55,0x28,0xdf,
    0x8c,0xa1,0x89,0x0d,0xbf,0xe6,0x42,0x68,0x41,0x99,0x2d,0x0f,0xb0,0x54,0xbb,0x16,
], dtype=np.uint8)

# Hamming weight lookup
HW = np.array([bin(i).count('1') for i in range(256)], dtype=np.uint8)

# Known correct key (for verification)
TRUE_KEY = np.array([
    0x2B, 0x7E, 0x15, 0x16,
    0x28, 0xAE, 0xD2, 0xA6,
    0xAB, 0xF7, 0x15, 0x88,
    0x09, 0xCF, 0x4F, 0x3C,
], dtype=np.uint8)

# ===== Load data =====
print("Loading traces...")
#traces = np.load('traces/traces.npy')
#plaintexts = np.load('traces/plaintexts.npy')
traces = np.load('traces_hispeed/traces.npy')
plaintexts = np.load('traces_hispeed/plaintexts.npy')
print(f"Traces shape: {traces.shape}")
print(f"Plaintexts shape: {plaintexts.shape}")

# ===== Trim to the AES region =====
# Based on your mean trace, AES runs roughly from sample 5000 to 23500
# Add some margin for safety
TRACE_START = 1000   # skip first few samples (trigger transient)
TRACE_END = traces.shape[1] - 1000
traces = traces[:, TRACE_START:TRACE_END]
print(f"Trimmed traces shape: {traces.shape}")

N, T = traces.shape

# ===== CPA Attack =====
def cpa_byte(traces, plaintexts, byte_index):
    """
    Recover one byte of the AES key using CPA.
    Returns: (best_guess, correlation_matrix)
    """
    pt_col = plaintexts[:, byte_index].astype(np.int32)  # (N,)
    
    corr_matrix = np.zeros((256, traces.shape[1]), dtype=np.float32)
    
    # Center traces once (optimization)
    traces_mean = traces.mean(axis=0)
    traces_centered = traces - traces_mean
    traces_var = (traces_centered ** 2).sum(axis=0)
    traces_std = np.sqrt(traces_var)
    
    for k_guess in range(256):
        # Hypothetical intermediate: Hamming weight of S-box(pt XOR k)
        hyp = HW[SBOX[pt_col ^ k_guess]].astype(np.float32)  # (N,)
        
        # Pearson correlation coefficient (vectorized)
        hyp_centered = hyp - hyp.mean()
        hyp_std = np.sqrt((hyp_centered ** 2).sum())
        
        if hyp_std == 0:
            continue
        
        numerator = hyp_centered @ traces_centered   # (T,)
        denominator = hyp_std * traces_std + 1e-12
        corr_matrix[k_guess] = numerator / denominator
    
    # Best guess = key byte with highest |correlation| at any time point
    max_abs_corr = np.max(np.abs(corr_matrix), axis=1)  # (256,)
    best_guess = int(np.argmax(max_abs_corr))
    return best_guess, corr_matrix, max_abs_corr

# ===== Run attack on all 16 key bytes =====
print("\nRunning CPA on all 16 key bytes...")
print(f"True key (for verification): {[f'{b:02X}' for b in TRUE_KEY]}")
print()

recovered_key = []
all_max_corrs = []

for byte_idx in range(16):
    best_guess, corr_matrix, max_abs_corr = cpa_byte(traces, plaintexts, byte_idx)
    
    # Sort candidates by correlation strength
    ranking = np.argsort(-max_abs_corr)  # descending
    true_rank = int(np.where(ranking == TRUE_KEY[byte_idx])[0][0])
    
    correct = best_guess == TRUE_KEY[byte_idx]
    mark = '✓' if correct else '✗'
    
    print(f"Byte {byte_idx:2d}: guess=0x{best_guess:02X} true=0x{TRUE_KEY[byte_idx]:02X} "
          f"[{mark}] corr={max_abs_corr[best_guess]:.4f} true_rank={true_rank}")
    
    recovered_key.append(best_guess)
    all_max_corrs.append(max_abs_corr)

recovered_key = np.array(recovered_key, dtype=np.uint8)

# ===== Summary =====
correct_bytes = np.sum(recovered_key == TRUE_KEY)
print(f"\n===== RESULT =====")
print(f"Recovered key: {[f'{b:02X}' for b in recovered_key]}")
print(f"True key:      {[f'{b:02X}' for b in TRUE_KEY]}")
print(f"Bytes correct: {correct_bytes}/16")

# ===== Plot correlation for byte 0 =====
_, corr_matrix_0, _ = cpa_byte(traces, plaintexts, 0)

fig, ax = plt.subplots(figsize=(14, 6))
for k in range(256):
    if k == TRUE_KEY[0]:
        continue  # plot true key last, on top
    ax.plot(corr_matrix_0[k], color='gray', linewidth=0.3, alpha=0.3)
ax.plot(corr_matrix_0[TRUE_KEY[0]], color='red', linewidth=1.5, label=f'True key byte 0 = 0x{TRUE_KEY[0]:02X}')
ax.set_xlabel('Sample index (within AES region)')
ax.set_ylabel('Pearson correlation')
ax.set_title('CPA correlation traces for byte 0 — true key should stand out')
ax.legend()
ax.grid(True)
plt.tight_layout()
plt.show()