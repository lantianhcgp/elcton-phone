#!/usr/bin/env python3
"""Real Android native linkat prerequisite check; preserves all small probe files."""
import ctypes
import hashlib
import json
import os
from pathlib import Path
import stat

out = Path(__file__).resolve().parent / 'r11/linkat-selfcheck'
out.mkdir(exist_ok=False)
source = out / 'original.bin'
target = out / 'snapshot.bin'
source.open('xb').write(b'actual-native-linkat-snapshot\x00\xff\n')
libc = ctypes.CDLL(None, use_errno=True)
linkat = libc.linkat
linkat.argtypes = (ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p, ctypes.c_int)
linkat.restype = ctypes.c_int
result = linkat(-100, os.fsencode(source), -100, os.fsencode(target), 0)
if result != 0:
    number = ctypes.get_errno()
    raise OSError(number, os.strerror(number))
a, b = source.stat(), target.stat()
assert stat.S_ISREG(a.st_mode) and stat.S_ISREG(b.st_mode)
assert a.st_ino == b.st_ino and a.st_dev == b.st_dev and a.st_nlink == b.st_nlink == 2
assert target.read_bytes() == source.read_bytes()
assert linkat(-100, os.fsencode(source), -100, os.fsencode(target), 0) != 0
report = {'passed': True, 'native_linkat': True, 'original_and_snapshot_inode_equal':True,
          'sha256':hashlib.sha256(source.read_bytes()).hexdigest(), 'bytes':a.st_size,
          'nlink':a.st_nlink, 'exclusive_existing_target_rejected':True,
          'python_os_link_available':hasattr(os,'link'), 'scope':'small actual native file test, no source/old evidence changed'}
(out / 'receipt.json').open('x').write(json.dumps(report,indent=2)+'\n')
print(json.dumps(report))
