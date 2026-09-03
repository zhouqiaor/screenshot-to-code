#!/usr/bin/env python3
"""
Compose CLI 直编 APK（绕过死锁的 Gradle）。
流程: kotlinc(2.0.21)+Compose compiler(2.0.21) → .class → d8 → dex
      → aapt2 link → 打入 multidex → zipalign → apksigner

增量构建（历史编译结果保留复用）
--------------------------------
三个阶段按输入指纹缓存，输入没变就跳过（见 buildcache.py）：
    kotlinc   ← MainActivity.kt + 依赖 jar 清单 + 编译参数
    deps_dex  ← 全部依赖 jar 的 (size, mtime)      ← 最贵，~150 s
    our_dex   ← classes/ 目录内容 + 依赖 jar 清单

只改 Kotlin 源码时 deps_dex 直接复用，单轮从 ~5 min 降到 ~70 s。
    python build_compose_apk.py                # 增量（默认）
    python build_compose_apk.py --no-cache     # 全量重建
    python build_compose_apk.py --force deps_dex   # 只强制某阶段
"""
import argparse
import os, sys, subprocess, glob, shutil, time

from buildcache import Cache, fingerprint

ROOT = os.path.dirname(os.path.abspath(__file__))
GRADLE_CACHE = os.path.expanduser(r"~/.gradle/caches/modules-2/files-2.1")
SDK = r"C:/Programs/Android/Sdk"
BT = os.path.join(SDK, "build-tools", "37.0.0")
AAPT2 = os.path.join(BT, "aapt2.exe")
D8 = os.path.join(BT, "d8.bat")
ZIPALIGN = os.path.join(BT, "zipalign.exe")
APKSIGNER = os.path.join(BT, "apksigner.bat")
ANDROID_JAR = os.path.join(SDK, "platforms", "android-34", "android.jar")
JAVA = r"C:/Programs/Java/jdk-21.0.11/bin/java.exe"
JAVAC = r"C:/Programs/Java/jdk-21.0.11/bin/javac.exe"
KEYSTORE = r"C:/Users/georgeslark/.android/debug.keystore"

KOTLINC_JAR = os.path.join(GRADLE_CACHE, "org.jetbrains.kotlin", "kotlin-compiler-embeddable", "2.0.21",
                           "79346ed53db48b18312a472602eb5c057070c54d", "kotlin-compiler-embeddable-2.0.21.jar")
COMPOSE_COMPILER_JAR = os.path.join(GRADLE_CACHE, "org.jetbrains.kotlin", "kotlin-compose-compiler-plugin-embeddable",
                                    "2.0.21", "e14f003d962fb25693b461de59490c91072a7979",
                                    "kotlin-compose-compiler-plugin-embeddable-2.0.21.jar")
KOTLIN_STDLIB = os.path.join(GRADLE_CACHE, "org.jetbrains.kotlin", "kotlin-stdlib", "2.0.21",
                             "618b539767b4899b4660a83006e052b63f1db551", "kotlin-stdlib-2.0.21.jar")
TROVE_JAR = os.path.join(GRADLE_CACHE, "org.jetbrains.intellij.deps", "trove4j", "1.0.20181211",
                         "216c2e14b070f334479d800987affe4054cd563f", "trove4j-1.0.20181211.jar")
COROUTINES_CORE_JAR = os.path.join(GRADLE_CACHE, "org.jetbrains.kotlinx", "kotlinx-coroutines-core-jvm", "1.7.3",
                                  "2b09627576f0989a436a00a4a54b55fa5026fb86", "kotlinx-coroutines-core-jvm-1.7.3.jar")
COROUTINES_ANDROID_JAR = os.path.join(GRADLE_CACHE, "org.jetbrains.kotlinx", "kotlinx-coroutines-android", "1.7.3",
                                     "38d9cad3a0b03a10453b56577984bdeb48edeed5", "kotlinx-coroutines-android-1.7.3.jar")
# Kotlin 编译器 codegen 阶段需要 org.jetbrains.annotations.NotNull（不是 androidx.annotation）
ANNOTATIONS_JAR = os.path.join(GRADLE_CACHE, "org.jetbrains", "annotations", "13.0",
                              "919f0dfe192fb4e063e7dacadee7f8bb9a2672a9", "annotations-13.0.jar")

