#!/usr/bin/env python3
"""Exclusive final report from exact successful remote Android/CI receipts only.
First-run failures are retained and never used as replacement successes.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re

p = argparse.ArgumentParser()
for key in ('verification', 'diag', 'full', 'build', 'diag_meta', 'full_meta', 'out'):
    p.add_argument('--' + key.replace('_', '-'), required=True)
a = p.parse_args()
v = json.loads(Path(a.verification).read_bytes())
d = json.loads(Path(a.diag).read_bytes())
f = json.loads(Path(a.full).read_bytes())
b = json.loads(Path(a.build).read_bytes())
dr = json.loads(Path(a.diag_meta).read_bytes())
fr = json.loads(Path(a.full_meta).read_bytes())
sha = v['source_sha']
assert v['passed'] is True and d['passed'] is True and f['passed'] is True
assert d['sourceSha'] == f['source_sha'] == b['headSha'] == dr['headSha'] == fr['headSha'] == sha
assert all(x['status'] == 'completed' and x['conclusion'] == 'success' for x in (b, dr, fr))
assert d['apkSha256']['main'] == v['apk_sha256']
assert d['certificates']['main'] == v['signer_sha256']
assert d['normalBackgroundFgs']['passed'] is True
assert d['normalBackgroundFgs']['stopPath'] == 'actual-notification-action'
assert d['keepaliveInstrumentationReceipt']['passed'] is True
assert d['normalHttpSelftest']['ok'] is True
assert len(f['shots']) == len(f['hierarchies']) == 28
assert f['theme_ui']['passed'] is True and f['palette_ui']['passed'] is True
assert f['system_bar_pixels']['passed'] is True
text = f'''# 手机端 0.2.9/code11 合并版交付

最终APK源码：{sha}
分支：release/0.2.9-20261114（不修改master）
文件：{v['delivery_path']}
字节数：{v['bytes']}
APK SHA-256：{v['apk_sha256']}
签名公证书 SHA-256：{v['signer_sha256']}

## 实际已验交付层
- P2P回执修复线与保活线已合并；保活默认开。通知权限/启动失败保留开启选择，但实际关闭监听，不把未活动显示成服务已运行。
- MCP共15项（旧4+新11）：error_tail、diag_read、version_info、fs_read、sync_connect、sync_disconnect、start_import、start_publish、abort、courses_read、courses_write、pickup_import、devices_list、pairing_state、sync_state。
- UI与MCP调用同一业务/状态机，只有本地token鉴权，监听127.0.0.1。MCP工具清单由生产类JVM与真实云端APK HTTP共同核验；涉及实体手表的同步成功并未验。
- 本地JVM152/152、最终Python104/104零skip、HTTP3784条断言；既有反例/新回归/历史原件保留。
- 精确真实Android构建和Gradle XML153/153零失败零skip；实际主APK与测试APK公证书一致、v2签名通过。
- 双轴复核与最新124项完整输入/37个产品文件SHA精确绑定；R2两处启动失败路径已逐项核。所有归因、首次RED、重跑RED与原件均保留。
- API33云端诊断及正常Android冷进程HTTP/NIO/完整错误持久化回读通过；通知默认开、实际通知STOP动作到durable停止后首探无HTTP响应等门禁通过。
- 云端后台保活只测Home亮屏5秒内三次探测，不是MIUI冻结/Doze/十分钟保活证明。
- API33原完整UI/主题/调色/产品套件及28张图像数值、系统栏像素门通过。UI外观/持久化套件明确预授权通知权限；不冒称首次权限窗交互已验。
- 旧0.2.8 APK与1.1.15 HAP SHA/大小未变；本次按新文件名独占写入，不覆盖已交付包。

## 物理真机层：pending，归发起方
- 纯MCP「导入→同步→回读」全链、零UI注入。
- 手机退后台10分钟 /health 200且error_tail可读。
- 本会话不安装/启动/点击手机，不操作表端/表盘/Scope，不修改签名材料。

## 精确证据
- 构建：{b['url']}
- 云端诊断/保活：{dr['url']}
- 云端完整UI：{fr['url']}
- 源码：https://github.com/lantianhcgp/elcton-phone/tree/{sha}
- 原始完整证据：qa/release-029/evidence/resume-1720/，含各次失败和修正的精确归因。
- 全源码/测试/配置/原始证据的独立远端逐字读回回执，以及交付尾部证据读回，另存同证据目录。
'''
out = Path(a.out)
out.parent.mkdir(parents=True, exist_ok=True)
with out.open('x') as file:
    file.write(text)
print(json.dumps({'report': str(out), 'bytes': out.stat().st_size, 'sha256': hashlib.sha256(out.read_bytes()).hexdigest(), 'physical_acceptance': 'pending-originator'}, ensure_ascii=False))
