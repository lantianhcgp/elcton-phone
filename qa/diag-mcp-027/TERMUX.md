# Termux 直接调只读 MCP

范围：com.hcbiu.elcton，127.0.0.1:8766；无需 adb forward/配对；所有凭据仅私有目录。原应用 stable 签名与 DEBUGGABLE 标记不变；本通路依赖用户已授权的 Shizuku shell 与 run-as，因此不适用于移除 debuggable 的商店 release。

## 最短调用

在本分支仓库运行：

    python -B qa/termux_mcp.py --tool error_tail --limit 128

脚本每次经 ~/rish/rish -c 'run-as com.hcbiu.elcton cat files/mcp/token' 直接捕获64字节令牌，验证格式，仅置于Python内存。rish -c这条真实读取已验证，tiny read 不混 DONE 标记避免传输交错。完整错误返回时只输出RPC响应，不输出令牌；禁把token读命令裸跑在可录屏/公开终端。

若调 curl/现有自测需要文件：

    python -B qa/termux_mcp.py --save-token /data/data/com.termux/files/home/.hermes/secrets/elcton-mcp-027.token
    python -B qa/mcp_http_selftest.py --url http://127.0.0.1:8766 --token-file /data/data/com.termux/files/home/.hermes/secrets/elcton-mcp-027.token

文件路径只允许Termux私有home内，O_NOFOLLOW/fchmod0600；禁止Documents、Download、/sdcard、剪贴板、屏幕、日志、git存凭据。现有文件为64字节，0600；mode实测见evidence/token-private-verification.json（无值）。取用不需要装App，不需要拿运行中的App抢前台，不调用WE/AGC。

## --adb-token-path 真正含义

原 selftest --adb-token com.hcbiu.elcton --adb-token-path files/mcp/token 等价于 adb exec-out run-as PACKAGE cat files/mcp/token。它是run-as工作目录下的路径，不是host可读路径，不是共享token/export端点。CI emulator可用adb；当前真机配对失效，使用上面已存在rish权限走同一run-as私有读取。不添加写工具，也不加公共token文件。

## 可达性策略

0.2.7 设置页新增「MCP 保持运行」，默认关；开时经明确用户同意通知，启动非导出前台服务，仅loopback只读；关时关闭当前listener/活动连接和通知。默认被动进程模式保留：普通冷启动App可短期使用MCP，但不承诺后台可达。不得把纯LISTEN或system resumedActivity当做HTTP成功。

辅助deviceidle白名单真机实测：添加成功，但连接仍超时；立即恢复并独立读回不存在，不写自动白名单、不更改电池策略。

## 本次真机原样失败边界

安装仍为0.2.6/code8，未安装0.2.7、不主动拉起App/解锁。Termux curl/urllib真请求均0字节/connect timeout；UID10838/PID26578 freezer记录冻结。rish/run-as读取原日志确有两条 Scope unauthorized(errorCode8)，这是私有文件核验而非error_tail成功。本棒在禁止安装/抢前台边界下，真机硬验收BLOCKED，不能宣称直接MCP外部全通。

若以后用户安装0.2.7并自己开启保活，再用上面只读脚本重验；完整请求/响应需按实际保存，仅Authorization字段脱敏。当前已保存实际尝试配置、curl退出码/urllib异常/0字节、freezer和白名单恢复证据，不编造成功响应。