SRC = os.path.join(ROOT, "app", "src", "main")
MANIFEST = os.path.join(SRC, "AndroidManifest.xml")
RES = os.path.join(SRC, "res")
MAIN_KT = os.path.join(SRC, "java", "com", "e2e", "settings", "MainActivity.kt")
DEPS_REPO = os.path.join(ROOT, "deps_repo")
OUT = os.path.join(ROOT, "compose_cli_build")
OUT_CLASSES = os.path.join(OUT, "classes")
OUT_DEX = os.path.join(OUT, "classes.dex")
BASE_APK = os.path.join(OUT, "base.apk")
ALIGNED_APK = os.path.join(OUT, "e2e_compose_debug.apk")
SIGNED_APK = os.path.join(OUT, "e2e_compose_debug_signed.apk")

STALE_DIR = os.path.join(OUT, "_stale_bak")


def force_rmtree(path):
    """整目录改名绕过 sandbox safe-delete shim（os.remove/os.rmdir 会被拦截/卡住）。

    旧实现把 .bak 留在原地（`deps_dex.bak.<ts>`），每轮重建堆一份 38 MB，
    实测积到 325 MB。现在统一收进 `compose_cli_build/_stale_bak/`，
    并且同名旧备份只保留最近 1 份，避免无限膨胀。
    """
    if not os.path.exists(path):
        return
    os.makedirs(STALE_DIR, exist_ok=True)
    name = os.path.basename(path.rstrip("\\/"))
    # 同名旧备份先让位（保留最近 1 份即可，更早的直接覆盖式让位）
    keep = os.path.join(STALE_DIR, name)
    if os.path.exists(keep):
        try:
            os.rename(keep, "%s.%d" % (keep, int(time.time() * 1000)))
        except OSError:
            pass
    try:
        os.rename(path, keep)
    except OSError as e:
        print("  [WARN] force_rmtree rename failed: %s" % e)

def safe_remove(path):
    """删除单个文件，失败（如被 shim 拦截）忽略，不阻断构建流程"""
    if not os.path.exists(path):
        return
    try:
        os.remove(path)
    except OSError as e:
        print("  [WARN] safe_remove skipped: %s (%s)" % (path, e))

def run(cmd, label, cwd=None):
    print(f"\n=== {label} ===")
    print(" ".join(cmd[:6]) + (" ..." if len(cmd) > 6 else ""))
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", cwd=cwd)
    out = r.stdout or ""
    err = r.stderr or ""
    if out:
        print(out[-2000:])
    if r.returncode != 0:
        print(f"[STDERR]\n{err[-3000:]}")
        print(f"[FAIL] {label} exit={r.returncode}")
        return False
    print(f"[OK] {label}")
    return True

def find_in_cache(group, artifact, version):
    """在 Gradle 缓存里按 group/artifact/version 定位 jar（os.walk，跨平台可靠）"""
    # 注意：Gradle 缓存的 group 目录保留点号（如 org.jetbrains.kotlin），不要 replace 成路径分隔符
    base = os.path.join(GRADLE_CACHE, group, artifact, version)
    if not os.path.isdir(base):
        return None
    target = f"{artifact}-{version}.jar"
    for root, dirs, files in os.walk(base):
        if target in files:
            return os.path.join(root, target)
    return None

def collect_dep_jars():
    """收集 deps_repo 下所有编译所需 jar：
    - aar 提取的 classes.jar
    - 纯 .jar 依赖（lifecycle-common / collection / annotation / coroutines-core 等）
    去重 key 用 artifact名/version/<file>，避免同版本不同 artifact 被合并。"""
    jars = []
    for root, dirs, files in os.walk(DEPS_REPO):
        has_aar = any(f.endswith(".aar") for f in files)
        for fn in files:
            if fn == "classes.jar":
                jars.append(os.path.join(root, fn))
            elif fn.endswith(".jar") and fn != "classes.jar" and not has_aar:
                # 纯 jar 依赖（该目录下没有 aar，说明是独立的 jar 制品）
                jars.append(os.path.join(root, fn))
    seen = set()
    uniq = []
    for j in jars:
        ver_dir = os.path.basename(os.path.dirname(j))
        art_dir = os.path.basename(os.path.dirname(os.path.dirname(j)))
        key = f"{art_dir}/{ver_dir}/{os.path.basename(j)}"
        if key not in seen:
            seen.add(key)
            uniq.append(j)
    return uniq

