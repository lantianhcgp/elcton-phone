# R9独立审查阻塞 — 修复方向（尚未改实现）

原冻结final-review-r9-continuation127/37继续保持；两原raw判定落盘前不改这份实现，全部原反例保留。

从两个独立live取证已确认：
1. inline observer写盘失败会让原成功harvest不返回（原测试断言不变；观测须try隔离）。
2. child返回7后最终receipt写失败会抛OSError掩盖7（所有观察写须best-effort，不改child返回）。
3. child信号-15/-13传sys.exit变241/243，原shell为143/141（保留原child原码，出口按POSIX128+signal）。
4. sampler任务卡住后无限join阻塞子进程结果（只观察线程daemon+有界join，不能让它拦child退出）。
5. crashdata按is_file读取symlink可跨出/tmp/android-runner并把任意外文件放进上传（拒绝symlink/路径逃逸，O_NOFOLLOW实际打开）。

下一版仅观察层修这些边界，新增独立反例测试先RED；旧产品/仪器/判据/超时/GPU/SDK资源不变。全回归与全新freeze+双轴→精确CI+两个新云端仍是必须项，观察修正不是模拟器已修证明。
