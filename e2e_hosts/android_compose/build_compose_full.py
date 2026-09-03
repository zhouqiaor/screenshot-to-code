#!/usr/bin/env python3
"""Compose 真机 APK 一站式构建（绕过 Gradle 死锁）。

执行三步：
  1. build_compose_apk.py —— kotlinc + Compose 插件编译业务代码；d8 依赖 dex；aapt2 应用资源
  2. link_resources.py    —— aapt2 compile/link 全部 38 个库资源；生成 484 个 R 类
  3. repack_full.py       —— 把业务/R 类打成 our.dex，与依赖 dex 一起塞进 base_res.apk 并签名

产物：compose_cli_build/e2e_compose_full_signed.apk

增量构建（默认开启）
--------------------
历史编译结果保留在 compose_cli_build/ 内，按输入指纹复用（见 buildcache.py）：
    阶段        缓存键                             全量耗时
    kotlinc     MainActivity.kt + 依赖清单          ~60 s
    deps_dex    全部依赖 jar 的 size/mtime          ~150 s  ← 最贵
    link_res    38 个库 res/ + app res + manifest   ~90 s
    our_r_dex   业务 .class + R .class              ~15 s
只改 Kotlin 源码 → 仅 kotlinc + our_r_dex 重跑，单轮 ~5 min → ~70 s。
只换主题/资源  → 仅 link_res + our_r_dex 重跑。
什么都没改     → 4 个阶段全命中，只重打包签名（~20 s）。

用法：
    python build_compose_full.py                    # 增量（默认，推荐）
    python build_compose_full.py --no-cache         # 全量重建（怀疑缓存不一致时）
    python build_compose_full.py --force deps_dex   # 只强制某个阶段
    python build_compose_full.py --force all        # 等价于 --no-cache

前置：
  - Android SDK build-tools 37.0.0（aapt2/d8/zipalign/apksigner）
  - JDK 21
  - Kotlin 2.0.21 + Compose 编译器插件 2.0.21（在 Gradle 缓存里）
  - deps_repo/ 已下载全部 Compose 依赖（运行 fetch_compose_deps_v2.py）
"""
import argparse
import subprocess, sys, os, time

ROOT = os.path.dirname(os.path.abspath(__file__))

# 各步骤支持的缓存阶段名，用于把 --force 精确路由到对应脚本
STAGE_OWNER = {
    "kotlinc": "build_compose_apk.py",
    "deps_dex": "build_compose_apk.py",
    "our_dex": "build_compose_apk.py",
    "link_res": "link_resources.py",
    "our_r_dex": "repack_full.py",
}


def run(script, label, extra_args):
    print("\n" + "=" * 60)
    print("STEP:", label)
    print("=" * 60)
    t0 = time.time()
    p = subprocess.run([sys.executable, "-u", script] + extra_args,
                       cwd=ROOT, text=True, encoding="utf-8", errors="replace")
    dt = time.time() - t0
    if p.returncode != 0:
        print("[FAIL] %s failed with rc=%d（耗时 %.1f s）" % (label, p.returncode, dt))
        sys.exit(1)
    print("[OK] %s（耗时 %.1f s）" % (label, dt))
    return dt


def main():
    ap = argparse.ArgumentParser(description="Compose CLI 直编 APK 一站式构建（默认增量）")
    ap.add_argument("--no-cache", action="store_true", help="禁用全部阶段缓存，全量重建")
    ap.add_argument("--force", action="append", default=[], metavar="STAGE",
                    help="强制重建指定阶段：%s 或 all" % "/".join(STAGE_OWNER))
    ap.add_argument("--seed-cache", action="store_true",
                    help="把已存在的历史产物纳管为缓存（首次启用缓存时跑一次即可）")
    args = ap.parse_args()

    unknown = [s for s in args.force if s not in STAGE_OWNER and s != "all"]
    if unknown:
        print("[FAIL] 未知阶段名：%s\n可选：%s, all" % (", ".join(unknown), ", ".join(STAGE_OWNER)))
        sys.exit(2)

    def args_for(script):
        """只把属于该脚本的 --force 传下去，避免脚本收到不认识的阶段名。"""
        out = ["--no-cache"] if args.no_cache else []
        if args.seed_cache:
            out.append("--seed-cache")
        for s in args.force:
            if s == "all" or STAGE_OWNER.get(s) == script:
                out += ["--force", s]
        return out

    t_all = time.time()
    times = []
    # --dex-only：这一步只要 classes/ 与 deps_dex/；它自带的 aapt2 link 与签名
    # 产物会被 repack_full.py 完全覆盖，跑了纯浪费（~40 s + 60 MB 冗余）
    times.append(("业务编译 + 依赖 dex", run(
        "build_compose_apk.py",
        "业务代码编译 + 依赖 dex（kotlinc → d8）",
        args_for("build_compose_apk.py") + ["--dex-only"])))
    times.append(("库资源链接 + R 类", run(
        "link_resources.py",
        "库资源链接 + R 类生成（aapt2 compile/link → javac）",
        args_for("link_resources.py"))))
    times.append(("完整打包 + 签名", run(
        "repack_full.py",
        "完整 APK 打包（base_res.apk + our dex + deps dex + sign）",
        args_for("repack_full.py"))))

    print("\n=== ALL DONE（总耗时 %.1f s）===" % (time.time() - t_all))
    for name, dt in times:
        print("  %-22s %6.1f s" % (name, dt))
    print("\nAPK: compose_cli_build/e2e_compose_full_signed.apk")
    print("安装: adb install -r compose_cli_build/e2e_compose_full_signed.apk")
    print("启动: adb shell am start -n com.e2e.settings/.MainActivity")
    print("截图: adb shell screencap -p /sdcard/compose.png && adb pull /sdcard/compose.png")


if __name__ == "__main__":
    main()
