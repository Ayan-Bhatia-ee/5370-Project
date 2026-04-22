import pyvisa
import numpy as np
import matplotlib.pyplot as plt
import time

SCOPE_ADDR = 'USB0::0x2A8D::0x17BC::MY65060111::0::INSTR'

rm = pyvisa.ResourceManager()
scope = rm.open_resource(SCOPE_ADDR)
scope.timeout = 10000
scope.clear()

print("Connected:", scope.query('*IDN?').strip())

# Configure for AES
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
time.sleep(0.5)

# Arm for single capture
print("Arming... waiting for trigger...")
scope.write(':SINGle')

# Wait for acquisition with polling (avoid *OPC? hang)
scope.timeout = 5000
try:
    scope.query('*OPC?')
    print("Captured!")
except Exception as e:
    print(f"Trigger timeout: {e}")
    print("Going to try force trigger...")
    scope.write(':TRIGger:FORCe')
    time.sleep(1)

def get_waveform(channel):
    scope.write(f':WAVeform:SOURce CHAN{channel}')
    scope.write(':WAVeform:FORMat BYTE')
    scope.write(':WAVeform:POINts:MODE RAW')
    scope.write(':WAVeform:POINts 50000')
    
    preamble = scope.query(':WAVeform:PREamble?').split(',')
    x_inc = float(preamble[4]); x_orig = float(preamble[5])
    y_inc = float(preamble[7]); y_orig = float(preamble[8]); y_ref = float(preamble[9])
    
    raw = scope.query_binary_values(':WAVeform:DATA?', datatype='B', container=np.array)
    volts = (raw - y_ref) * y_inc + y_orig
    t = np.arange(len(raw)) * x_inc + x_orig
    return t, volts

t1, v1 = get_waveform(1)
t2, v2 = get_waveform(2)

fig, (ax1, ax2) = plt.subplots(2, 1, sharex=True, figsize=(14, 6))
ax1.plot(t1 * 1e3, v1 * 1000, 'b-', linewidth=0.5)
ax1.set_ylabel('CH1 Power (mV)')
ax1.set_title('AES-128 power trace')
ax1.grid(True)

ax2.plot(t2 * 1e3, v2, 'r-', linewidth=1)
ax2.set_ylabel('CH2 Trigger')
ax2.set_xlabel('Time (ms)')
ax2.set_title('Trigger')
ax2.grid(True)

plt.tight_layout()
plt.show()

print(f"CH1 range: {v1.min()*1000:.2f} to {v1.max()*1000:.2f} mV")
print(f"CH2 range: {v2.min():.2f} to {v2.max():.2f} V")

scope.write(':RUN')
scope.close()