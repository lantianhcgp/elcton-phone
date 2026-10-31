import subprocess, time
end=time.monotonic()+10
while time.monotonic()<end:
    if subprocess.run(['xdpyinfo','-display',':99'],capture_output=True).returncode == 0:
        break
    time.sleep(.1)
else:
    raise SystemExit('X display unavailable')
