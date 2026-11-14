# R11 latest diagnostics original images — parent native visual review

Exact source: 84a6c406099348f75b436a8e9467c34487766859
Exact diagnostics run: 43600960069 / attempt1
Actual APK SHA256s match the independently verified build43600711386 main664e8eae…b5065 / testeb54c78b…a5462d. All334 fetched original file hashes independently matched inventory, plus full verifier10 checks passed. This section records visual review, not acceptance of MIUI/physical10minutes.

## Actual images personally loaded and component crops inspected

- settings-version.png (1080x1920, SHA c30504e840eca749823fa776e4d6f94a2f1431fe4e4e26f7c0ab6997247211b9): header hc课程表/设置/第11周, import/backup three rows and red 清空手机课表, privacy paragraph, 0.2.9·测试构建 pill, four-item bottom navigation and three-button system bar. Correct visible Chinese and no horizontal spill/overlap in the tested viewport. The lower privacy card is naturally scrolled/clipped at content viewport below the version pill; MCP switch is NOT visible in this particular viewport and is not inferred from it.
- diagnostics-head.png (SHA22d89d2e9f92604784da3d23296cb454d4ec1d972c34b9de2980df251e49174e): 连接诊断 heading, timestamp2026-11-14T13:45:15.260Z, qa.synthetic.instrumentation, exception/java.lang.IllegalStateException, [errorCode=860026]: SYNTHETIC-BEGIN, line1 onward. Line wraps remain inside dialog. Title/content start crop[166,375,914,907] personally inspected, no corrupted glyph/ellipsis at the tested start. Content extends below scroll viewport; not a truncated string assertion by sight alone.
- diagnostics-tail.png (SHA d6461856ca9d8b03ce3c8edf6f0fc83a027ea7a0a7d382518c5e02a1f8b945a2): lines43–48, caused by, java.lang.IllegalArgumentException, [errorCode=860026]: SYNTHETIC-CAUSE and SYNTHETIC-END all visible after scrolling. Crop[165,1091,918,1505] explicitly checked full END and cause glyphs, bottom padding and 关闭 button. No missing final marker, overlap or horizontal spill seen. Complete text equality is independently enforced by original JSON/HTTP/fixture checks rather than claiming all48lines were visually shown simultaneously.
- mcp-keepalive-on.png (SHA3993f029e636e59fdf1257f62c46a8d3af2cdb98ea5e86c618993c49746d2baa): privacy card includes visible version0.2.9 and Wear Engine qualification. MCP诊断/MCP保持运行, white knob on right over purple active track, default-on notification explanation, 127.0.0.1:8766/shared business layer text and private token/Shizuku/run-as paragraph. Crop[79,653,1000,1550] explicitly checked each line/card/active switch, natural wraps, bottom explanation and no text/nav overlap. 0.2.9 pill and switch glyphs visible intact.

No UI/product edits made. The synthetic exception explicitly says no real device result. No real watch/WearEngine/MIUI or10-minute health acceptance is claimed.
