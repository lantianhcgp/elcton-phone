# R8 diagnostics actual cloud visual review

Source APK b3eb55680b51f5fbdf392d402acdcdae168f2b20 / build43715446826; UI run43718640929 attempt1, workflow4fc3363f2b30073f1a71de4d4073460b81ec537f; API33/three-button. Original artifact bytes and complete JSON/pixel gates are separate from this visual review (diagnostics-verification/receipt.json passed=true checks12 errors=[]).

Parent personally loaded original screenshots with vision_analyze, then individually enlarged each listed region. No browser/emulator/device started locally.

- diag-product/settings-version.png full + crop[65,1220,1027,1765]: Import/backup action rows visible; three-line privacy description naturally wraps; 0.2.10·测试构建 badge fully readable; Today/Timetable/Device/Settings labels and system three-button controls separated. The privacy card continues below the scroll viewport, not evidence of a lost final paragraph (the following keepalive-on screenshot shows it). No horizontal cut glyph/overlay/blackframe in inspected components.
- diag-product/diagnostics-head.png full + crop[160,370,928,948]: 连接诊断 title, timestamp, exception type, errorCode860026 and SYNTHETIC-BEGIN readable; long text naturally wraps. This is explicitly qa.synthetic.instrumentation, no real device result. Scroll viewport shows only first lines by design.
- diag-product/diagnostics-tail.png full + crop[150,1100,928,1514]: lines43-48, caused-by IllegalArgumentException, SYNTHETIC-CAUSE and SYNTHETIC-END complete; Close button below text has unobstructed label. No Copy button is shown, so no copy-action claim is made.
- diag-product/mcp-keepalive-on.png full + crop[83,960,1008,1534]: MCP诊断/保持运行 headings, ON switch, default-on notice, loopback address and shared-business-layer warning, background restriction and private token storage notices readable without overlap. Version badge and nav consistent with version screenshot.
- normal-notification-on.png full + crop[48,739,1036,1174]: app title, MCP保持运行, loopback port text and Stop action readable. Text wraps naturally; unrelated Android serial-console system notification truncation is not attributed to the app.

Visual result for inspected diagnostic components: PASS. This does not certify Doze/MIUI/HMS/physical watch handshake, actual SDK callback root cause, or fingerprint acceptance. Genuine handshake root cause remains unknown.
