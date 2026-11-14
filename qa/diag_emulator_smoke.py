#!/usr/bin/env python3
"""CI-only real Android 0.2.7 diagnostics acceptance; never runs adb on a phone.

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


def verify_keepalive_report(report, head, run_id, sdk):
    require(isinstance(report, dict), "Missing keepalive report object")
    require(report.get("passed") is True and report.get("sourceSha") == head and report.get("qaRun") == run_id,
            "Keepalive receipt is not for this exact successful run")
    for key in ("defaultOff", "noDefaultNotification", "onNotification", "backgroundHttp",
                "offPortClosed", "offNotificationRemoved", "businessAndTokenAndErrorsUnchanged",
                "bindFailureUiOffAndHintRetained", "startingNotActive", "activeChannelDeniedStopsAndUiOff",
                "backgroundChannelDeniedEventStops"):
        require(report.get(key) is True, "Missing real keepalive assertion: " + key)
    if sdk >= 33:
        require(report.get("permissionDeniedFailClosed") is True, "Notification denial must fail closed on API33+")
    return report


def verify_one_test(result, label):
    text = result.stdout.decode(errors="replace")
    require(result.returncode == 0 and len(re.findall(r"^OK \(1 test\)\r?$", text, re.M)) == 1
            and not re.search(r"FAILURES|INSTRUMENTATION_FAILED|INSTRUMENTATION_ABORTED", text),
            label + " failed; full logs/evidence retained")


def settings_navigation_node(tree):
    # Original 026 accessibility evidence has TWO text="设置" labels: header + tab.
    # Select the enabled focusable navigation subtree, never a title by coordinates.
    candidates = [node for node in tree.iter('node')
                  if node.get('package') == PACKAGE and node.get('enabled') == 'true'
                  and node.get('focusable') == 'true'
                  and any(child.get('package') == PACKAGE and child.get('text') == '设置'
                          for child in node.iter('node'))]
    require(len(candidates) == 1, 'Actual enabled settings navigation must be unambiguous')
    return candidates[0]


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

    def harvest(self, label="diag-harvest"):
        result = self.adb(label, "exec-out", "run-as", PACKAGE, "tar", "-cf", "-", "-C", "files", "qa-diag-evidence", timeout=45)
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
        require(report.get("packageVersion") == "0.2.7" and report.get("packageCode") == 9, "Installed package identity")
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

    def ui_tree(self, label):
        # A real accessibility dump, not an instrumentation launch or preference injection.
        remote = "/sdcard/qa-normal-mcp-window.xml"
        self.adb(label + "-dump", "shell", "uiautomator", "dump", remote, timeout=20)
        raw = self.adb(label + "-xml", "exec-out", "cat", remote).stdout
        (self.out / (label + ".xml")).write_bytes(raw)
        return ET.fromstring(raw)

    def tap_node(self, label, node):
        bounds = re.fullmatch(r"\[(\d+),(\d+)\]\[(\d+),(\d+)\]", node.get("bounds", ""))
        if bounds is None or node.get("enabled") != "true":
            raise AssertionError("Actual UI target is not enabled/bounded")
        left, top, right, bottom = map(int, bounds.groups())
        require(left < right and top < bottom, "Actual UI target has no visible bounds")
        self.adb(label, "shell", "input", "tap", str((left + right) // 2), str((top + bottom) // 2))

    def keepalive_switch(self, label):
        tree = self.ui_tree(label + "-navigation")
        settings = settings_navigation_node(tree)
        if settings.get("selected") != "true":
            self.tap_node(label + "-settings-tap", settings)
        for attempt in range(8):
            tree = self.ui_tree(label + "-settings-" + str(attempt))
            nodes = [node for node in tree.iter("node") if node.get("package") == PACKAGE]
            switches = [node for node in nodes if node.get("resource-id") in ("mcp-keepalive-switch", PACKAGE + ":id/mcp-keepalive-switch")
                        or (node.get("class") == "android.widget.Switch" and node.get("checkable") == "true")]
            if switches:
                require(len(switches) == 1 and any(node.get("text") == "MCP 保持运行" for node in nodes), "Real MCP settings switch/label missing or ambiguous")
                return switches[0]
            scrollable = [node for node in nodes if node.get("scrollable") == "true"]
            require(len(scrollable) == 1, "Actual settings scroll container must be unambiguous")
            bounds = re.fullmatch(r"\[(\d+),(\d+)\]\[(\d+),(\d+)\]", scrollable[0].get("bounds", ""))
            if bounds is None:
                raise AssertionError("Missing settings scroll bounds")
            left, top, right, bottom = map(int, bounds.groups())
            x = str((left + right) // 2)
            self.adb(label + "-scroll-" + str(attempt), "shell", "input", "swipe", x, str(top + (bottom - top) * 4 // 5),
                     x, str(top + (bottom - top) // 5), "300")
        raise AssertionError("Real MCP settings switch did not become visible")

    def normal_fingerprint(self, label):
        values = self.business(label + "-business")
        # Hash private data, never archive or print the token. NO preference writes.
        result = self.adb(label + "-private-hashes", "shell", "run-as", PACKAGE, "sha256sum", "files/mcp/token", "files/diagnostics/wear-errors.jsonl")
        lines = result.stdout.decode().splitlines()
        require(len(lines) == 2 and all(re.fullmatch(r"[0-9a-f]{64}  files/(mcp/token|diagnostics/wear-errors.jsonl)", line) for line in lines),
                "Complete actual token/error fingerprints required")
        return values + sorted(lines)

    def foreground_receipt(self, label, pid):
        services = self.adb(label + "-services", "shell", "dumpsys", "activity", "services", PACKAGE).stdout.decode(errors="replace")
        # Match only the actual app service record; some unrelated service cannot satisfy this gate.
        records = re.split(r"(?=\* ServiceRecord\{)", services)
        service = [record for record in records if re.search(r"\* ServiceRecord\{[^\n]*com\.hcbiu\.elcton/\.McpKeepAliveService[\s}]", record)]
        require(len(service) == 1 and re.search(r"\bisForeground=true\b", service[0])
                and re.search(r"\bforegroundId=8766\b", service[0]), "Actual MCP service must be foreground with its notification")
        require(re.search(r"\bapp=ProcessRecord\{[^\n]*\b" + re.escape(pid) + r":com\.hcbiu\.elcton/", service[0]), "Foreground service must belong to the same ordinary app PID")
        activities = self.adb(label + "-activities", "shell", "dumpsys", "activity", "activities").stdout.decode(errors="replace")
        require(not re.search(r"(?:mResumedActivity|topResumedActivity|ResumedActivity)[^\n]*com\.hcbiu\.elcton/", activities), "App Activity still resumed after Home")
        running = self.adb(label + "-instrumentation", "shell", "dumpsys", "activity").stdout.decode(errors="replace")
        require("ACTIVITY MANAGER" in running and not re.search(r"ActiveInstrumentation\{", running), "Ordinary background evidence cannot run under instrumentation")
        actual_pid = self.adb(label + "-pid", "shell", "pidof", PACKAGE).stdout.decode().strip()
        require(actual_pid == pid, "Normal process unexpectedly restarted during bounded observation")

    def background_rpc(self, suite, label, name, arguments):
        ident = label
        value = {"jsonrpc": "2.0", "id": ident, "method": "tools/call", "params": {"name": name, "arguments": arguments}}
        status, headers, body = suite.urllib_request("POST", "/mcp", value)
        # Suite independently checks lengths/UTF8/credential non-echo before evidence is written.
        (self.out / (label + "-response.json")).write_bytes(body)
        (self.out / (label + "-http.json")).write_text(json.dumps({"status": status, "headers": headers}) + "\n")
        reply = json.loads(body)
        require(status == 200 and reply.get("jsonrpc") == "2.0" and reply.get("id") == ident and "error" not in reply, "Real background urllib RPC envelope")
        result = reply.get("result", {})
        content = result.get("content", [])
        require(result.get("isError") is False and len(content) == 1 and content[0].get("type") == "text", "Real background tool must succeed")
        data = json.loads(content[0]["text"])
        require(result.get("structuredContent") == data, "Background tool text/structured content mismatch")
        return data

    def verify_normal_background(self, suite, expected, sdk):
        self.report["stage"] = "ordinary-background-fgs"; self.save()
        before = self.normal_fingerprint("background-before")
        if sdk >= 33:
            self.adb("normal-permission-grant", "shell", "pm", "grant", PACKAGE, "android.permission.POST_NOTIFICATIONS")
        switch = self.keepalive_switch("normal-enable")
        require(switch.get("checked") == "false", "Normal cold-start must not silently enable FGS")
        self.tap_node("normal-switch-on", switch)
        checked = self.keepalive_switch("normal-on-readback")
        require(checked.get("checked") == "true", "Real settings opt-in did not become checked")
        frame = self.adb("normal-keepalive-on-frame", "exec-out", "screencap", "-p").stdout
        (self.out / "normal-keepalive-on.png").write_bytes(frame)
        pid = self.adb("normal-background-initial-pid", "shell", "pidof", PACKAGE).stdout.decode().strip()
        require(re.fullmatch(r"[0-9]+", pid) is not None, "Require one ordinary app PID")
        self.adb("normal-home", "shell", "input", "keyevent", "KEYCODE_HOME")
        observations = []
        self.report["normalBackgroundFgs"] = {"passed": False, "scope": "ordinary emulator process; screen-on Home; finite 5s/3 probes; NOT Doze/sticky/phone proof",
                                               "pid": pid, "observations": observations}
        self.save()
        started = time.monotonic()
        for attempt, offset in enumerate((0.0, 2.5, 5.0), 1):
            # A bounded three-sample measurement, not an unbounded keepalive/watchdog.
            delay = started + offset - time.monotonic()
            if delay > 0:
                time.sleep(delay)
            label = "normal-background-" + str(attempt)
            self.foreground_receipt(label, pid)
            version = self.background_rpc(suite, label + "-version", "version_info", {})
            require(version.get("versionName") == "0.2.7" and version.get("versionCode") == 9 and version.get("packageName") == PACKAGE, "Ordinary background exact version")
            errors = self.background_rpc(suite, label + "-errors", "error_tail", {"limit": 1})
            require(len(errors.get("errors", [])) == 1 and errors["errors"][0]["full"] == expected, "Ordinary background persisted full error")
            observations.append({"attempt": attempt, "elapsedSeconds": time.monotonic() - started, "foreground": True, "ordinaryProcess": True, "urllibVersionAndError": True})
            self.save()
        self.adb("normal-notification-shade", "shell", "cmd", "statusbar", "expand-notifications")
        tree = self.ui_tree("normal-notification-on")
        require(any(node.get("package") == "com.android.systemui" and node.get("text") == "MCP 保持运行" for node in tree.iter("node")), "Actual FGS notification must be visible")
        notification = self.adb("normal-notification-frame", "exec-out", "screencap", "-p").stdout
        (self.out / "normal-notification-on.png").write_bytes(notification)
        # Scope the action to the smallest real notification subtree containing our title.
        containers = [node for node in tree.iter("node") if any(child.get("text") == "MCP 保持运行" for child in node.iter("node"))
                      and any(child.get("text") in ("停止", "STOP", "Stop") for child in node.iter("node"))]
        container = min(containers, key=lambda node: len(list(node.iter("node")))) if containers else ET.Element("empty")
        stop = [node for node in container.iter("node") if node.get("package") == "com.android.systemui" and node.get("text") in ("停止", "STOP", "Stop") and node.get("enabled") == "true"]
        if len(stop) == 1:
            self.tap_node("normal-notification-stop-tap", stop[0])
            stop_path = "actual-notification-action"
        else:
            # Collapsed/hidden action: use the real settings switch, never non-exported service bypass/prefs.
            self.adb("normal-notification-collapse", "shell", "cmd", "statusbar", "collapse")
            self.adb("normal-stop-return", "shell", "am", "start", "-W", "-n", PACKAGE + "/.MainActivity")
            switch = self.keepalive_switch("normal-disable")
            require(switch.get("checked") == "true", "Stop must target the actual enabled switch")
            self.tap_node("normal-switch-off", switch)
            stop_path = "actual-settings-switch"
        self.adb("normal-stop-shade-collapse", "shell", "cmd", "statusbar", "collapse")
        # Observe closure while still stopped; don't mistake HTTP errors or adb forward success for a closed listener.
        import socket
        closed = False
        for attempt in range(3):
            try:
                with socket.create_connection(("127.0.0.1", 18766), timeout=1) as peer:
                    peer.settimeout(1)
                    peer.sendall(b"GET /health HTTP/1.1\r\nHost: localhost\r\nConnection: close\r\n\r\n")
                    raw = peer.recv(65536)
                (self.out / ("normal-stop-port-" + str(attempt) + ".bin")).write_bytes(raw)
                closed = raw == b""  # adb forward accepts locally then closes when the device listener is gone.
            except (ConnectionRefusedError, ConnectionResetError, BrokenPipeError):
                closed = True
                (self.out / ("normal-stop-port-" + str(attempt) + ".txt")).write_text("Actual socket refused/reset/broken pipe; no HTTP response\n")
            require(closed, "Actual listener still responds after explicit user stop (timeouts/errors aren't closure)")
        stopped = self.adb("normal-stop-services", "shell", "dumpsys", "activity", "services", PACKAGE).stdout.decode(errors="replace")
        require("isForeground=true" not in stopped and "McpKeepAliveService" not in stopped, "Foreground service remains after explicit stop")
        self.adb("normal-stop-notifications", "shell", "dumpsys", "notification", "--noredact")
        self.adb("normal-stop-shade", "shell", "cmd", "statusbar", "expand-notifications")
        off_tree = self.ui_tree("normal-notification-off")
        require(not any(node.get("text") == "MCP 保持运行" for node in off_tree.iter("node")), "MCP foreground notification still visible after stop")
        self.adb("normal-stop-final-collapse", "shell", "cmd", "statusbar", "collapse")
        self.adb("normal-off-return", "shell", "am", "start", "-W", "-n", PACKAGE + "/.MainActivity")
        switch = self.keepalive_switch("normal-off-readback")
        require(switch.get("checked") == "false", "Explicit stop did not persist real UI opt-out")
        require(self.normal_fingerprint("background-after") == before, "Background FGS/HTTP/stop mutated business, token or errors")
        self.report["normalBackgroundFgs"].update(passed=True, stopPath=stop_path, offPortClosed=True, offNotificationRemoved=True,
                                                 businessAndTokenAndErrorsUnchanged=True, observationCount=len(observations))
        self.save()

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
        sdk_level = int(self.report["sdk"])
        self.report["stage"] = "diagnostics-instrumentation"; self.save()
        result = self.adb("diag-instrumentation", "shell", "am", "instrument", "-w", "-r", "-e", "diag_emulator", "true", "-e", "diag_source_sha", head,
                          "-e", "diag_run", run_id, "-e", "class", PACKAGE + ".DiagnosticsUiTest", PACKAGE + ".test/androidx.test.runner.AndroidJUnitRunner", timeout=420, check=False)
        target = self.harvest()
        verify_one_test(result, "Real diagnostic instrumentation")
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
        http = self.run("android-http-selftest", [sys.executable, "-B", "qa/mcp_http_selftest.py", "--url", "http://127.0.0.1:18766", "--adb-token", PACKAGE,
                        "--adb-token-path", "files/mcp/token", "--adb-serial", self.serial], timeout=120)
        http_report = json.loads(http.stdout)
        require(http_report.get("ok") is True and http_report.get("mode") == "read-only-app"
                and http_report.get("clients") == ["urllib", "curl"], "Normal app must run genuine urllib AND curl selftests")
        self.report["normalHttpSelftest"] = http_report; self.save()
        # Prove a second actual process recovered the persisted synthetic error and both NIO files.
        sys.path.insert(0, str(Path("qa").resolve()))
        from mcp_http_selftest import Suite
        token_result = subprocess.run(["adb", "-s", self.serial, "exec-out", "run-as", PACKAGE, "cat", "files/mcp/token"], capture_output=True, timeout=10)
        require(token_result.returncode == 0 and re.fullmatch(rb"[0-9a-f]{64}", token_result.stdout), "Cold-start actual token read")
        suite = Suite("http://127.0.0.1:18766", token_result.stdout.decode("ascii"))
        expected = (target / "synthetic-expected.txt").read_text()
        failed, version = suite.call("version_info")
        require(not failed and version.get("versionName") == "0.2.7" and version.get("versionCode") == 9 and version.get("packageName") == PACKAGE, "Cold-process real version_info")
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
        self.verify_normal_background(suite, expected, sdk_level)
        # Run destructive notification-denial/bind-failure instrumentation last.
        # Revoking notification permission may kill the emulator process; a channel
        # downgrade is not reliably reversible by recreating the same channel ID.
        # Do not contaminate the independently measured ordinary process above.
        self.report["stage"] = "keepalive-instrumentation"; self.save()
        self.shell("keepalive-cold-stop", "am force-stop " + PACKAGE)
        if sdk_level >= 33:
            self.adb("keepalive-permission-denied", "shell", "pm", "revoke", PACKAGE, "android.permission.POST_NOTIFICATIONS")
        keepalive = self.adb("keepalive-instrumentation", "shell", "am", "instrument", "-w", "-r", "-e", "diag_emulator", "true",
                             "-e", "diag_source_sha", head, "-e", "diag_run", run_id, "-e", "class", PACKAGE + ".McpKeepAliveTest",
                             PACKAGE + ".test/androidx.test.runner.AndroidJUnitRunner", timeout=180, check=False)
        keepalive_target = self.harvest("keepalive-harvest")
        verify_one_test(keepalive, "Real keepalive instrumentation")
        keepalive_report = json.loads((keepalive_target / "keepalive-report.json").read_text())
        self.report["keepaliveInstrumentationReceipt"] = verify_keepalive_report(keepalive_report, head, run_id, sdk_level)
        for name in ("mcp-keepalive-on.png", "mcp-keepalive-on.xml"):
            require((keepalive_target / name).is_file() and (keepalive_target / name).stat().st_size > 0, "Missing keepalive visual evidence: " + name)
        require(any(node.get("package") == PACKAGE for node in ET.parse(keepalive_target / "mcp-keepalive-on.xml").getroot().iter("node")),
                "Keepalive screenshot hierarchy must be actual app")
        self.shell("keepalive-final-stop", "am force-stop " + PACKAGE)
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
                    self.harvest("diag-final-harvest")
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
