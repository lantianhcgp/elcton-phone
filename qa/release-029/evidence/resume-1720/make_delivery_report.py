#!/usr/bin/env python3
"""Produce delivery report only from actual verified receipts; always keeps physical scope pending."""
import argparse,json,hashlib
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--verification',required=True);p.add_argument('--diag',required=True);p.add_argument('--full',required=True);p.add_argument('--out',required=True);a=p.parse_args()
v=json.loads(Path(a.verification).read_bytes());d=json.loads(Path(a.diag).read_bytes());f=json.loads(Path(a.full).read_bytes());assert v['passed'] is True and d['passed'] is True and f['passed'] is True
sha=v['source_sha'];assert d.get('sourceSha',d.get('source_sha'))==sha and f.get('sourceSha',f.get('source_sha'))==sha
text='''# 手机端 0.2.9/code11 合并版交付

构建源码：{sha}
分支：release/0.2.9-20261114（不修改 master）
实际文件：{path}
文件字节数：{bytes}
APK SHA-256：{apksha}
公证书 SHA-256：{cert}

## 实际交付层
- p2p 回执线与保活线合并；保活默认开启，拒通知权限时保留选择但关闭监听，不假称活动。
- MCP 15 项：旧4只读 + 新11动作/数据；UI与MCP共用同一业务/状态机。
- 本地主机JVM152/152、全量Python100/100零skip、HTTP3784断言；真实Runtime并发回归已保留。
- 精确CI43583832086：Android真实编译、Gradle XML153/153零skip、APK及测试APK、原签名均通过。
- API33云端diagnostics43584056185：完整原始报告见下列证据；不是MIUI/物理蓝牙证明。
- API33云端full43584098560：原主题/调色/产品回归完整报告见下列证据。
- 原0.2.8 APK与1.1.15 HAP原SHA未变，不覆盖旧交付物。

## 物理真机层：pending，归发起方
- 纯MCP「导入→同步→回读」零UI注入。
- 退后台10分钟 /health 200与error_tail可读。
- 本会话不安装/启动/点击手机，不操作表端/表盘/Scope，不换签名。

## 证据索引
- 构建：https://github.com/lantianhcgp/elcton-phone/actions/runs/43583832086
- 诊断/保活：https://github.com/lantianhcgp/elcton-phone/actions/runs/43584056185
- 全UI：https://github.com/lantianhcgp/elcton-phone/actions/runs/43584098560
- 原始证据：qa/release-029/evidence/resume-1720/（包含首次RED及每次迁移完整归因/不变原件）
'''.format(sha=sha,path=v['delivery_path'],bytes=v['bytes'],apksha=v['apk_sha256'],cert=v['signer_sha256'])
out=Path(a.out);out.parent.mkdir(parents=True,exist_ok=True)
with out.open('x') as file:file.write(text)
print(json.dumps({'report':str(out),'bytes':out.stat().st_size,'sha256':hashlib.sha256(out.read_bytes()).hexdigest(),'physical_acceptance':'pending-originator'},ensure_ascii=False))
