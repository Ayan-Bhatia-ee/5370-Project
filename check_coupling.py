import pyvisa, time

SCOPE_ADDR = 'USB0::0x2A8D::0x17BC::MY65060111::0::INSTR'

rm = pyvisa.ResourceManager()
scope = rm.open_resource(SCOPE_ADDR)
scope.timeout = 10000
scope.clear()

print("Current CH1 coupling:", scope.query(':CHANnel1:COUPling?').strip())

# Try to set AC
scope.write(':CHANnel1:COUPling AC')
time.sleep(0.5)
print("After setting AC:", scope.query(':CHANnel1:COUPling?').strip())

scope.close()