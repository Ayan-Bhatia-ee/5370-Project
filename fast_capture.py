import pyvisa
import numpy as np
import time
import os

SCOPE_ADDR = 'USB0::0x2A8D::0x17BC::MY65060111::0::INSTR'
N_TRACES = 5000                # START SMALL - test with 50 first
OUTPUT_DIR = 'traces_hispeed'
SAVE_EVERY = 200

LFSR_SEED = 0xACE1BEEF
LFSR_TAPS = 0xD0000001

def lfsr_byte(state):
    out = 0
    for _ in range(8):
        bit = state & 1
        state >>= 1
        if bit: state ^= LFSR_TAPS
        out = ((out << 1) | bit) & 0xFF
    return out, state

def generate_plaintexts(n):
    pts = np.zeros((n, 16), dtype=np.uint8)
    state = LFSR_SEED
    for i in range(n):
        for j in range(16):
            b, state = lfsr_byte(state)
            pts[i, j] = b
    return pts

def configure_scope(scope):
    scope.write('*RST')
    time.sleep(2)
    scope.write('*CLS')
    time.sleep(0.5)
    
    # Longer timebase window to include more of AES
    scope.write(':TIMebase:SCALe 0.0002')        # 200 µs/div → 2 ms window
    scope.write(':TIMebase:POSition 0.0009')     # trigger near left
    
    # CH1 - the key change: BW limit ON
    scope.write(':CHANnel1:DISPlay ON')
    scope.write(':CHANnel1:PROBe 10')
    scope.write(':CHANnel1:COUPling AC')
    scope.write(':CHANnel1:SCALe 0.010')          # 10 mV/div
    scope.write(':CHANnel1:OFFSet 0')
    scope.write(':CHANnel1:BWLimit ON')           # ← ON! Filters clock noise
    
    scope.write(':CHANnel2:DISPlay ON')
    scope.write(':CHANnel2:PROBe 10')
    scope.write(':CHANnel2:COUPling DC')
    scope.write(':CHANnel2:SCALe 1.0')
    scope.write(':CHANnel2:OFFSet 1.5')
    
    scope.write(':TRIGger:MODE EDGE')
    scope.write(':TRIGger:EDGE:SOURce CHAN2')
    scope.write(':TRIGger:EDGE:SLOPe POSitive')
    scope.write(':TRIGger:EDGE:LEVel 1.5')
    scope.write(':TRIGger:SWEep NORMal')
    
    scope.write(':ACQuire:TYPE NORMal')
    
    # Request fewer points — scope will pick ~100 MSa/s
    scope.write(':WAVeform:SOURce CHAN1')
    scope.write(':WAVeform:FORMat BYTE')
    scope.write(':WAVeform:POINts:MODE RAW')
    scope.write(':WAVeform:POINts 200000')        # 200k points over 2 ms = 100 MSa/s
    
    time.sleep(1.5)
    
    print("=== Verified scope state ===")
    print(f"  CH1 coupling: {scope.query(':CHANnel1:COUPling?').strip()}")
    print(f"  CH1 scale:    {float(scope.query(':CHANnel1:SCALe?').strip())*1000:.1f} mV/div")
    print(f"  CH1 BW limit: {scope.query(':CHANnel1:BWLimit?').strip()}")
    print(f"  Timebase:     {float(scope.query(':TIMebase:SCALe?').strip())*1e6:.1f} µs/div")
    print(f"  Sample rate:  {float(scope.query(':ACQuire:SRATe?').strip())/1e6:.1f} MSa/s")
    print()

def capture_trace(scope):
    scope.write(':SINGle')
    scope.query('*OPC?')
    preamble = scope.query(':WAVeform:PREamble?').split(',')
    y_inc = float(preamble[7]); y_orig = float(preamble[8]); y_ref = float(preamble[9])
    raw = scope.query_binary_values(':WAVeform:DATA?', datatype='B', container=np.array)
    volts = (raw - y_ref) * y_inc + y_orig
    time.sleep(0.01)
    return volts.astype(np.float32), raw

def open_scope_with_retry(rm, attempts=5):
    for a in range(attempts):
        try:
            s = rm.open_resource(SCOPE_ADDR)
            s.timeout = 15000
            s.clear()
            _ = s.query('*IDN?')
            return s
        except Exception as e:
            print(f"  open attempt {a+1}: {e}")
            time.sleep(2)
    raise RuntimeError("Can't open scope")

def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    print(f"Generating {N_TRACES} plaintexts...")
    pts = generate_plaintexts(N_TRACES)
    
    rm = pyvisa.ResourceManager()
    scope = open_scope_with_retry(rm)
    print("Connected:", scope.query('*IDN?').strip())
    configure_scope(scope)
    
    print("First trace — checking signal quality...")
    first, raw = capture_trace(scope)
    actual_points = len(first)
    print(f"  Points: {actual_points}")
    print(f"  Raw byte: min={raw.min()}, max={raw.max()}, std={raw.std():.2f}")
    print(f"  Voltage: {first.min()*1000:.2f} to {first.max()*1000:.2f} mV")
    
    if raw.std() < 10:
        print("\n⚠️  WARNING: Raw byte std is very low (< 10).")
        print("    CH1 may not be picking up the AES signal properly.")
        print("    Continuing anyway, but results may be poor.")
    else:
        print("  ✓ Signal quality looks good!")
    print()
    
    traces = np.zeros((N_TRACES, actual_points), dtype=np.float32)
    traces[0] = first
    
    t0 = time.time()
    for i in range(1, N_TRACES):
        ok = False
        for attempt in range(3):
            try:
                tr, _ = capture_trace(scope)
                if len(tr) >= actual_points:
                    traces[i] = tr[:actual_points]
                else:
                    traces[i, :len(tr)] = tr
                ok = True
                break
            except Exception as e:
                print(f"  [{i}] attempt {attempt+1}: {e}")
                time.sleep(1)
                try: scope.close()
                except: pass
                try:
                    scope = open_scope_with_retry(rm)
                    configure_scope(scope)
                except: pass
        if not ok:
            print(f"  [{i}] skipped")
            continue
        
        if (i + 1) % SAVE_EVERY == 0:
            np.save(os.path.join(OUTPUT_DIR, 'traces.npy'), traces[:i+1])
            np.save(os.path.join(OUTPUT_DIR, 'plaintexts.npy'), pts[:i+1])
            el = time.time() - t0
            rate = (i + 1) / el
            eta = (N_TRACES - i - 1) / rate
            print(f"  {i+1}/{N_TRACES} ({rate:.2f}/s, ETA {eta:.0f}s, saved)")
    
    np.save(os.path.join(OUTPUT_DIR, 'traces.npy'), traces)
    np.save(os.path.join(OUTPUT_DIR, 'plaintexts.npy'), pts)
    print(f"\nDone: {N_TRACES} traces in {time.time()-t0:.1f}s")
    
    try: scope.write(':RUN'); scope.close()
    except: pass

if __name__ == '__main__':
    main()