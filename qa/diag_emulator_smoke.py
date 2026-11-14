#!/usr/bin/env python3
"""CI-only real Android 0.2.6 diagnostics acceptance; never runs adb on a phone.

python3 -B qa/diag_emulator_smoke.py            # GitHub emulator job only
python3 -B qa/diag_emulator_smoke.py --self-test # local verifier tests, NO adb
The only injected data comes from DiagnosticsUiTest and is labeled SYNTHETIC.
"""
from pathlib import Path
import argparse
import hashlib
import io
import json
import os
import re
import statistics
import subprocess
import sys
import tarfile
import time
import unittest
import uuid
import xml.etree.ElementTree as ET

PACKAGE = "com.hcbiu.elcton"
CERT = "fc08a0b474a8ffca5887bd5c88ac15e865a63a64eca81c10f344496c46d9ad94"
SHOTS = ("settings-version", "diagnostics-head", "diagnostics-tail")


def require(condition, label):
    if not condition:
        raise AssertionError(label)


def source_identity(text, head):
    # Preserve the token exactly: accept only the build's fixed one-line SHA record.
    require(re.fullmatch(r"[0-9a-f]{40}\n", text) is not None, "Malformed artifact source-sha")
    require(re.fullmatch(r"[0-9a-f]{40}", head) is not None, "Malformed checkout HEAD")
    require(text[:-1] == head, "Both APKs must come from exact checkout HEAD")
    return head


def certificate_identity(text):
    digests = re.findall(r"^Signer #\d+ certificate SHA-256 digest: ([0-9a-fA-F]{64})$", text, re.M)
    require(len(digests) == 1 and digests[0].lower() == CERT, "Actual APK signer must be fixed production certificate")
    return digests[0].lower()


def pixel_stats(image, area, step):
    left, top, right, bottom = area
    require(0 <= left < right <= image.width and 0 <= top < bottom <= image.height, "Semantic bounds outside real PNG")
    values = [sum(image.getpixel((x, y))) / 3.0 for y in range(top, bottom, step) for x in range(left, right, step)]
    return {"samples": len(values), "mean": statistics.fmean(values), "stddev": statistics.pstdev(values),
            "minimum": min(values), "maximum": max(values), "step": step}


def verify_pixels(full, target):
    require(full["mean"] > 10 and full["stddev"] > 12, "Blank or uncommitted full emulator frame")
    require(target["stddev"] > 8 and target["maximum"] - target["minimum"] > 45, "Semantic text target has no rendered pixels")


