# R6 Android 精确链 — 显式执行、小型零复制 helpers

**仅新增本目录文件；没有 dispatch/push/Gradle/kotlinc/Chromium/ADB/设备动作。**

## 已核路径、旧基线与边界

- 当前根：`/data/data/com.termux/files/home/elcton-phone-diagnostics-0210-20261115`
- 固定分支：`diag/p2p-trace-0.2.10-20261115`；仓库 `lantianhcgp/elcton-phone`。
- 旧源根：`/data/data/com.termux/files/home/elcton-phone-release-029-20261114`。
- 旧工具：旧源根下 `qa/release-029/evidence/resume-1720/resume-fourth/` 的 `run_exact_pipeline.py`、`fetch_exact_attempt.py`、`verify_exact_build.py`、`verifiers/verify_cloud.py`、`verify_cloud_snapshot_map.py`。**不要直接运行**：旧分支/版本/153硬编码，旧 cloud 会完整复制大树。
- `.github/workflows/build.yml` SHA256 `ae61e37478852ca2263912eb0f28792aed6b4aab93bec0632a281177b9f12487`。
- `.github/workflows/ui-smoke.yml` SHA256 `9f7c80dff5db343a240ee90728cd97ac025da87930ad2233037a4834ae57d095`。两 workflow 旧/新字节相同；diag push 不触发，原 `workflow_dispatch` 无需改 YAML。
- build 原真实命令 `gradle -PelctonP2pCandidate=true testDebugUnitTest assembleDebug assembleDebugAndroidTest --no-daemon --stacktrace`，其后真实 Gradle classpath HTTP3784、稳定主/测试签名、binary manifest。不是 HOST 代验 Android。
- 主 APK 必须 `com.hcbiu.elcton /12/0.2.10`；测试 APK `com.hcbiu.elcton.test` 的实际版本字段保持空；两 APK 各查 apksigner、单 signer、v2、CRC、SHA/size；证书 `fc08a0b474a8ffca5887bd5c88ac15e865a63a64eca81c10f344496c46d9ad94`。
- 原真实 Gradle XML为30 suites/153 unique labels；当前新增观测19 = **172**，不是 HOST171。afterREADY8 属HOST专用 `.in`，不混入Gradle。
- parent新增 baseline fixture：`qa/p2p-trace-0210/r6/fixtures/P2pTraceBaselineEngine.kt` SHA256 `af97a6fd8e3a9941b6cc11d533423cdb049f038782a6bd9791c8ed8ac5c274e9`。整个qa递归进入Gradle test sourceSet；生成重复`.kt`不可stage。
- 当前 `qa/diag_emulator_smoke.py` 使用已迁移的三个版本谓词；离线Gate只在内存把旧 `background` 的一个版本tuple改为12/0.2.10，AST证明其余全部节点和labels原样；其他4 criteria逐字节冻结。`clients/diagnostics/background/full/tour/check/write`全部继承，完整JSON不删键/错误/精度。
- full仍原theme23、palette74、tour28 PNG/XML/state、keyboard1、system bars20。`emulator_install_and_tour.py` 绝不import，仅运行原纯 verifier AST span。

## 前提与阻塞

1. 本次HEAD仍为R5断点 `de3e6f182c2def5a52d33f33684777f1fc941ccd`，**不能作为R6最终SHA dispatch**。parent完成源冻结、版本/新身份登记、SPEC→QUALITY、白名单commit及获准push后再执行。
2. `dispatch-build`要求真实review目录内`dual-closure.json`（passed=true、axes各有axis/raw_sha256及对应`<axis>-raw.txt`）和完整`reviewed-manifest.json`（repo相对路径→SHA256）。必须由实际评审回执形成，不能编造closure。
3. source identity历史 `qa/release-029/approved-release-delta.json`不动；parent独立登记3新源SHA/P2pTrace身份。helper不代改旧源门。
4. 手机空间仅约1.1GB（本次只读检查）；新fetch先查ZIP空间，读取CRC后再查完整展开空间，不足明确拒绝并保留ZIP。**绝不复制旧600MB树、不stage artifact/ZIP/证据**。
5. CI固定Python3.12/Pillow11.2.1；本机不同版本仅记为离线复算环境，真实Android/UI证据必须来自新的精确run。本次只做helper self-test，不声称新Android绿。

## 精确命令（仅交接，未执行）

下列路径OUT每次都必须不存在；全部写入本exclusive ci目录。token完全由gh处理，不读取/输出凭据。

