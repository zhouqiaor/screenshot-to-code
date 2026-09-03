# -*- coding: utf-8 -*-
"""构建阶段缓存：保留历史编译结果，让重复编译只跑真正变化的阶段。

设计要点
--------
1. **指纹（fingerprint）**：每个阶段的输入（源文件 / 依赖 jar / 资源目录 / 命令行参数）
   算成一个 sha256。文件签名用 `(basename, size, mtime_ns)`，不读内容——
   deps_repo 有 119 MB / 50 个 jar，读内容算哈希比直接重编还慢。
2. **stamp 文件**：`<out>/.cache/<stage>.stamp`（JSON），记录指纹 + 时间 + 输出清单。
3. **命中条件**（三者同时满足才复用）：
   - stamp 存在且指纹一致
   - 声明的输出全部仍存在
   - 未被 `--no-cache` / `--force <stage>` 显式禁用
4. **失效即重建**：任一条件不满足则重跑该阶段，跑完写新 stamp。

为什么值得做
------------
本项目 CLI 直编各阶段耗时（i5-8250U / 8 GB）：
    deps_dex   ~150 s   d8 打 50 个 jar → 2 个 dex（最贵）
    link_res   ~90 s    aapt2 编译 38 个库 res + javac 484 个 R 类
    kotlinc    ~60 s    Compose 编译器插件
    our_dex    ~8 s     只有我们的 .class
只改 MainActivity.kt 时，deps_dex 与 link_res 的输入完全没变，
复用后单轮从 ~5 min 降到 ~70 s。
"""
import hashlib
import json
import os
import time


def _stat_sig(path):
    """文件签名：size + mtime_ns。不读内容（大 jar 读哈希比重编还慢）。"""
    try:
        st = os.stat(path)
        return "%d:%d" % (st.st_size, st.st_mtime_ns)
    except OSError:
        return "MISSING"


def fingerprint(files=(), dirs=(), extra=()):
    """算输入指纹。
    files: 单个文件列表（用 basename 参与哈希，避免绝对路径变动导致误失效）
    dirs:  目录列表（递归，用相对路径参与哈希）
    extra: 任意字符串（命令行参数、版本号、min-api 等）
    """
    h = hashlib.sha256()
    for p in sorted(files):
        h.update(("F|%s|%s\n" % (os.path.basename(p), _stat_sig(p))).encode("utf-8"))
    for d in sorted(dirs):
        if not os.path.isdir(d):
            h.update(("D|%s|MISSING\n" % os.path.basename(d)).encode("utf-8"))
            continue
        for root, _, fns in os.walk(d):
            for fn in sorted(fns):
                fp = os.path.join(root, fn)
                rel = os.path.relpath(fp, d).replace("\\", "/")
                h.update(("D|%s|%s\n" % (rel, _stat_sig(fp))).encode("utf-8"))
    for e in extra:
        h.update(("E|%s\n" % e).encode("utf-8"))
    return h.hexdigest()


class Cache:
    """阶段缓存管理器。

    用法：
        cache = Cache(OUT, enabled=not args.no_cache, forced=args.force)
        fp = fingerprint(files=dep_jars, extra=["min-api=24"])
        if not cache.hit("deps_dex", fp, [dex_path]):
            ... 真正执行 d8 ...
            cache.save("deps_dex", fp, [dex_path])
        cache.summary()
    """

    def __init__(self, out_dir, enabled=True, forced=(), seed=False):
        self.dir = os.path.join(out_dir, ".cache")
        self.enabled = enabled
        self.forced = set(forced or ())
        # seed 模式：不执行阶段，只为「已存在的历史产物」补写 stamp。
        # 用于首次引入缓存机制时把此前手工构建的 deps_dex / r_classes 直接纳管，
        # 避免白白重建。指纹算法与正常路径完全同源，不存在漂移。
        self.seed = seed
        os.makedirs(self.dir, exist_ok=True)
        self.hits = []
        self.rebuilt = []
        self.seeded = []
        self._t0 = {}

    def _stamp(self, stage):
        return os.path.join(self.dir, stage + ".stamp")

    def hit(self, stage, fp, outputs):
        """检查缓存是否可用。命中返回 True（调用方应跳过该阶段）。"""
        self._t0[stage] = time.time()
        if self.seed:
            missing = [o for o in outputs if not os.path.exists(o)]
            if missing:
                print("[cache SEED] %s → 历史产物不全（缺 %s），改为正常构建"
                      % (stage, ", ".join(os.path.basename(m) for m in missing[:3])))
                return False
            self.save(stage, fp, outputs)
            self.rebuilt.pop()          # save() 记的是「重建」，seed 要单独统计
            self.seeded.append(stage)
            print("[cache SEED] %s → 已按现有产物补种 stamp，跳过执行" % stage)
            return True
        if not self.enabled:
            print("[cache OFF ] %s → 重建（--no-cache）" % stage)
            return False
        if stage in self.forced or "all" in self.forced:
            print("[cache SKIP] %s → 重建（--force %s）" % (stage, stage))
            return False
        sp = self._stamp(stage)
        if not os.path.exists(sp):
            print("[cache MISS] %s → 重建（无 stamp，首次构建）" % stage)
            return False
        try:
            with open(sp, "r", encoding="utf-8") as f:
                rec = json.load(f)
        except (OSError, ValueError):
            print("[cache MISS] %s → 重建（stamp 损坏）" % stage)
            return False
        if rec.get("fp") != fp:
            print("[cache MISS] %s → 重建（输入已变化）" % stage)
            return False
        missing = [o for o in outputs if not os.path.exists(o)]
        if missing:
            print("[cache MISS] %s → 重建（产物缺失：%s）"
                  % (stage, ", ".join(os.path.basename(m) for m in missing[:3])))
            return False
        names = ", ".join(os.path.basename(o) for o in outputs[:3])
        if len(outputs) > 3:
            names += " +%d" % (len(outputs) - 3)
        print("[cache HIT ] %s → 跳过，复用 %s（上次构建 %s）"
              % (stage, names, rec.get("ts", "?")))
        self.hits.append(stage)
        return True

    def save(self, stage, fp, outputs):
        """阶段执行成功后写 stamp。"""
        rec = {
            "fp": fp,
            "ts": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "elapsed_s": round(time.time() - self._t0.get(stage, time.time()), 1),
            "outputs": [os.path.basename(o) for o in outputs],
        }
        try:
            with open(self._stamp(stage), "w", encoding="utf-8") as f:
                json.dump(rec, f, ensure_ascii=False, indent=2)
        except OSError as e:
            print("  [WARN] 写 stamp 失败 %s: %s" % (stage, e))
        self.rebuilt.append(stage)

    def invalidate(self, stage):
        """手工作废某阶段（改名而非删除，绕过沙箱 safe-delete shim）。"""
        sp = self._stamp(stage)
        if os.path.exists(sp):
            try:
                os.rename(sp, sp + ".invalid.%d" % int(time.time() * 1000))
            except OSError:
                pass

    def summary(self):
        if self.seeded:
            print("\n[cache] 补种 %d 个阶段：%s" % (len(self.seeded), ", ".join(self.seeded)))
        print("\n[cache] 命中 %d 个阶段：%s" % (len(self.hits), ", ".join(self.hits) or "-"))
        print("[cache] 重建 %d 个阶段：%s" % (len(self.rebuilt), ", ".join(self.rebuilt) or "-"))
        if self.hits or self.seeded:
            print("[cache] 提示：如需强制全量重建用 --no-cache，单阶段用 --force <stage>")
