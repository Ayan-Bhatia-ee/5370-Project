import pyvisa
import numpy as np
import time
import os

SCOPE_ADDR = 'USB0::0x2A8D::0x17BC::MY65060111::0::INSTR'
N_TRACES = 3000
OUTPUT_DIR = 'traces'
SAVE_EVERY = 200  # save progress every 200 traces
REQUESTED_POINTS = 10000

LFSR_SEED = 0xACE1BEEF
LFSR_TAPS = 0xD0000001

def lfsr_byte(state):
    out = 0
    for _ in range(8):
        bit = state & 1
        state >>= 1
        if bit:
            state ^= LFSR_TAPS
        out = ((out << 1) | bit) & 0xFF
    return out, state

def generate_plaintexts(n_traces):
    plaintexts = np.zeros((n_traces, 16), dtype=np.uint8)
    state = LFSR_SEED
    for i in range(n_traces):
        for j in range(16):
            pt_byte, state = lfsr_byte(state)
            plaintexts[i, j] = pt_byte
    return plaintexts

def configure_scope(scope):
    scope.write(':TIMebase:SCALe 0.0005')
    scope.write(':TIMebase:POSition 0.002')
    scope.write(':CHANnel1:DISPlay ON')
    scope.write(':CHANnel1:COUPling AC')
    scope.write(':CHANnel1:SCALe 0.010')
    scope.write(':CHANnel1:BWLimit ON')
    scope.write(':CHANnel1:PROBe 10')
    scope.write(':CHANnel2:DISPlay ON')
    scope.write(':CHANnel2:COUPling DC')
    scope.write(':CHANnel2:SCALe 1.0')
    scope.write(':CHANnel2:OFFSet 1.5')
    scope.write(':CHANnel2:PROBe 10')
    scope.write(':TRIGger:MODE EDGE')
    scope.write(':TRIGger:EDGE:SOURce CHAN2')
    scope.write(':TRIGger:EDGE:SLOPe POSitive')
    scope.write(':TRIGger:EDGE:LEVel 1.5')
    scope.write(':TRIGger:SWEep NORMal')
    scope.write(':ACQuire:TYPE HRESolution')
    scope.write(':WAVeform:SOURce CHAN1')
    scope.write(':WAVeform:FORMat BYTE')
    scope.write(':WAVeform:POINts:MODE RAW')
    scope.write(f':WAVeform:POINts {REQUESTED_POINTS}')
    time.sleep(0.5)

def capture_trace(scope):
    scope.write(':SINGle')
    scope.query('*OPC?')
    preamble = scope.query(':WAVeform:PREamble?').split(',')
    y_inc = float(preamble[7]); y_orig = float(preamble[8]); y_ref = float(preamble[9])
    raw = scope.query_binary_values(':WAVeform:DATA?', datatype='B', container=np.array)
    volts = (raw - y_ref) * y_inc + y_orig
    time.sleep(0.01)
    return volts.astype(np.float32)

def open_scope_with_retry(rm, max_attempts=5):
    for attempt in range(max_attempts):
        try:
            scope = rm.open_resource(SCOPE_ADDR)
            scope.timeout = 10000
            scope.clear()
            _ = scope.query('*IDN?')
            return scope
        except Exception as e:
            print(f"  open attempt {attempt+1} failed: {e}")
            time.sleep(2)
    raise RuntimeError("Couldn't open scope after retries")

def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    print(f"Generating {N_TRACES} plaintexts...")
    plaintexts = generate_plaintexts(N_TRACES)
    
    rm = pyvisa.ResourceManager()
    scope = open_scope_with_retry(rm)
    print("Connected:", scope.query('*IDN?').strip())
    configure_scope(scope)
    
    print("\nCapturing first trace to determine size...")
    first_trace = capture_trace(scope)
    actual_points = len(first_trace)
    print(f"Scope returns {actual_points} points per trace")
    
    traces = np.zeros((N_TRACES, actual_points), dtype=np.float32)
    traces[0] = first_trace
    
    print(f"\nCapturing {N_TRACES} traces (saving every {SAVE_EVERY})...")
    t0 = time.time()
    last_saved = 0
    
    for i in range(1, N_TRACES):
        success = False
        for attempt in range(3):
            try:
                trace = capture_trace(scope)
                if len(trace) >= actual_points:
                    traces[i] = trace[:actual_points]
                else:
                    traces[i, :len(trace)] = trace
                success = True
                break
            except Exception as e:
                print(f"\n  [trace {i}] attempt {attempt+1} error: {e}")
                time.sleep(1)
                try:
                    scope.close()
                except: pass
                try:
                    scope = open_scope_with_retry(rm)
                    configure_scope(scope)
                except Exception as e2:
                    print(f"  reopen failed: {e2}")
                    time.sleep(3)
        
        if not success:
            print(f"\n  [trace {i}] skipped after retries")
            continue
        
        # Save periodically
        if (i + 1) % SAVE_EVERY == 0:
            np.save(os.path.join(OUTPUT_DIR, 'traces.npy'), traces[:i+1])
            np.save(os.path.join(OUTPUT_DIR, 'plaintexts.npy'), plaintexts[:i+1])
            last_saved = i + 1
            elapsed = time.time() - t0
            rate = (i + 1) / elapsed
            eta = (N_TRACES - i - 1) / rate if rate > 0 else 0
            print(f"  Trace {i+1}/{N_TRACES}  ({rate:.2f}/s, ETA: {eta:.0f}s, saved)")
    
    # Final save
    np.save(os.path.join(OUTPUT_DIR, 'traces.npy'), traces)
    np.save(os.path.join(OUTPUT_DIR, 'plaintexts.npy'), plaintexts)
    
    elapsed = time.time() - t0
    print(f"\nDone: {N_TRACES} traces in {elapsed:.1f}s")
    
    try:
        scope.write(':RUN')
        scope.close()
    except: pass

if __name__ == '__main__':
    main()