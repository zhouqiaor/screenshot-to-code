#!/usr/bin/env python3
"""完整打包：base_res.apk（含全部库资源）+ our classes + R classes + deps dex → 签名 APK。

依赖前置产物：
  link_resources.py -> compose_cli_build/base_res.apk, compose_cli_build/r_classes/
  redex_deps.py     -> compose_cli_build/deps_dex/classes*.dex
  build_compose_apk.py 的 kotlinc 阶段 -> compose_cli_build/classes/

关键点：
  1. minSdk 24 原生支持 multidex，全部 dex 按 classes.dex/classes2.dex/... 打进 APK，
     绝不能只打第一个（此前漏掉 deps 的 classes2.dex 导致 ClassNotFoundException）。
  2. 我们的 .class 与 R .class 必须与依赖分开 d8，依赖只作 --classpath，
     否则 d8 会把我们的类当无用代码丢掉。

增量：业务/R 的 .class 没变时复用 our_dex（跳过 d8），见 buildcache.py。
"""
import argparse
import os, sys, subprocess, zipfile, time, importlib.util

from buildcache import Cache, fingerprint

ROOT = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("bca", os.path.join(ROOT, "build_compose_apk.py"))
bca = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bca)

OUT = bca.OUT
BT = bca.BT
D8 = bca.D8
ZIPALIGN = bca.ZIPALIGN
APKSIGNER = bca.APKSIGNER
ANDROID_JAR = bca.ANDROID_JAR
KEYSTORE = bca.KEYSTORE

BASE_RES_APK = os.path.join(OUT, "base_res.apk")
R_CLASSES = os.path.join(OUT, "r_classes")
WORK_APK = os.path.join(OUT, "base_full.apk")
ALIGNED_APK = os.path.join(OUT, "e2e_compose_full.apk")
SIGNED_APK = os.path.join(OUT, "e2e_compose_full_signed.apk")


STALE_DIR = os.path.join(OUT, "_stale_bak")


def rename_away(path):
    """改名让位（绕沙箱 safe-delete shim），统一收进 _stale_bak/ 避免原地堆积。"""
    if not os.path.exists(path):
        return
    os.makedirs(STALE_DIR, exist_ok=True)
    name = os.path.basename(path.rstrip("\\/"))
    keep = os.path.join(STALE_DIR, name)
    if os.path.exists(keep):
        try:
            os.rename(keep, "%s.%d" % (keep, int(time.time() * 1000)))
        except OSError:
            pass
    try:
        os.rename(path, keep)
    except OSError as e:
        print("  [WARN] rename_away: %s (%s)" % (path, e))


def run(cmd, label):
    p = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if (p.stdout or "").strip():
        print((p.stdout or "").strip()[:1500])
    if p.returncode != 0:
        print("[FAIL] %s rc=%d" % (label, p.returncode))
        print((p.stderr or "").strip()[:4000])
        return False
    if (p.stderr or "").strip():
        print("[stderr] " + (p.stderr or "").strip()[:800])
    print("[OK] %s" % label)
    return True


def collect_dex(d):
    out = []
    p0 = os.path.join(d, "classes.dex")
    if os.path.exists(p0):
        out.append(p0)
    i = 2
    while True:
        p = os.path.join(d, "classes%d.dex" % i)
        if not os.path.exists(p):
            break
        out.append(p)
        i += 1
    return out