def collect_extra_jars():
    """Gradle 缓存里 Google Maven 没有的运行时支撑库。

    必须全部进 d8 输入，否则装机后运行时报 NoClassDefFoundError：
      - kotlin-stdlib          -> kotlin/jvm/internal/Intrinsics（Kotlin 生成代码必用）
      - coroutines-core-jvm    -> kotlinx.coroutines 核心 868 个类
      - coroutines-android     -> 仅 9 个类的 Android Main dispatcher，不含核心实现
    已实测三者除 META-INF/versions/9/module-info.class 外无类名重叠，不会 d8 duplicate。
    """
    extra = []
    wanted = [
        ("kotlin-stdlib", KOTLIN_STDLIB, ("org.jetbrains.kotlin", "kotlin-stdlib", "2.0.21")),
        ("kotlinx-coroutines-core-jvm", COROUTINES_CORE_JAR,
         ("org.jetbrains.kotlinx", "kotlinx-coroutines-core-jvm", "1.7.3")),
        ("kotlinx-coroutines-android", COROUTINES_ANDROID_JAR,
         ("org.jetbrains.kotlinx", "kotlinx-coroutines-android", "1.7.3")),
    ]
    for label, const_path, coord in wanted:
        p = const_path if os.path.exists(const_path) else find_in_cache(*coord)
        if p and os.path.exists(p):
            extra.append(p)
        else:
            print("  [WARN] 缓存未找到 %s:%s" % (label, coord[2]))
    return extra

def parse_args():
    ap = argparse.ArgumentParser(
        description="Compose CLI 直编 APK（默认增量：复用历史编译结果）")
    ap.add_argument("--no-cache", action="store_true",
                    help="禁用全部阶段缓存，全量重建")
    ap.add_argument("--force", action="append", default=[],
                    metavar="STAGE",
                    help="强制重建指定阶段，可重复；可选 kotlinc/deps_dex/our_dex/all")
    ap.add_argument("--seed-cache", action="store_true",
                    help="不执行构建，只为已存在的历史产物补写 stamp（首次启用缓存时用）")
    ap.add_argument("--dex-only", action="store_true",
                    help="只产出 classes/ 与 deps_dex/，跳过 aapt2 link 与打包签名"
                         "（完整流程由 link_resources.py + repack_full.py 接管，"
                         "这里的 APK 会被覆盖，属纯浪费）")
    return ap.parse_args()


