#!/usr/bin/env python3
"""Credential audit of exact git payload bytes, including deliberate probe symlinks."""
import argparse
import hashlib
import io
import json
import os
from pathlib import Path
import re
import stat
import subprocess
from urllib.parse import urlsplit
import zipfile

p = argparse.ArgumentParser()
p.add_argument('--out', required=True)
a = p.parse_args()
root = Path.cwd()
known = set()
credentials = Path.home() / '.git-credentials'
if credentials.is_file():
    for line in credentials.read_text().splitlines():
        password = urlsplit(line).password
        if password and len(password) >= 12:
            known.add(password.encode())
env = Path.home() / '.hermes/.env'
if env.is_file():
    for line in env.read_text().splitlines():
        key, sep, value = line.partition('=')
        if sep and re.search(r'(?:KEY|TOKEN|PASSWORD|SECRET)', key) and len(value.strip()) >= 12:
            value = value.strip().strip('\"\'')
            if value and not value.startswith(('http://', 'https://')):
                known.add(value.encode())
patterns = [
    ('github-token', re.compile(rb'ghp_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{30,}')),
    ('api-token', re.compile(rb'sk-[A-Za-z0-9_-]{24,}')),
    ('private-key', re.compile(rb'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----')),
]
tracked = subprocess.check_output(['git', 'ls-files', '-z'])
new = subprocess.check_output(['git', 'ls-files', '--others', '--exclude-standard', '-z'])
names = sorted({s.decode() for s in (tracked + new).split(b'\0') if s})
hits, rows, links = [], {}, []
archives = 0

def scan(raw, name):
    found = set()
    if any(value in raw for value in known):
        found.add('exact-known-secret')
    for kind, pattern in patterns:
        if pattern.search(raw):
            found.add(kind)
    if found:
        hits.append({'path': name, 'categories': sorted(found)})

for name in names:
    file = root / name
    mode = file.lstat().st_mode
    if stat.S_ISLNK(mode):
        # Git stores the link text, not the target; never read outside the worktree.
        assert name.startswith('qa/release-029/evidence/'), 'Source symlink outside approved probe evidence'
        raw = os.readlink(file).encode()
        links.append({'path': name, 'payload_bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()})
    else:
        assert stat.S_ISREG(mode), 'Not an ordinary Git payload file: ' + name
        raw = file.read_bytes()
    scan(raw, name)
    rows[name] = {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}
    if not stat.S_ISLNK(mode) and file.suffix in ('.apk', '.jar', '.zip') and zipfile.is_zipfile(io.BytesIO(raw)):
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            for entry in archive.infolist():
                if not entry.is_dir():
                    scan(archive.read(entry), name + '::' + entry.filename)
        archives += 1
report = {'passed': not hits, 'scope': 'All current git tracked/untracked-not-ignored actual ordinary files, archive entries and literal symlink payloads; original exact known/pattern checks unchanged; never follow probe symlinks or print values',
          'files': len(rows), 'bytes': sum(x['bytes'] for x in rows.values()), 'archives_scanned': archives,
          'hits': hits, 'probe_symlinks': links,
          'file_manifest_sha256': hashlib.sha256(json.dumps(rows, sort_keys=True, separators=(',', ':')).encode()).hexdigest()}
with Path(a.out).open('x') as file:
    json.dump(report, file, indent=2)
    file.write('\n')
print(json.dumps(report), flush=True)
raise SystemExit(0 if report['passed'] else 1)
