#!/usr/bin/env python3
"""Retry only identical original read-only transport; keep every original gate."""
import hashlib
import json
from pathlib import Path
import runpy
import sys
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
SOURCE = 'a0881bf7c1d97724ea166f0e51988902c280a5cc'

def main():
    args = sys.argv[1:]
    assert args and args[0] in ('wait', 'readback', 'fetch'), 'Read-only subcommand required, no dispatch/POST'
    import subprocess
    for name in ('pipeline.py', 'r6_common.py'):
        path = HERE / name
        committed = subprocess.check_output(['git', 'show', SOURCE + ':' + str(path.relative_to(ROOT))], cwd=ROOT)
        assert path.read_bytes() == committed, 'Original helper bytes changed'
    assert '--out' in args
    output = Path(args[args.index('--out') + 1]).absolute()
    assert '..' not in output.parts and output.is_relative_to(HERE) and output != HERE
    assert not any(p.is_symlink() for p in (output, *output.parents)) and not output.exists()
    # This log is a sibling, so original new_out still owns its own exclusive directory.
    transport = output.with_name(output.name + '.transport.jsonl')
    assert not transport.exists()
    stream = transport.open('x')
    sys.path.insert(0, str(HERE))
    import r6_common
    original_api = r6_common.api
    def get_with_retry(path, payload=None):
        assert payload is None, 'Read-only wrapper refuses POST payload'
        for attempt in range(1, 7):
            try:
                result = original_api(path, None)
                stream.write(json.dumps({'path': path, 'attempt': attempt, 'success': True, 'at': time.time()}) + '\n')
                stream.flush()
                return result
            except (AssertionError, subprocess.TimeoutExpired, json.JSONDecodeError) as error:
                stream.write(json.dumps({'path': path, 'attempt': attempt, 'success': False, 'error_type': type(error).__name__, 'at': time.time(), 'credential_values_not_stored': True}) + '\n')
                stream.flush()
                if attempt == 6:
                    raise
                time.sleep(min(attempt * 2, 10))
    r6_common.api = get_with_retry
    # r6_common.pages/exact_readback use the same globals, every identity gate unchanged.
    sys.argv = [str(HERE / 'pipeline.py'), *args]
    try:
        runpy.run_path(str(HERE / 'pipeline.py'), run_name='__main__')
    finally:
        stream.close()

if __name__ == '__main__':
    main()
