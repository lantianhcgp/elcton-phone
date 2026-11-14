#!/usr/bin/env python3
"""Cloud-only best-effort observation; original child runs once and keeps its exit.

Observer I/O never decides Android acceptance, retries the child, or modifies a device.
"""
import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import signal
import stat
import subprocess
import sys
import threading
import time

OBSERVER_JOIN_SECONDS = 1.0
CRASH_FILE_LIMIT = 32 * 1024 * 1024
CRASH_TOTAL_LIMIT = 64 * 1024 * 1024
CRASH_SCAN_LIMIT = 256
CRASH_COPY_LIMIT = 64
CRASH_DEPTH_LIMIT = 8
CRASH_INDEX_LIMIT = 32768


def verify_cloud_emulator():
    if os.environ.get('GITHUB_ACTIONS') != 'true' or os.environ.get('CI') != 'true':
        raise RuntimeError('This observer runs only on a GitHub cloud runner')
    result = subprocess.run(['adb', 'devices'], capture_output=True, text=True, check=True, timeout=20)
    connected = [line.split() for line in result.stdout.splitlines()[1:] if line.strip()]
    if len(connected) != 1 or len(connected[0]) != 2:
        raise RuntimeError('Expected exactly one verified emulator')
    serial, state = connected[0]
    if re.fullmatch(r'emulator-[0-9]+', serial) is None or state != 'device':
        raise RuntimeError('Physical or unready device is forbidden')
    return serial


def proc_snapshot():
    result = {'time': datetime.datetime.now(datetime.timezone.utc).isoformat(),
              'monotonic': time.monotonic(), 'emulator_processes': []}
    result['meminfo'] = Path('/proc/meminfo').read_text()
    for entry in Path('/proc').iterdir():
        if not entry.name.isdecimal():
            continue
        try:
            comm = (entry / 'comm').read_text().strip()
            cmdline = (entry / 'cmdline').read_bytes().split(b'\0')
            executable = os.path.basename(cmdline[0].decode(errors='replace')) if cmdline else ''
            if comm.startswith(('qemu-system', 'emulator')) or executable.startswith(('qemu-system', 'emulator')):
                result['emulator_processes'].append({'pid': int(entry.name), 'comm': comm,
                                                     'status': (entry / 'status').read_text(),
                                                     'oom_score': (entry / 'oom_score').read_text().strip()})
        except (OSError, ValueError, IndexError):
            continue
    for name in ('memory.current', 'memory.max', 'memory.events', 'memory.peak'):
        file = Path('/sys/fs/cgroup') / name
        if file.is_file():
            result[name] = file.read_text()
    result['console_ports'] = []
    for name in ('/proc/net/tcp', '/proc/net/tcp6'):
        for row in Path(name).read_text().splitlines()[1:]:
            parts = row.split()
            if len(parts) > 3 and parts[1].split(':')[-1] in ('15B2', '15B3'):
                result['console_ports'].append({'local_address': parts[1], 'state': parts[3]})
    return result


def capture_kernel(output):
    result = subprocess.run(['sudo', '-n', 'dmesg', '-T'], capture_output=True, timeout=20)
    with (output / 'kernel-final.stdout.bin').open('xb') as file:
        file.write(result.stdout)
    with (output / 'kernel-final.stderr.bin').open('xb') as file:
        file.write(result.stderr)
    with (output / 'kernel-final.exit').open('x') as file:
        file.write(str(result.returncode) + '\n')


def open_directories(root_fd, parts):
    """Open only real directories below a pinned directory handle, never symlinks."""
    current = os.dup(root_fd)
    try:
        for name in parts:
            if name in ('', '.', '..') or '/' in name:
                raise ValueError('Invalid relative crash-data component')
            try:
                os.mkdir(name, mode=0o700, dir_fd=current)
            except FileExistsError:
                pass
            following = os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=current)
            os.close(current)
            current = following
        return current
    except Exception:
        os.close(current)
        raise