class Harness:
    def __init__(self):
        self.out = Path("qa-evidence")
        self.out.mkdir(exist_ok=True)
        self.report = {"passed": False, "scope": "real CI Android emulator; SYNTHETIC diagnostic; no paired watch", "stage": "identity"}
        self.serial = None
        self.live = None
        self.live_file = None
        self.save()

    def save(self):
        (self.out / "diag-host-report.json").write_text(json.dumps(self.report, ensure_ascii=False, indent=2) + "\n")

    def run(self, label, command, timeout=30, stdin=None, check=True):
        try:
            result = subprocess.run(command, input=stdin, capture_output=True, timeout=timeout)
            stdout, stderr, code = result.stdout, result.stderr, result.returncode
        except subprocess.TimeoutExpired as error:
            (self.out / (label + ".stdout.bin")).write_bytes(error.stdout or b"")
            (self.out / (label + ".stderr.bin")).write_bytes(error.stderr or b"")
            (self.out / (label + ".log")).write_bytes((error.stdout or b"") + (error.stderr or b"") + b"\nTIMEOUT\n")
            raise
        (self.out / (label + ".stdout.bin")).write_bytes(stdout)
        (self.out / (label + ".stderr.bin")).write_bytes(stderr)
        (self.out / (label + ".log")).write_bytes(stdout + stderr)
        if check:
            require(code == 0, label + " failed; complete output saved")
        return result

    def adb(self, label, *arguments, timeout=30, check=True):
        require(self.serial is not None and re.fullmatch(r"emulator-[0-9]+", self.serial), "Never address a physical Android device")
        return self.run(label, ["adb", "-s", self.serial, *arguments], timeout=timeout, check=check)

    def shell(self, label, command, timeout=30, check=True):
        require(self.serial is not None, "No verified CI emulator")
        return self.run(label, ["adb", "-s", self.serial, "shell"], timeout=timeout, stdin=(command + "\n").encode(), check=check)

    def harvest(self):
        result = self.adb("diag-harvest", "exec-out", "run-as", PACKAGE, "tar", "-cf", "-", "-C", "files", "qa-diag-evidence", timeout=45)
        target = self.out / "diag-product"
        target.mkdir(exist_ok=True)
        with tarfile.open(fileobj=io.BytesIO(result.stdout), mode="r:") as archive:
            for member in archive.getmembers():
                if member.isdir():
                    continue
                path = Path(member.name)
                require(member.isfile() and not path.is_absolute() and path.parts[0] == "qa-diag-evidence" and ".." not in path.parts, "Unsafe evidence archive member")
                stream = archive.extractfile(member)
                if stream is None:
                    raise AssertionError("Missing evidence archive member")
                destination = target.joinpath(*path.parts[1:])
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.write_bytes(stream.read())
        return target

    def verify_evidence(self, target, head, run_id):
        from PIL import Image
        report = json.loads((target / "report.json").read_text())
        require(report.get("passed") is True and report.get("sourceSha") == head and report.get("qaRun") == run_id, "Instrumentation receipt is not for this exact successful run")
        require(report.get("packageVersion") == "0.2.6" and report.get("packageCode") == 8, "Installed package identity")
        for key in ("activityRecreated", "fullTextUntruncated", "closeVisibleAndWorks", "androidNioHttpRead", "businessFilesUnchanged"):
            require(report.get(key) is True, "Missing real instrumentation assertion: " + key)
        expected = (target / "synthetic-expected.txt").read_bytes()
        require(hashlib.sha256(expected).hexdigest() == report["syntheticFullSha256"], "Synthetic full diagnostic digest")
        require(b"SYNTHETIC-BEGIN" in expected and b"SYNTHETIC-CAUSE" in expected and expected.endswith(b"SYNTHETIC-END"), "Evidence data must be explicitly synthetic and complete")
        require(report.get("causeCount") == 2 and len(report.get("captures", [])) == len(SHOTS), "Complete cause and screenshot coverage")
        results = []
        for name in SHOTS:
            png = target / (name + ".png")
            receipt = json.loads((target / (name + ".json")).read_text())
            require(receipt.get("pixelReady") is True and receipt.get("name") == name, "Screenshot readiness receipt")
            require(hashlib.sha256(png.read_bytes()).hexdigest() == receipt["pngSha256"], "PNG exact receipt hash")
            with Image.open(png) as raw:
                image = raw.convert("RGB")
                require([image.width, image.height] == [receipt["screenWidth"], receipt["screenHeight"]], "PNG physical dimensions")
                full = pixel_stats(image, [0, 0, image.width, image.height], 3)
                local = pixel_stats(image, receipt["targetBounds"], 1)
                verify_pixels(full, local)
                for actual, recorded in ((full, receipt["fullPixels"]), (local, receipt["targetPixels"])):
                    require(actual["samples"] == recorded["samples"] and actual["step"] == recorded["step"], "Independent pixel sample count")
                    for key in ("mean", "stddev", "minimum", "maximum"):
                        require(abs(actual[key] - recorded[key]) < 0.0001, "Independent exact PNG pixel statistics: " + key)
            nodes = list(ET.parse(target / (name + ".xml")).getroot().iter("node"))
            require(any(node.get("package") == PACKAGE for node in nodes), "Real app accessibility hierarchy missing")
            label = receipt["targetText"]
            require(any(label in node.get("text", "") for node in nodes), "Rendered semantic target not in actual app hierarchy")
            if name == "diagnostics-head":
                require(receipt["extra"]["scroll"] <= 1 and receipt["extra"]["scrollMax"] > 0, "Actual head scroll position")
            if name == "diagnostics-tail":
                require(receipt["extra"]["scroll"] >= receipt["extra"]["scrollMax"] - 1 and receipt["extra"]["scrollMax"] > 0, "Actual tail scroll position")
            results.append({"name": name, "bounds": receipt["targetBounds"], "fullPixels": full, "targetPixels": local})
        self.report["instrumentationReceipt"] = report
        self.report["independentPngChecks"] = results
        self.save()

    def business(self, label):
        command = "run-as " + PACKAGE + " sh -c " + "'for f in files/timetable.json files/timetable-last-good.json files/timetable.json.bak files/timetable-last-good.json.bak; do if test -f \"$f\"; then sha256sum \"$f\"; else printf \"ABSENT %s\\n\" \"$f\"; fi; done'"
        text = self.shell(label, command).stdout.decode().splitlines()
        require(len(text) == 4, "Incomplete business-file fingerprint")
        return sorted(text)

    def execute(self):
        # First guard is local-only. No adb, APK install or app launch may precede it.
        require(os.environ.get("GITHUB_ACTIONS") == "true" and os.environ.get("RUNNER_OS") == "Linux", "CI emulator only: refusing all local/phone adb actions")
        head = self.run("checkout-head", ["git", "rev-parse", "HEAD"]).stdout.decode().removesuffix("\n")
        main = list(Path("incoming").rglob("elcton-phone-probe.apk"))
        tests = list(Path("incoming").rglob("elcton-ui-tests.apk"))
        sources = list(Path("incoming").rglob("source-sha.txt"))
        require(len(main) == len(tests) == len(sources) == 1, "Require one exact signed main/test/source artifact set")
        source_identity(sources[0].read_bytes().decode("ascii"), head)
        require(main[0].parent == tests[0].parent == sources[0].parent, "APK/test/SHA records must share exact build dist")
        sdk = os.environ.get("ANDROID_HOME") or os.environ.get("ANDROID_SDK_ROOT")
        if not sdk:
            raise AssertionError("Android SDK required for genuine apksigner verification")
        signer = Path(sdk) / "build-tools/34.0.0/apksigner"
        require(signer.is_file(), "Missing actual Android apksigner 34.0.0")
        signatures = {}
        for label, apk in (("main", main[0]), ("tests", tests[0])):
            result = self.run(label + "-apksigner", [str(signer), "verify", "--print-certs", str(apk)], timeout=45)
            signatures[label] = certificate_identity(result.stdout.decode())
        self.report.update(sourceSha=head, apkSha256={"main": hashlib.sha256(main[0].read_bytes()).hexdigest(), "tests": hashlib.sha256(tests[0].read_bytes()).hexdigest()}, certificates=signatures)
        self.save()
        devices = self.run("adb-devices", ["adb", "devices"]).stdout.decode().splitlines()[1:]
        live = [line.split() for line in devices if line.strip()]
        require(len(live) == 1 and len(live[0]) == 2 and live[0][1] == "device" and re.fullmatch(r"emulator-[0-9]+", live[0][0]), "Refuse attached phones or multiple adb devices")
        self.serial = live[0][0]
        require(self.adb("emulator-property", "shell", "getprop", "ro.kernel.qemu").stdout.decode().strip() == "1", "Target is not actual emulator")
        navigation = os.environ.get("QA_NAVIGATION_MODE", "three-button")
        require(navigation in ("three-button", "gestural"), "Unknown navigation mode")
        overlay = "com.android.internal.systemui.navbar." + ("threebutton" if navigation == "three-button" else "gestural")
        self.shell("navigation-overlay", "cmd overlay enable-exclusive --category " + overlay)
        require("[x] " + overlay in self.shell("overlays", "cmd overlay list").stdout.decode(), "Actual navigation overlay not enabled")
        self.report.update(serial=self.serial, navigationMode=navigation, sdk=self.adb("sdk-property", "shell", "getprop", "ro.build.version.sdk").stdout.decode().strip())
        self.report["stage"] = "install-instrumentation"; self.save()
        self.adb("install-main", "install", "-r", str(main[0]), timeout=120)
        self.adb("install-tests", "install", "-r", str(tests[0]), timeout=120)
        self.shell("screen-ready", "svc power stayon true; settings put system screen_off_timeout 2147483647; input keyevent KEYCODE_WAKEUP; wm dismiss-keyguard")
        run_id = str(uuid.uuid4()); self.report["qaRun"] = run_id; self.save()
        self.live_file = (self.out / "diag-logcat-live.txt").open("wb")
        self.live = subprocess.Popen(["adb", "-s", self.serial, "logcat", "-v", "threadtime"], stdout=self.live_file, stderr=subprocess.STDOUT)
        result = self.adb("diag-instrumentation", "shell", "am", "instrument", "-w", "-r", "-e", "diag_emulator", "true", "-e", "diag_source_sha", head,
                          "-e", "diag_run", run_id, "-e", "class", PACKAGE + ".DiagnosticsUiTest", PACKAGE + ".test/androidx.test.runner.AndroidJUnitRunner", timeout=420, check=False)
        target = self.harvest()
        text = result.stdout.decode(errors="replace")
        require(result.returncode == 0 and re.search(r"OK \(1 test\)", text) and not re.search(r"FAILURES|INSTRUMENTATION_FAILED|INSTRUMENTATION_ABORTED", text), "Real diagnostic instrumentation failed; full logs/evidence retained")
        self.verify_evidence(target, head, run_id)
        self.report["stage"] = "normal-app-read-only-http"; self.save()
        # Instrumentation may finish its target process. Explicitly cold-start the actual app on emulator only.
        self.shell("normal-force-stop", "am force-stop " + PACKAGE)
        launch = self.adb("normal-launch", "shell", "am", "start", "-W", "-n", PACKAGE + "/.MainActivity", timeout=45)
        require(not re.search(r"Error:|Error type|Exception", launch.stdout.decode(errors="replace")), "Normal emulator application launch failed")
        self.adb("http-forward", "forward", "tcp:18766", "tcp:8766")
        import urllib.request
        ready = False
        deadline = time.monotonic() + 20
        while time.monotonic() < deadline:
            try:
                with urllib.request.urlopen("http://127.0.0.1:18766/health", timeout=2) as response:
                    ready = response.status == 200 and json.loads(response.read()) == {"ok": True}
                if ready:
                    break
            except (OSError, ValueError):
                pass
            time.sleep(0.2)
        require(ready, "Normal Android Application passive server health timeout")
        before = self.business("http-business-before")
        self.run("android-http-selftest", [sys.executable, "-B", "qa/mcp_http_selftest.py", "--url", "http://127.0.0.1:18766", "--adb-token", PACKAGE,
                   "--adb-token-path", "files/mcp/token", "--adb-serial", self.serial], timeout=120)
        # Prove a second actual process recovered the persisted synthetic error and both NIO files.
        sys.path.insert(0, str(Path("qa").resolve()))
        from mcp_http_selftest import Suite
        token_result = subprocess.run(["adb", "-s", self.serial, "exec-out", "run-as", PACKAGE, "cat", "files/mcp/token"], capture_output=True, timeout=10)
        require(token_result.returncode == 0 and re.fullmatch(rb"[0-9a-f]{64}", token_result.stdout), "Cold-start actual token read")
        suite = Suite("http://127.0.0.1:18766", token_result.stdout.decode("ascii"))
        expected = (target / "synthetic-expected.txt").read_text()
        failed, version = suite.call("version_info")
        require(not failed and version.get("versionName") == "0.2.6" and version.get("versionCode") == 8 and version.get("packageName") == PACKAGE, "Cold-process real version_info")
        failed, errors = suite.call("error_tail", {"limit": 1})
        require(not failed and errors["errors"][-1]["full"] == expected, "Cold-process actual persisted error_tail")
        failed, diagnostic = suite.call("diag_read")
        require(not failed and diagnostic["latestError"]["full"] == expected and diagnostic["mcp"]["running"] is True, "Cold-process actual persisted diag_read")
        for path in ("diagnostics/state.json", "diagnostics/wear-errors.jsonl"):
            failed, data = suite.call("fs_read", {"path": path})
            require(not failed and data["bytes"] == len(data["text"].encode()), "Actual Android NIO FileChannel fs_read " + path)
            decoded = json.loads(data["text"]) if path.endswith("state.json") else json.loads(data["text"].splitlines()[-1])
            require((decoded["latestError"]["full"] if path.endswith("state.json") else decoded["full"]) == expected, "Real persisted whitelist content " + path)
        require(self.business("http-business-after") == before, "Read-only HTTP must not mutate timetable")
        logs = self.adb("diag-logcat-final", "logcat", "-d", "-v", "threadtime").stdout.decode(errors="replace")
        require(not re.search(r"FATAL EXCEPTION[\s\S]{0,1500}Process: com\.hcbiu\.elcton[,\s]", logs), "App crash in actual emulator logcat")
        self.report.update(passed=True, stage="complete", normalColdProcessPersistence=True, androidNioHttpRead=True, businessFilesUnchanged=True,
                           coldHttpAssertions=suite.count, token="REDACTED")
        self.save()
        print(json.dumps({"passed": True, "sourceSha": head, "screenshots": len(SHOTS), "scope": "real emulator only; SYNTHETIC errors"}))

    def finish(self):
        if self.serial:
            try:
                self.adb("diag-final-logcat", "logcat", "-d", "-v", "threadtime", timeout=15, check=False)
                if not self.report.get("passed"):
                    self.harvest()
            except Exception as error:
                (self.out / "diag-final-harvest-error.txt").write_text(type(error).__name__ + ": " + str(error))
        if self.live:
            self.live.terminate()
            try:
                self.live.wait(timeout=10)
            except subprocess.TimeoutExpired:
                self.live.kill(); self.live.wait(timeout=5)
        if self.live_file:
            self.live_file.close()
        self.save()