def main():
    ap = argparse.ArgumentParser(description="完整 APK 打包（默认增量复用 our+R dex）")
    ap.add_argument("--no-cache", action="store_true", help="禁用缓存，强制重跑 d8")
    ap.add_argument("--force", action="append", default=[], metavar="STAGE",
                    help="强制重建阶段：our_r_dex 或 all")
    ap.add_argument("--seed-cache", action="store_true",
                    help="不执行 d8，只为已存在的 our_dex 补写 stamp（仍会重新打包签名）")
    args = ap.parse_args()
    cache = Cache(OUT, enabled=not args.no_cache, forced=args.force,
                  seed=args.seed_cache)

    for need in (BASE_RES_APK, R_CLASSES, bca.OUT_CLASSES, os.path.join(OUT, "deps_dex")):
        if not os.path.exists(need):
            print("[FAIL] 缺少前置产物: %s" % need)
            sys.exit(1)

    dep_jars = bca.collect_dep_jars()
    extra_jars = bca.collect_extra_jars()

    # 1. d8 our classes + R classes（依赖仅作 classpath）
    our_dex_dir = os.path.join(OUT, "our_dex")
    inputs = []
    for base in (bca.OUT_CLASSES, R_CLASSES):
        for root, _, files in os.walk(base):
            for fn in files:
                if fn.endswith(".class"):
                    inputs.append(os.path.join(root, fn))
    print("[our] %d 个 .class（业务 + R）" % len(inputs))
    # 缓存键：业务 .class + R .class 内容 + 依赖 classpath 清单
    our_fp = fingerprint(dirs=[bca.OUT_CLASSES, R_CLASSES],
                         files=dep_jars + extra_jars,
                         extra=["min-api=24", "release"])
    our_dex_main = os.path.join(our_dex_dir, "classes.dex")
    if not cache.hit("our_r_dex", our_fp, [our_dex_main]):
        rename_away(our_dex_dir)
        os.makedirs(our_dex_dir, exist_ok=True)
        cp_args = []
        for cp in [ANDROID_JAR] + dep_jars + extra_jars:
            cp_args += ["--classpath", cp]
        # 输入文件太多会超命令行长度上限，写 @argfile
        argfile = os.path.join(OUT, "_our_inputs.txt")
        with open(argfile, "w", encoding="utf-8") as f:
            for p in inputs:
                f.write(p.replace("\\", "/") + "\n")
        if not run([D8, "--release", "--output", our_dex_dir, "--min-api", "24"] + cp_args +
                   ["@" + argfile], "d8 our+R dex"):
            sys.exit(1)
        cache.save("our_r_dex", our_fp, [our_dex_main])

    our_dexes = collect_dex(our_dex_dir)
    deps_dexes = collect_dex(os.path.join(OUT, "deps_dex"))
    print("[dex] ours=%d deps=%d" % (len(our_dexes), len(deps_dexes)))

    # 2. 复制 base_res.apk 并塞入全部 dex
    rename_away(WORK_APK)
    with open(BASE_RES_APK, "rb") as src, open(WORK_APK, "wb") as dst:
        dst.write(src.read())
    dex_entries = []
    for idx, src in enumerate(our_dexes + deps_dexes):
        dex_entries.append((src, "classes.dex" if idx == 0 else "classes%d.dex" % (idx + 1)))
    with zipfile.ZipFile(WORK_APK, "a", zipfile.ZIP_STORED) as z:
        for src, name in dex_entries:
            z.write(src, name)
    print("[OK] 打入 %d 个 dex:" % len(dex_entries))
    for src, name in dex_entries:
        print("     %-14s <- %-26s %10d bytes" % (name, os.path.relpath(src, OUT), os.path.getsize(src)))

    # 3. zipalign + 签名
    rename_away(ALIGNED_APK)
    if not run([ZIPALIGN, "-f", "4", WORK_APK, ALIGNED_APK], "zipalign"):
        sys.exit(1)
    rename_away(SIGNED_APK)
    if not run([APKSIGNER, "sign", "--ks", KEYSTORE, "--ks-pass", "pass:android",
                "--ks-key-alias", "androiddebugkey", "--key-pass", "pass:android",
                "--out", SIGNED_APK, ALIGNED_APK], "apksigner"):
        sys.exit(1)

    sz = os.path.getsize(SIGNED_APK)
    print("\n=== SUCCESS ===\n%s (%.1f MB)" % (SIGNED_APK, sz / 1024 / 1024))
    with zipfile.ZipFile(SIGNED_APK) as z:
        for i in z.infolist():
            print("  %-28s %12d %s" % (i.filename, i.file_size,
                                       "STORED" if i.compress_type == 0 else "DEFLATE"))
    cache.summary()


if __name__ == "__main__":
    main()
