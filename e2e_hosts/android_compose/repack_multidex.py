#!/usr/bin/env python3
"""
快速重打包（复用已有 dex 产物，跳过 kotlinc）。

用途：验证「原生 multidex 打包」能否修掉设备上的
     ClassNotFoundException: com.e2e.settings.MainActivity

背景：d8 merge deps_dex/classes.dex + our_dex/classes.dex 时，deps 的
     classes2.dex（4.4MB）被漏掉，导致 MainActivity 的父类
     androidx.activity.ComponentActivity 无法解析 → ART 拒绝定义该类。
     minSdk 24 原生支持 multidex，直接按 classes.dex / classes2.dex /
     classes3.dex 顺序全部打进 APK 即可。
"""
import os, sys, subprocess, zipfile, time

ROOT = os.path.dirname(os.path.abspath(__file__))
SDK = r"C:/Programs/Android/Sdk"
BT = os.path.join(SDK, "build-tools", "37.0.0")
AAPT2 = os.path.join(BT, "aapt2.exe")
ZIPALIGN = os.path.join(BT, "zipalign.exe")
APKSIGNER = os.path.join(BT, "apksigner.bat")
ANDROID_JAR = os.path.join(SDK, "platforms", "android-34", "android.jar")
KEYSTORE = r"C:/Users/georgeslark/.android/debug.keystore"

SRC = os.path.join(ROOT, "app", "src", "main")
MANIFEST = os.path.join(SRC, "AndroidManifest.xml")
RES = os.path.join(SRC, "res")
OUT = os.path.join(ROOT, "compose_cli_build")
BASE_APK = os.path.join(OUT, "base_md.apk")
ALIGNED_APK = os.path.join(OUT, "e2e_compose_md.apk")
SIGNED_APK = os.path.join(OUT, "e2e_compose_md_signed.apk")


def run(cmd, label):
    print("\n>>> %s" % label)
    print("    " + " ".join('"%s"' % c if " " in c else c for c in cmd[:6]) +
          (" ... (+%d args)" % (len(cmd) - 6) if len(cmd) > 6 else ""))
    p = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if p.stdout and p.stdout.strip():
        print(p.stdout.strip()[:2000])
    if p.returncode != 0:
        print("[FAIL] rc=%d" % p.returncode)
        if p.stderr:
            print(p.stderr.strip()[:3000])
        return False
    if p.stderr and p.stderr.strip():
        print("[stderr] " + p.stderr.strip()[:800])
    print("[OK] %s" % label)
    return True


def safe_remove(path):
    if not os.path.exists(path):
        return
    try:
        os.rename(path, "%s.old.%d" % (path, int(time.time() * 1000)))
    except OSError as e:
        print("  [WARN] safe_remove skipped: %s (%s)" % (path, e))


def collect_dex(d):
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


def main():
    our_dexes = collect_dex(os.path.join(OUT, "our_dex"))
    deps_dexes = collect_dex(os.path.join(OUT, "deps_dex"))
    print("our_dex : %s" % [os.path.basename(p) for p in our_dexes])
    print("deps_dex: %s" % [os.path.basename(p) for p in deps_dexes])
    if not our_dexes or not deps_dexes:
        print("[FAIL] 缺少 dex 产物，请先跑 build_compose_apk.py")
        sys.exit(1)

    dex_entries = []
    for idx, src in enumerate(our_dexes + deps_dexes):
        name = "classes.dex" if idx == 0 else "classes%d.dex" % (idx + 1)
        dex_entries.append((src, name))
    print("\nmultidex 布局：")
    for src, name in dex_entries:
        print("  %-14s <- %-24s %10d bytes" % (name, os.path.relpath(src, OUT), os.path.getsize(src)))

    # 1. aapt2 compile + link
    compiled_res = os.path.join(OUT, "compiled_res_md.zip")
    safe_remove(compiled_res)
    if not run([AAPT2, "compile", "--dir", RES, "-o", compiled_res], "aapt2 compile res"):
        sys.exit(1)
    safe_remove(BASE_APK)
    if not run([AAPT2, "link", "-o", BASE_APK, "-I", ANDROID_JAR,
                "--manifest", MANIFEST, compiled_res], "aapt2 link base_md.apk"):
        sys.exit(1)

    # 2. 打入全部 dex（STORED，保持 4 字节对齐友好）
    with zipfile.ZipFile(BASE_APK, "a", zipfile.ZIP_STORED) as z:
        for src, name in dex_entries:
            z.write(src, name)
    print("\n[OK] 打入 %d 个 dex: %s" % (len(dex_entries), ", ".join(n for _, n in dex_entries)))

    # 3. zipalign
    safe_remove(ALIGNED_APK)
    if not run([ZIPALIGN, "-f", "4", BASE_APK, ALIGNED_APK], "zipalign"):
        sys.exit(1)

    # 4. apksigner
    safe_remove(SIGNED_APK)
    if not run([APKSIGNER, "sign",
                "--ks", KEYSTORE,
                "--ks-pass", "pass:android",
                "--ks-key-alias", "androiddebugkey",
                "--key-pass", "pass:android",
                "--out", SIGNED_APK, ALIGNED_APK], "apksigner"):
        sys.exit(1)

    sz = os.path.getsize(SIGNED_APK)
    print("\n=== SUCCESS ===\n%s (%d bytes, %.1f MB)" % (SIGNED_APK, sz, sz / 1024 / 1024))
    with zipfile.ZipFile(SIGNED_APK) as z:
        for i in z.infolist():
            print("  %-30s %12d %s" % (i.filename, i.file_size,
                                       "STORED" if i.compress_type == 0 else "DEFLATE"))


if __name__ == "__main__":
    main()
