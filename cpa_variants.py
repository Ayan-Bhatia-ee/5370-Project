import numpy as np

SBOX = np.array([...], dtype=np.uint8)  # same S-box as before — paste it here
HW = np.array([bin(i).count('1') for i in range(256)], dtype=np.uint8)
TRUE_KEY = np.array([
    0x2B,0x7E,0x15,0x16,0x28,0xAE,0xD2,0xA6,
    0xAB,0xF7,0x15,0x88,0x09,0xCF,0x4F,0x3C,
], dtype=np.uint8)

traces = np.load('traces/traces.npy')  # UNALIGNED
plaintexts = np.load('traces/plaintexts.npy')
print(f"Shape: {traces.shape}")

# Narrow window — first round only
TRACE_START = 1050
TRACE_END = 1500
traces = traces[:, TRACE_START:TRACE_END]
print(f"Trimmed: {traces.shape}")

def cpa_with_model(traces, plaintexts, byte_index, model_fn):
    pt_col = plaintexts[:, byte_index].astype(np.int32)
    traces_c = traces - traces.mean(axis=0)
    traces_std = np.sqrt((traces_c ** 2).sum(axis=0))
    
    corrs = np.zeros((256, traces.shape[1]), dtype=np.float32)
    for k in range(256):
        hyp = model_fn(pt_col, k).astype(np.float32)
        h_c = hyp - hyp.mean()
        h_std = np.sqrt((h_c ** 2).sum())
        if h_std == 0: continue
        corrs[k] = (h_c @ traces_c) / (h_std * traces_std + 1e-12)
    return corrs

# Different leakage models
models = {
    'HW(Sbox(p^k))': lambda p, k: HW[SBOX[p ^ k]],
    'HW(p^k)':      lambda p, k: HW[p ^ k],
    'HW(Sbox(p^k)^p)': lambda p, k: HW[SBOX[p ^ k] ^ p],  # hamming distance pre→post sbox
    'Sbox(p^k)':    lambda p, k: SBOX[p ^ k],             # value itself
}

print(f"True key: {[f'{b:02X}' for b in TRUE_KEY]}\n")

for model_name, model_fn in models.items():
    print(f"\n=== Model: {model_name} ===")
    correct = 0
    for b in range(16):
        corrs = cpa_with_model(traces, plaintexts, b, model_fn)
        max_abs = np.max(np.abs(corrs), axis=1)
        ranking = np.argsort(-max_abs)
        best = int(ranking[0])
        true_rank = int(np.where(ranking == TRUE_KEY[b])[0][0])
        if best == TRUE_KEY[b]:
            correct += 1
        print(f"  Byte {b:2d}: guess=0x{best:02X} true=0x{TRUE_KEY[b]:02X} rank={true_rank:3d}")
    print(f"  Correct: {correct}/16")