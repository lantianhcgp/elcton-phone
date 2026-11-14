#!/usr/bin/env python3
"""Same exact all-blob comparator over a hashed stream; no extra 330MB download on phone.
The original compare_archive/tree_rows are loaded verbatim and remain unmodified.
"""
import argparse
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import subprocess
import tarfile

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('frozen_all_blob_comparator', HERE / 'remote_readback_exact.py')
assert spec and spec.loader
M = importlib.util.module_from_spec(spec)
spec.loader.exec_module(M)


class HashedReader(io.RawIOBase):
    def __init__(self, stream):
        self.stream = stream
        self.sha = hashlib.sha256()
        self.count = 0

    def readable(self):
        return True

    def read(self, size=-1):
        value = self.stream.read(size)
        self.sha.update(value)
        self.count += len(value)
        return value


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--sha', required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    assert len(args.sha) == 40 and all(c in '0123456789abcdef' for c in args.sha)
    args.out.mkdir(parents=True, exist_ok=False)
    repo = 'lantianhcgp/elcton-phone'
    branch = json.loads(subprocess.check_output(['gh', 'api', 'repos/' + repo + '/branches/release%2F0.2.9-20261114'], timeout=60))
    assert branch['commit']['sha'] == args.sha
    expected = M.tree_rows(args.sha)
    command = ['gh', 'api', 'repos/' + repo + '/tarball/' + args.sha]
    with (args.out / 'download.stderr.bin').open('xb') as errors:
        child = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=errors)
        assert child.stdout is not None
        stream = HashedReader(child.stdout)
        try:
            with tarfile.open(fileobj=stream, mode='r|gz') as archive:
                rows = M.compare_archive(archive, expected,
                                         lambda oid: subprocess.check_output(['git', 'cat-file', 'blob', oid]))
            # Tar EOF can precede transport EOF; hash every actually delivered wire byte.
            while stream.read(1024 * 1024):
                pass
            code = child.wait(timeout=60)
            (args.out / 'download.exit').open('x').write(str(code) + '\n')
            assert code == 0
        finally:
            child.stdout.close()
            if child.poll() is None:
                child.terminate()
                child.wait(timeout=30)
    report = {'passed': True, 'source_sha': args.sha, 'remote_branch_sha': branch['commit']['sha'],
              'scope': 'ALL remote tarball exact Git blobs/literal evidence links, same original unmodified comparator; hashed full download stream without duplicate raw cache; no omission or following/extraction',
              'files': len(rows), 'tracked_bytes': sum(row['bytes'] for row in rows.values()),
              'symlink_payloads': sum(row['git_mode'] == '120000' for row in rows.values()),
              'remote_archive_bytes': stream.count, 'remote_archive_sha256': stream.sha.hexdigest(),
              'original_comparator_sha256': hashlib.sha256((HERE / 'remote_readback_exact.py').read_bytes()).hexdigest(),
              'rows': rows}
    (args.out / 'all-files-readback.json').open('x').write(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({k: v for k, v in report.items() if k != 'rows'}, ensure_ascii=False), flush=True)


if __name__ == '__main__':
    main()
