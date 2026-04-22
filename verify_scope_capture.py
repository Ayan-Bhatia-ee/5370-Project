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

# Let scope auto-configure via Auto Scale
scope.write(':AUToscale')
time.sleep(3)  # wait for auto scale to settle

print("\nAuto Scale complete. Now checking state...")
print(f"  CH1 scale: {scope.query(':CHANnel1:SCALe?').strip()}")
print(f"  CH1 coupling: {scope.query(':CHANnel1:COUPling?').strip()}")
print(f"  CH2 scale: {scope.query(':CHANnel2:SCALe?').strip()}")
print(f"  Timebase: {scope.query(':TIMebase:SCALe?').strip()}")
print(f"  Sample rate: {float(scope.query(':ACQuire:SRATe?').strip())/1e6:.1f} MSa/s")
print(f"  Trigger source: {scope.query(':TRIGger:EDGE:SOURce?').strip()}")

# Now manually set CH1 to AC and proper sensitivity
scope.write(':CHANnel1:COUPling AC')
scope.write(':CHANnel1:SCALe 0.020')
scope.write(':CHANnel1:BWLimit OFF')

# Trigger on CH2
scope.write(':TRIGger:MODE EDGE')
scope.write(':TRIGger:EDGE:SOURce CHAN2')
scope.write(':TRIGger:EDGE:SLOPe POSitive')
scope.write(':TRIGger:EDGE:LEVel 1.5')
scope.write(':TRIGger:SWEep NORMal')

# Zoom in to first round
scope.write(':TIMebase:SCALe 0.00005')
scope.write(':TIMebase:POSition 0.00020')

scope.write(':ACQuire:TYPE NORMal')
time.sleep(1)

# Verify
print("\nAfter configuration:")
print(f"  CH1 scale: {float(scope.query(':CHANnel1:SCALe?').strip())*1000:.1f} mV/div")
print(f"  CH1 coupling: {scope.query(':CHANnel1:COUPling?').strip()}")
print(f"  Timebase: {float(scope.query(':TIMebase:SCALe?').strip())*1e6:.1f} µs/div")
print(f"  Sample rate: {float(scope.query(':ACQuire:SRATe?').strip())/1e6:.1f} MSa/s")

# Single capture
scope.write(':WAVeform:SOURce CHAN1')
scope.write(':WAVeform:FORMat BYTE')
scope.write(':WAVeform:POINts:MODE RAW')
scope.write(':WAVeform:POINts MAX')

print("\nArming...")
scope.write(':SINGle')
scope.query('*OPC?')
print("Captured!")

preamble = scope.query(':WAVeform:PREamble?').split(',')
y_inc = float(preamble[7]); y_orig = float(preamble[8]); y_ref = float(preamble[9])
x_inc = float(preamble[4])

raw = scope.query_binary_values(':WAVeform:DATA?', datatype='B', container=np.array)
print(f"Got {len(raw)} points")
print(f"Raw byte min={raw.min()}, max={raw.max()}, std={raw.std():.1f}")
print(f"  (if std < 10, something is wrong — should be 30-100)")

volts = (raw - y_ref) * y_inc + y_orig
print(f"Voltage: min={volts.min()*1000:.2f} mV, max={volts.max()*1000:.2f} mV")

# Also grab CH2
scope.write(':WAVeform:SOURce CHAN2')
raw2 = scope.query_binary_values(':WAVeform:DATA?', datatype='B', container=np.array)
pre2 = scope.query(':WAVeform:PREamble?').split(',')
y_inc2 = float(pre2[7]); y_orig2 = float(pre2[8]); y_ref2 = float(pre2[9])
volts2 = (raw2 - y_ref2) * y_inc2 + y_orig2

fig, (a1, a2) = plt.subplots(2, 1, sharex=True, figsize=(14, 6))
t = np.arange(len(volts)) * x_inc * 1e6
a1.plot(t, volts * 1000, 'b-', linewidth=0.5)
a1.set_ylabel('CH1 Power (mV)')
a1.grid(True)

a2.plot(np.arange(len(volts2)) * x_inc * 1e6, volts2, 'r-', linewidth=1)
a2.set_ylabel('CH2 Trigger (V)')
a2.set_xlabel('Time (µs)')
a2.grid(True)

plt.tight_layout()
plt.show()

scope.write(':RUN')
scope.close()