```bash
cd /data/data/com.termux/files/home/elcton-phone-diagnostics-0210-20261115
CI="$PWD/qa/p2p-trace-0210/r6/ci"
SHA='<最终R6完整40位小写commit>'
WSHA="$SHA"                  # UI workflow HEAD，QA-only变更时可不同；须独立绑定
REVIEW='<真实独立SPEC+QUALITY闭合目录>'
E="$CI/evidence/<本轮唯一目录名>"

# 纯离线helper测试；无网络/设备/构建/文件写入
python -B "$CI/pipeline.py" --self-test
python -B "$CI/verify_r6.py" --self-test

# 最终源码的必跑case库存：原153完整label + 已核新增19，预注册，不从新XML倒推
python -B "$CI/verify_r6.py" register-cases --source "$SHA" \
  --added-cases "$CI/added-cases.json" --out "$E/case-registration"

# 必须显式dispatch-build；无自动dispatch/rerun/push
python -B "$CI/pipeline.py" dispatch-build --sha "$SHA" --review "$REVIEW" --out "$E/build-dispatch"
BUILD='<build-dispatch/registered.json真实run.id>'
python -B "$CI/pipeline.py" wait --run "$BUILD" --sha "$SHA" --kind build --out "$E/build-wait"
python -B "$CI/pipeline.py" fetch --run "$BUILD" --sha "$SHA" --source "$SHA" --kind build --out "$E/build-artifact"
python -B "$CI/verify_r6.py" build --source "$SHA" --run "$BUILD" --incoming "$E/build-artifact" \
  --case-manifest "$E/case-registration/testcases.json" --out "$E/build-verification"

# API33 / three-button / 显式build_run+build_sha；先注册diag，再注册full，不猜最新ID
python -B "$CI/pipeline.py" dispatch-ui --sha "$WSHA" --suite diagnostics --build-run "$BUILD" \
  --build-sha "$SHA" --build-receipt "$E/build-verification/receipt.json" --out "$E/diagnostics-dispatch"
DIAG='<diagnostics-dispatch/registered.json真实run.id>'
python -B "$CI/pipeline.py" dispatch-ui --sha "$WSHA" --suite full --build-run "$BUILD" \
  --build-sha "$SHA" --build-receipt "$E/build-verification/receipt.json" \
  --previous-registration "$E/diagnostics-dispatch/registered.json" --out "$E/full-dispatch"
FULL='<full-dispatch/registered.json真实run.id>'

# 两run注册后可并行等待；每个命令单独保存真实exit，失败仍取件并保留RED
python -B "$CI/pipeline.py" wait --run "$DIAG" --sha "$WSHA" --kind android --seconds 2400 --out "$E/diagnostics-wait"
python -B "$CI/pipeline.py" wait --run "$FULL" --sha "$WSHA" --kind android --seconds 2400 --out "$E/full-wait"
python -B "$CI/pipeline.py" fetch --run "$DIAG" --sha "$WSHA" --source "$SHA" --kind android --out "$E/diagnostics-artifact"
python -B "$CI/pipeline.py" fetch --run "$FULL" --sha "$WSHA" --source "$SHA" --kind android --out "$E/full-artifact"
python -B "$CI/verify_r6.py" cloud --source "$SHA" --workflow-sha "$WSHA" --run "$DIAG" --suite diagnostics \
  --incoming "$E/diagnostics-artifact" --registration "$E/diagnostics-dispatch/registered.json" \
  --build-run "$BUILD" --build-receipt "$E/build-verification/receipt.json" --out "$E/diagnostics-verification"
python -B "$CI/verify_r6.py" cloud --source "$SHA" --workflow-sha "$WSHA" --run "$FULL" --suite full \
  --incoming "$E/full-artifact" --registration "$E/full-dispatch/registered.json" \
  --build-run "$BUILD" --build-receipt "$E/build-verification/receipt.json" --out "$E/full-verification"

# 收尾重新读精确run/attempt/完整分页artifact；先后attempt变化禁止闭合PASS
python -B "$CI/pipeline.py" readback --run "$BUILD" --sha "$SHA" --kind build --out "$E/build-final-readback"
python -B "$CI/pipeline.py" readback --run "$DIAG" --sha "$WSHA" --kind android --out "$E/diagnostics-final-readback"
python -B "$CI/pipeline.py" readback --run "$FULL" --sha "$WSHA" --kind android --out "$E/full-final-readback"
```

UI名是`android-ui-${github.sha}`＝WSHA，不是buildSha；build名`android-probe-${github.sha}`。helper保存run API、exact attempt API、全分页artifacts总数、exact ID、原ZIP CRC及SHA/size、**每个文件全量inventory**、前后字节等值、code fingerprints、原完整JSON/错误。重复同名/attempt歧义即拒绝，不用`gh run download --name`。

每个suite最终必须自己的`receipt.json passed:true`且其原始run/attempt completed/success；build最终XML必须172 unique，原153逐个label全在。任何网络/工具/真实CI失败均保留原退出码和原件，不替换为旧绿色证据。没有Release/master/PR/设备授权。