def open_existing_directory(path):
    """Pin every existing component from /; NOFOLLOW on the leaf alone is insufficient."""
    raw = os.fspath(path)
    if not os.path.isabs(raw):
        raw = os.path.join(os.getcwd(), raw)
    parts = raw.split('/')
    if '..' in parts:
        raise ValueError('Parent traversal in crash-data root')
    components = [name for name in parts if name not in ('', '.')]
    if not components:
        raise ValueError('Filesystem root is not a crash-data leaf')
    # O_PATH needs no ancestor read permission (Android denies reading /), while
    # every relative open still checks search permissions and refuses symlinks.
    search_mode = getattr(os, 'O_PATH')
    current = os.open('/', search_mode | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        for number, name in enumerate(components):
            mode = os.O_RDONLY if number == len(components) - 1 else search_mode
            following = os.open(name, mode | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=current)
            os.close(current)
            current = following
        return current
    except BaseException:
        os.close(current)
        raise


def write_pinned_json(directory_fd, name, value, limit):
    """Create one bounded new leaf below the pinned output, never a lexical re-open."""
    raw = (json.dumps(value, ensure_ascii=True, separators=(',', ':')) + '\n').encode('utf-8')
    if len(raw) > limit:
        raise OSError('Crash-data JSON exceeded bound')
    fd = os.open(name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=directory_fd)
    with os.fdopen(fd, 'wb') as file:
        file.write(raw)


def capture_crashdata(output):
    """Bounded lazy traversal; source ancestors, output and index use pinned handles."""
    copied = []
    budget = {'scanned_entries': 0, 'copied_files': 0, 'content_bytes': 0,
              'max_depth': 0, 'stopped_reason': None,
              'limits': {'scan': CRASH_SCAN_LIMIT, 'copy': CRASH_COPY_LIMIT,
                         'depth': CRASH_DEPTH_LIMIT, 'index_bytes': CRASH_INDEX_LIMIT,
                         'file_bytes': CRASH_FILE_LIMIT, 'total_bytes': CRASH_TOTAL_LIMIT}}
    source_fd = None
    destination_fd = None
    output_fd = open_existing_directory(output)
    try:
        try:
            source_fd = open_existing_directory(Path('/tmp/android-runner'))
        except FileNotFoundError:
            budget['stopped_reason'] = 'source-absent'
        if source_fd is not None:
            destination_fd = open_directories(output_fd, ['emulator-crashdata'])

            def exhausted(reason):
                budget['stopped_reason'] = reason
                return True

            def walk(directory_fd, prefix=()):
                with os.scandir(directory_fd) as entries:
                    for entry in entries:
                        if budget['scanned_entries'] >= CRASH_SCAN_LIMIT:
                            return exhausted('scan-limit')
                        if budget['copied_files'] >= CRASH_COPY_LIMIT:
                            return exhausted('copy-limit')
                        budget['scanned_entries'] += 1
                        name = entry.name
                        if name in ('', '.', '..') or '/' in name:
                            continue
                        info = os.stat(name, dir_fd=directory_fd, follow_symlinks=False)
                        if stat.S_ISLNK(info.st_mode):
                            continue
                        if stat.S_ISDIR(info.st_mode):
                            if len(prefix) >= CRASH_DEPTH_LIMIT:
                                return exhausted('depth-limit')
                            following = os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
                                                dir_fd=directory_fd)
                            try:
                                budget['max_depth'] = max(budget['max_depth'], len(prefix) + 1)
                                if walk(following, prefix + (name,)):
                                    return True
                            finally:
                                os.close(following)
                            continue
                        allowed = name.startswith('emu-crash-') or name.endswith('.dmp')
                        if not stat.S_ISREG(info.st_mode) or not allowed or info.st_nlink != 1:
                            continue
                        if info.st_size > CRASH_FILE_LIMIT:
                            return exhausted('file-limit')
                        if budget['content_bytes'] + info.st_size > CRASH_TOTAL_LIMIT:
                            return exhausted('total-limit')
                        relative = prefix + (name,)
                        # Reserve index capacity before any source read or destination copy.
                        reserved = {'path': '/'.join(relative), 'bytes': CRASH_FILE_LIMIT,
                                    'sha256': '0' * 64}
                        index_size = len((json.dumps(copied + [reserved], ensure_ascii=True,
                                                     separators=(',', ':')) + '\n').encode('utf-8'))
                        if index_size > CRASH_INDEX_LIMIT:
                            return exhausted('index-limit')
                        fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=directory_fd)
                        try:
                            current = os.fstat(fd)
                            if (not stat.S_ISREG(current.st_mode) or current.st_nlink != 1
                                    or (current.st_dev, current.st_ino) != (info.st_dev, info.st_ino)):
                                raise OSError('Crash-data source changed during safe open')
                            remaining = CRASH_TOTAL_LIMIT - budget['content_bytes']
                            read_limit = min(CRASH_FILE_LIMIT, remaining)
                            with os.fdopen(fd, 'rb', closefd=False) as src:
                                raw = src.read(read_limit + 1)
                            if len(raw) > read_limit:
                                return exhausted('total-limit' if remaining < CRASH_FILE_LIMIT else 'file-limit')
                            parent_fd = open_directories(destination_fd, prefix)
                            try:
                                target_fd = os.open(name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                                                    0o600, dir_fd=parent_fd)
                                with os.fdopen(target_fd, 'wb') as dest:
                                    dest.write(raw)
                            finally:
                                os.close(parent_fd)
                            budget['content_bytes'] += len(raw)
                            budget['copied_files'] += 1
                            copied.append({'path': '/'.join(relative), 'bytes': len(raw),
                                           'sha256': hashlib.sha256(raw).hexdigest()})
                        finally:
                            os.close(fd)
                return False

            walk(source_fd)
        write_pinned_json(output_fd, 'crashdata-index.json', copied, CRASH_INDEX_LIMIT)
        write_pinned_json(output_fd, 'crashdata-budget.json', budget, 4096)
    finally:
        if destination_fd is not None:
            os.close(destination_fd)
        if source_fd is not None:
            os.close(source_fd)
        os.close(output_fd)


