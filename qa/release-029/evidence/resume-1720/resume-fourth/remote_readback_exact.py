#!/usr/bin/env python3
"""Streaming exact external tarball readback, including literal Git evidence symlinks.
No extraction or symlink following. All rows must match the exact local Git tree.
"""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import subprocess
import tarfile


def tree_rows(sha):
    raw = subprocess.check_output(['git', 'ls-tree', '-r', '-z', sha])
    expected = {}
    for row in raw.split(b'\0'):
        if not row:
            continue
        meta, encoded = row.split(b'\t', 1)
        mode, kind, oid = meta.decode().split()
        path = encoded.decode()
        assert kind == 'blob' and mode in ('100644', '100755', '120000'), 'Unexpected Git object kind/mode'
        assert path not in expected
        expected[path] = {'mode': mode, 'oid': oid}
    return expected


def compare_archive(archive, expected, get_blob):
    seen = set()
    result = {}
    prefix = None
    for member in archive:
        name = PurePosixPath(member.name)
        assert not name.is_absolute() and '..' not in name.parts and name.parts, 'Unsafe tarball path'
        if prefix is None:
            prefix = name.parts[0]
        assert name.parts[0] == prefix, 'More than one archive root'
        if member.isdir():
            continue
        assert len(name.parts) >= 2
        relative = PurePosixPath(*name.parts[1:]).as_posix()
        assert relative in expected and relative not in seen, 'Missing/unexpected/duplicate member: ' + relative
        row = expected[relative]
        local = get_blob(row['oid'])
        if row['mode'] == '120000':
            assert member.issym() and not member.islnk(), 'Evidence symlink Git mode not preserved'
            remote = member.linkname.encode('utf-8')
            assert remote == local, 'Literal evidence symlink payload differs: ' + relative
        else:
            assert member.isfile() and not member.issym() and not member.islnk(), 'Ordinary blob became a link'
            stream = archive.extractfile(member)
            assert stream is not None
            remote = stream.read()
            assert remote == local and len(remote) == member.size, 'Remote/local bytes differ: ' + relative
        result[relative] = {'bytes': len(local), 'sha256': hashlib.sha256(local).hexdigest(),
                            'git_blob': row['oid'], 'git_mode': row['mode'],
                            'scope': 'literal link target only, never followed' if row['mode'] == '120000' else 'exact ordinary blob'}
        seen.add(relative)
    assert seen == set(expected), 'Incomplete remote archive'
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--sha', required=True)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--cache', type=Path, required=True)
    args = parser.parse_args()
    assert len(args.sha) == 40 and all(c in '0123456789abcdef' for c in args.sha), 'Invalid SHA token'
    repo = 'lantianhcgp/elcton-phone'
    out = args.out
    out.mkdir(parents=True, exist_ok=False)
    args.cache.parent.mkdir(parents=True, exist_ok=True)
    branch = json.loads(subprocess.check_output(['gh', 'api', 'repos/' + repo + '/branches/release%2F0.2.9-20261114']))
    assert branch['commit']['sha'] == args.sha, 'External branch does not point to target SHA'
    expected = tree_rows(args.sha)
    with args.cache.open('xb') as stream:
        fetched = subprocess.run(['gh', 'api', 'repos/' + repo + '/tarball/' + args.sha],
                                 stdout=stream, stderr=subprocess.PIPE, timeout=240)
    (out / 'download.stderr.bin').open('xb').write(fetched.stderr)
    (out / 'download.exit').open('x').write(str(fetched.returncode) + '\n')
    fetched.check_returncode()
    with tarfile.open(args.cache, 'r|gz') as archive:
        rows = compare_archive(archive, expected,
                               lambda oid: subprocess.check_output(['git', 'cat-file', 'blob', oid]))
    with args.cache.open('rb') as stream:
        digest = hashlib.file_digest(stream, 'sha256').hexdigest()
    report = {'passed': True, 'source_sha': args.sha, 'remote_branch_sha': branch['commit']['sha'],
              'scope': 'Independent exact external tarball; ALL Git source/test/config/raw evidence bytes and literal evidence symlink payloads; no omissions, links never followed',
              'files': len(rows), 'tracked_bytes': sum(row['bytes'] for row in rows.values()),
              'symlink_payloads': sum(row['git_mode'] == '120000' for row in rows.values()),
              'remote_archive_bytes': args.cache.stat().st_size, 'remote_archive_sha256': digest, 'rows': rows}
    (out / 'all-files-readback.json').open('x').write(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({k: v for k, v in report.items() if k != 'rows'}, ensure_ascii=False), flush=True)


if __name__ == '__main__':
    main()