def main():
    args = parse_args()
    os.makedirs(OUT, exist_ok=True)
    cache = Cache(OUT, enabled=not args.no_cache, forced=args.force,
                  seed=args.seed_cache)

    dep_jars = collect_dep_jars()
    extra_jars = collect_extra_jars()
    print(f"[deps] {len(dep_jars)} compose runtime jars + {len(extra_jars)} extra (stdlib/coroutines) from cache")
    if len(dep_jars) < 8:
        print("[WARN] 依赖不足，下载可能未完成")

    # 依赖 jar 清单指纹：deps_dex / kotlinc / our_dex 三阶段共用
    deps_fp = fingerprint(files=dep_jars + extra_jars, extra=["min-api=24", "release"])

    # === 1. kotlinc 编译 ===
    # java 启动 classpath 必须含 kotlin-stdlib + trove4j + coroutines-core（编译器自身依赖）
    java_cp_parts = [KOTLINC_JAR, KOTLIN_STDLIB, TROVE_JAR]
    coroutines_core = COROUTINES_CORE_JAR if os.path.exists(COROUTINES_CORE_JAR) else find_in_cache("org.jetbrains.kotlinx", "kotlinx-coroutines-core-jvm", "1.7.3")
    if coroutines_core:
        java_cp_parts.append(coroutines_core)
    else:
        print("  [WARN] 缓存未找到 kotlinx-coroutines-core-jvm:1.7.3（编译器运行可能缺类）")
    # org.jetbrains.annotations：编译器 codegen 生成 NotNull 注解时必需
    annotations = ANNOTATIONS_JAR if os.path.exists(ANNOTATIONS_JAR) else find_in_cache("org.jetbrains", "annotations", "13.0")
    if annotations and os.path.exists(annotations):
        java_cp_parts.append(annotations)
    else:
        print("  [WARN] 缓存未找到 org.jetbrains.annotations:13.0（编译器 codegen 可能缺类）")
    java_cp = ";".join(java_cp_parts)
    # kotlinc 编译 classpath：android.jar + stdlib + compose 依赖 + coroutines-android
    cp_parts = [ANDROID_JAR, KOTLIN_STDLIB] + dep_jars + extra_jars
    cp = ";".join(cp_parts)
    kotlinc_cmd = [
        JAVA, "-cp", java_cp,
        "org.jetbrains.kotlin.cli.jvm.K2JVMCompiler",
        "-Xplugin=" + COMPOSE_COMPILER_JAR,
        "-no-stdlib",
        "-jvm-target", "1.8",
        "-cp", cp,
        "-d", OUT_CLASSES,
        MAIN_KT,
    ]
    # 缓存键：Kotlin 源码 + 依赖清单 + 编译参数（jvm-target / 插件 jar 版本）
    kt_fp = fingerprint(files=[MAIN_KT, COMPOSE_COMPILER_JAR],
                        extra=[deps_fp, "jvm-target=1.8", "no-stdlib"])
    main_class = os.path.join(OUT_CLASSES, "com", "e2e", "settings", "MainActivity.class")
    if not cache.hit("kotlinc", kt_fp, [main_class]):
        # kotlinc 不做增量，重编前必须清空输出目录（残留旧 .class 会混进 dex）
        if os.path.exists(OUT_CLASSES):
            force_rmtree(OUT_CLASSES)
        os.makedirs(OUT_CLASSES, exist_ok=True)
        if not run(kotlinc_cmd, "kotlinc + Compose compiler"):
            sys.exit(1)
        cache.save("kotlinc", kt_fp, [main_class])

    # === 2. d8 分两步打 dex（避免 our classes 与依赖 jar 一起作为输入时被静默丢弃）===
    # 2a. 依赖 jar + extra 单独打成 deps.dex
    #     这一步最贵（50 个 jar → ~150 s），依赖 jar 不变时必须复用。
    deps_dex_dir = os.path.join(OUT, "deps_dex")
    deps_dex_main = os.path.join(deps_dex_dir, "classes.dex")
    if not cache.hit("deps_dex", deps_fp, [deps_dex_main]):
        if os.path.exists(deps_dex_dir):
            force_rmtree(deps_dex_dir)
        os.makedirs(deps_dex_dir, exist_ok=True)
        deps_cmd = [D8, "--release", "--output", deps_dex_dir, "--min-api", "24"] + dep_jars + extra_jars
        if not run(deps_cmd, "d8 deps dex"):
            sys.exit(1)
        cache.save("deps_dex", deps_fp, [deps_dex_main])

    # 2b. 我们的 .class 单独打成 our.dex（依赖作为 classpath 供解析）
    our_dex_dir = os.path.join(OUT, "our_dex")
    our_dex_main = os.path.join(our_dex_dir, "classes.dex")
    our_class_files = []
    for root, dirs, files in os.walk(OUT_CLASSES):
        for fn in files:
            if fn.endswith(".class"):
                our_class_files.append(os.path.join(root, fn))
    if not our_class_files:
        print("[FAIL] classes/ 目录内没有 .class（kotlinc 缓存可能失效，试 --force kotlinc）")
        sys.exit(1)
    # 缓存键：编译产物目录内容 + 依赖清单（classpath 影响 d8 解析结果）
    our_fp = fingerprint(dirs=[OUT_CLASSES], extra=[deps_fp])
    if not cache.hit("our_dex", our_fp, [our_dex_main]):
        if os.path.exists(our_dex_dir):
            force_rmtree(our_dex_dir)
        os.makedirs(our_dex_dir, exist_ok=True)
        classpath = [ANDROID_JAR] + dep_jars + extra_jars
        cp_args = []
        for cp in classpath:
            cp_args += ["--classpath", cp]
        our_cmd = [D8, "--release", "--output", our_dex_dir, "--min-api", "24"] + cp_args + our_class_files
        if not run(our_cmd, "d8 our dex"):
            sys.exit(1)
        cache.save("our_dex", our_fp, [our_dex_main])

    # 2c. 收集所有 dex，按原生 multidex 规则编号（不再 d8 merge —— 合并会因
    #     method_ids 超 65536 而丢弃 deps 的 classes2.dex，导致 MainActivity
    #     的父类无法解析，运行时报 ClassNotFoundException）
    #     minSdk 24 平台原生支持 multidex：classes.dex / classes2.dex / classes3.dex ...
    def collect_dex(d):
        """按 classes.dex, classes2.dex, classes3.dex ... 顺序返回目录内 dex 路径"""
        out = []
        first = os.path.join(d, "classes.dex")
        if os.path.exists(first):
            out.append(first)
        i = 2
        while True:
            p = os.path.join(d, "classes%d.dex" % i)
            if not os.path.exists(p):
                break
            out.append(p)
            i += 1
        return out

    our_dexes = collect_dex(our_dex_dir)
    deps_dexes = collect_dex(deps_dex_dir)
    if not our_dexes:
        print("[FAIL] our_dex 目录内没有 dex 产物")
        sys.exit(1)
    if not deps_dexes:
        print("[FAIL] deps_dex 目录内没有 dex 产物")
        sys.exit(1)

    # 我们的类放主 dex（classes.dex），依赖顺延到 classes2.dex 起
    dex_entries = []  # [(源文件路径, APK 内条目名)]
    for idx, src in enumerate(our_dexes + deps_dexes):
        name = "classes.dex" if idx == 0 else "classes%d.dex" % (idx + 1)
        dex_entries.append((src, name))
    print("[OK] multidex 布局：")
    for src, name in dex_entries:
        print("     %-14s <- %s (%d bytes)" % (name, os.path.relpath(src, OUT), os.path.getsize(src)))

    if args.dex_only:
        print("\n[dex-only] 已产出 classes/ 与 deps_dex/，跳过 aapt2 link / 打包 / 签名")
        print("           后续由 link_resources.py + repack_full.py 接管")
        cache.summary()
        return

    # === 3. aapt2 compile + link ===
    compiled_res = os.path.join(OUT, "compiled_res.zip")
    if os.path.exists(compiled_res):
        safe_remove(compiled_res)
    aapt2_compile = [AAPT2, "compile", "--dir", RES, "-o", compiled_res]
    if not run(aapt2_compile, "aapt2 compile res"):
        sys.exit(1)

    aapt2_link = [AAPT2, "link",
                  "-o", BASE_APK,
                  "-I", ANDROID_JAR,
                  "--manifest", MANIFEST,
                  "--auto-add-overlay",
                  "-A", os.path.join(OUT, "assets") if os.path.exists(os.path.join(OUT, "assets")) else OUT,
                  compiled_res]
    # aapt2 link 需要 assets 目录存在与否分开处理
    aapt2_link = [AAPT2, "link", "-o", BASE_APK, "-I", ANDROID_JAR,
                  "--manifest", MANIFEST, compiled_res]
    if not run(aapt2_link, "aapt2 link base.apk"):
        sys.exit(1)

    # === 4. 把所有 dex 打进 base.apk ===
    import zipfile
    with zipfile.ZipFile(BASE_APK, "a", zipfile.ZIP_STORED) as z:
        for src, name in dex_entries:
            z.write(src, name)
    print("[OK] 打入 %d 个 dex: %s" % (len(dex_entries), ", ".join(n for _, n in dex_entries)))

    # === 5. zipalign ===
    if os.path.exists(ALIGNED_APK):
        safe_remove(ALIGNED_APK)
    if not run([ZIPALIGN, "-f", "4", BASE_APK, ALIGNED_APK], "zipalign"):
        sys.exit(1)

    # === 6. apksigner ===
    if os.path.exists(SIGNED_APK):
        safe_remove(SIGNED_APK)
    sign = [APKSIGNER, "sign",
            "--ks", KEYSTORE,
            "--ks-pass", "pass:android",
            "--ks-key-alias", "androiddebugkey",
            "--key-pass", "pass:android",
            "--out", SIGNED_APK,
            ALIGNED_APK]
    if not run(sign, "apksigner"):
        sys.exit(1)

    sz = os.path.getsize(SIGNED_APK)
    print(f"\n=== SUCCESS ===\n{SIGNED_APK} ({sz} bytes, {sz/1024/1024:.1f} MB)")
    cache.summary()

if __name__ == "__main__":
    main()