def run_child(command, output, interval=1.0):
    output = Path(output)
    stop = threading.Event()
    errors = []
    enabled = True
    try:
        output.mkdir(parents=True, exist_ok=False)
    except Exception as error:
        enabled = False
        errors.append({'capture': 'directory', 'type': type(error).__name__})

    def sample():
        try:
            with (output / 'samples.jsonl').open('x') as file:
                while not stop.is_set():
                    try:
                        row = proc_snapshot()
                    except Exception as error:
                        row = {'observation_error': type(error).__name__}
                    if stop.is_set():
                        break
                    file.write(json.dumps(row) + '\n')
                    file.flush()
                    stop.wait(interval)
        except Exception as error:
            errors.append({'capture': 'sampler', 'type': type(error).__name__})

    sampler = None
    if enabled:
        try:
            # A stuck diagnostic cannot prevent interpreter exit. Normal runs join cleanly.
            sampler = threading.Thread(target=sample, name='cloud-emulator-evidence', daemon=True)
            sampler.start()
        except Exception as error:
            sampler = None
            errors.append({'capture': 'sampler-start', 'type': type(error).__name__})
    child = None
    try:
        # Preserve the original full process execution even when any observer setup failed.
        child = subprocess.Popen(command)
        code = child.wait()
    finally:
        stop.set()
        if sampler is not None:
            try:
                sampler.join(OBSERVER_JOIN_SECONDS)
            except Exception as error:
                errors.append({'capture': 'sampler-join', 'type': type(error).__name__})

    def finish():
        for capture in (capture_kernel, capture_crashdata):
            try:
                capture(output)
            except Exception as error:
                errors.append({'capture': capture.__name__, 'type': type(error).__name__})
        receipt = {'returncode': code, 'passed': code == 0, 'pid': child.pid,
                   'sampler_stopped': sampler is None or not sampler.is_alive(), 'observer_errors': list(errors),
                   'scope': 'child exit only; NOT Android acceptance; observation may fail independently; no child retries/device changes'}
        try:
            with (output / 'child-exit.json').open('x') as file:
                json.dump(receipt, file, indent=2)
                file.write('\n')
        except Exception:
            pass  # Receipt I/O failure cannot replace the actual child's exit.
    if enabled:
        try:
            finalizer = threading.Thread(target=finish, name='cloud-emulator-evidence-finalize', daemon=True)
            finalizer.start()
            finalizer.join(OBSERVER_JOIN_SECONDS)
        except Exception:
            pass
    return code


def exit_like_child(code):
    if code < 0:
        # Popen's negative native signal must remain a signal, not sys.exit(-N) modulo256.
        number = -code
        if number not in (signal.SIGKILL, signal.SIGSTOP):
            signal.signal(number, signal.SIG_DFL)
        os.kill(os.getpid(), number)
        raise SystemExit(128 + number)  # Unreachable under normal POSIX delivery.
    raise SystemExit(code)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('command', nargs=argparse.REMAINDER)
    args = parser.parse_args()
    verify_cloud_emulator()
    command = args.command[1:] if args.command[:1] == ['--'] else args.command
    expected = [sys.executable, 'qa/emulator_install_and_tour.py']
    if command != expected and command != ['python3', 'qa/emulator_install_and_tour.py']:
        raise RuntimeError('Only the exact unchanged full-suite entrypoint is permitted')
    exit_like_child(run_child(command, Path('qa-evidence/cloud-observer')))


if __name__ == '__main__':
    main()
