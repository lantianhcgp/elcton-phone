from pathlib import Path
import subprocess, sys
apks=list(Path('incoming').rglob('elcton-phone-probe.apk'))
assert len(apks)==1,apks
subprocess.run(['adb','install','-r',str(apks[0])],check=True)
subprocess.run([sys.executable,'qa/emulator_tour.py'],check=True)