class VerifierTests(unittest.TestCase):
    def test_literal_identity(self):
        sha = "a" * 40
        self.assertEqual(sha, source_identity(sha + "\n", sha))
        for value in (sha, " " + sha + "\n", sha.upper() + "\n", "b" * 40 + "\n"):
            with self.assertRaises(AssertionError):
                source_identity(value, sha)

    def test_actual_signer_gate(self):
        text = "Signer #1 certificate SHA-256 digest: " + CERT + "\n"
        self.assertEqual(CERT, certificate_identity(text))
        for value in (text.replace(CERT, "0" * 64), text + text, "", "certificate SHA-256 digest: " + CERT):
            with self.assertRaises(AssertionError):
                certificate_identity(value)

    def test_blank_and_missing_target_rejected(self):
        full = {"mean": 200, "stddev": 20}
        target = {"stddev": 15, "maximum": 240, "minimum": 20}
        verify_pixels(full, target)
        for first, second in (({"mean": 1, "stddev": 1}, target), (full, {"stddev": 0, "maximum": 200, "minimum": 200})):
            with self.assertRaises(AssertionError):
                verify_pixels(first, second)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(VerifierTests))
        return 0 if result.wasSuccessful() else 1
    harness = Harness()
    try:
        harness.execute()
        return 0
    except Exception as error:
        harness.report.update(passed=False, failure=type(error).__name__ + ": " + str(error))
        print(json.dumps({"passed": False, "stage": harness.report["stage"], "failure": harness.report["failure"]}), file=sys.stderr)
        return 1
    finally:
        harness.finish()


if __name__ == "__main__":
    sys.exit(main())
