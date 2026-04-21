import pyvisa
import numpy as np
import matplotlib.pyplot as plt

SCOPE_ADDR = 'USB0::0x2A8D::0x17BC::MY65060111::0::INSTR'

rm = pyvisa.ResourceManager()
scope = rm.open_resource(SCOPE_ADDR)
scope.timeout = 15000

print("Connected:", scope.query('*IDN?').strip())

# ===== Configure scope =====
# Timebase: 2 ms/div → 20 ms total window
scope.write(':TIMebase:SCALe 0.002')
scope.write(':TIMebase:POSition 0.008')  # trigger near left edge

# CH1: AC coupling, sensitive for power measurement
scope.write(':CHANnel1:DISPlay ON')
scope.write(':CHANnel1:COUPling AC')
scope.write(':CHANnel1:SCALe 0.010')       # 10 mV/div
scope.write(':CHANnel1:BWLimit ON')
scope.write(':CHANnel1:PROBe 10')          # 10:1 probe

# CH2: DC coupling, logic level
scope.write(':CHANnel2:DISPlay ON')
scope.write(':CHANnel2:COUPling DC')
scope.write(':CHANnel2:SCALe 1.0')         # 1 V/div
scope.write(':CHANnel2:OFFSet 1.5')        # center at 1.5V
scope.write(':CHANnel2:PROBe 1')

# Trigger: CH2 rising edge
scope.write(':TRIGger:MODE EDGE')
scope.write(':TRIGger:EDGE:SOURce CHAN2')
scope.write(':TRIGger:EDGE:SLOPe POSitive')
scope.write(':TRIGger:EDGE:LEVel 1.5')
scope.write(':TRIGger:SWEep NORMal')

# Use High-Resolution mode (NOT averaging — averaging breaks CH2)
scope.write(':ACQuire:TYPE HRESolution')

def get_waveform(channel):
    scope.write(f':WAVeform:SOURce CHAN{channel}')
    scope.write(':WAVeform:FORMat BYTE')
    scope.write(':WAVeform:POINts:MODE RAW')
    scope.write(':WAVeform:POINts 20000')
    
    preamble = scope.query(':WAVeform:PREamble?').split(',')
    x_inc = float(preamble[4]); x_orig = float(preamble[5])
    y_inc = float(preamble[7]); y_orig = float(preamble[8]); y_ref = float(preamble[9])
    
    raw = scope.query_binary_values(':WAVeform:DATA?', datatype='B', container=np.array)
    volts = (raw - y_ref) * y_inc + y_orig
    time  = np.arange(len(raw)) * x_inc + x_orig
    return time, volts

# ===== Single-shot capture =====
print("Arming scope... waiting for trigger...")
scope.write(':SINGle')
scope.query('*OPC?')
print("Captured!")

t1, v1 = get_waveform(1)
t2, v2 = get_waveform(2)

# Plot
fig, (ax1, ax2) = plt.subplots(2, 1, sharex=True, figsize=(12, 6))

ax1.plot(t1 * 1e3, v1 * 1000, 'b-', linewidth=0.5)
ax1.set_ylabel('CH1 Power (mV)')
ax1.set_title('Power trace (shunt resistor)')
ax1.grid(True)

ax2.plot(t2 * 1e3, v2, 'r-', linewidth=1)
ax2.set_ylabel('CH2 Trigger (V)')
ax2.set_xlabel('Time (ms)')
ax2.set_title('Trigger signal (PB0)')
ax2.grid(True)

plt.tight_layout()
plt.show()

print(f"CH1: min={v1.min()*1000:.2f} mV, max={v1.max()*1000:.2f} mV, std={v1.std()*1000:.2f} mV")
print(f"CH2: min={v2.min():.2f} V,   max={v2.max():.2f} V")

scope.close()
