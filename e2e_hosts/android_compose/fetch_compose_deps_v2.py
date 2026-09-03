#!/usr/bin/env python3
"""精确清单批量下载 Compose 1.7.3 的 -android 变体 + 支撑库。直接列，不 BFS。"""
import os, urllib.request, urllib.error, zipfile, io, time

MAVEN = "https://maven.google.com"
REPO = os.path.join(os.path.dirname(os.path.abspath(__file__)), "deps_repo")
os.makedirs(REPO, exist_ok=True)

# (group, artifact, version) — 优先 -android 变体（含 classes.jar）
ARTIFACTS = [
    # Compose runtime
    ("androidx.compose.runtime", "runtime-android", "1.7.3"),
    ("androidx.compose.runtime", "runtime-saveable-android", "1.7.3"),
    ("androidx.compose.runtime", "runtime", "1.7.3"),  # 元包，含 manifest
    # Compose ui
    ("androidx.compose.ui", "ui-android", "1.7.3"),
    ("androidx.compose.ui", "ui-graphics-android", "1.7.3"),
    ("androidx.compose.ui", "ui-text-android", "1.7.3"),
    ("androidx.compose.ui", "ui-unit-android", "1.7.3"),
    ("androidx.compose.ui", "ui-tooling-preview-android", "1.7.3"),
    ("androidx.compose.ui", "ui-util-android", "1.7.3"),
    ("androidx.compose.ui", "ui", "1.7.3"),
    # Compose foundation
    ("androidx.compose.foundation", "foundation-android", "1.7.3"),
    ("androidx.compose.foundation", "foundation-layout-android", "1.7.3"),
    # Compose animation
    ("androidx.compose.animation", "animation-android", "1.7.3"),
    ("androidx.compose.animation", "animation-core-android", "1.7.3"),
    # Compose material3
    ("androidx.compose.material3", "material3-android", "1.3.0"),
    # Compose material icons
    ("androidx.compose.material", "material-icons-extended-android", "1.7.3"),
    ("androidx.compose.material", "material-icons-core-android", "1.7.3"),
    # Activity
    ("androidx.activity", "activity", "1.9.2"),
    ("androidx.activity", "activity-compose", "1.9.2"),
    ("androidx.activity", "activity-ktx", "1.9.2"),
    # Core
    ("androidx.core", "core", "1.13.1"),
    ("androidx.core", "core-ktx", "1.13.1"),
    # Lifecycle
    ("androidx.lifecycle", "lifecycle-runtime-android", "2.8.4"),
    ("androidx.lifecycle", "lifecycle-viewmodel-android", "2.8.4"),
    ("androidx.lifecycle", "lifecycle-viewmodel-compose-android", "2.8.4"),
    ("androidx.lifecycle", "lifecycle-common", "2.8.4"),
    ("androidx.lifecycle", "lifecycle-common-java8", "2.8.4"),
    ("androidx.lifecycle", "lifecycle-runtime-ktx", "2.8.4"),
    # Savedstate / collection / annotation / tracing / profileinstaller / startup
    # 只保留 aar 变体，避免与 -jvm 兄弟重复造成 classpath 冲突
    ("androidx.savedstate", "savedstate", "1.2.1"),
    ("androidx.collection", "collection", "1.4.0"),
    ("androidx.annotation", "annotation", "1.7.0"),
    ("androidx.annotation", "annotation-experimental", "1.3.1"),
    ("androidx.tracing", "tracing", "1.1.0"),
    ("androidx.profileinstaller", "profileinstaller", "1.3.1"),
    ("androidx.startup", "startup-runtime", "1.1.1"),
    # Kotlinx coroutines（仅 android 变体）
    ("org.jetbrains.kotlinx", "kotlinx-coroutines-android", "1.7.3"),
]

def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
            if attempt == 2:
                return None
            time.sleep(2)
        except Exception:
            if attempt == 2:
                return None
            time.sleep(2)
    return None

def main():
    ok = 0; fail = []
    for (g, a, v) in ARTIFACTS:
        gp = g.replace(".", "/")
        base = f"{MAVEN}/{gp}/{a}/{v}/{a}-{v}"
        data = fetch(base + ".aar")
        ext = ".aar"
        if data is None:
            data = fetch(base + ".jar")
            ext = ".jar"
        if data is None:
            data = fetch(base + ".pom")  # 至少确认存在
            ext = ".pom"
        if data is None:
            fail.append(f"{g}:{a}:{v} (404)")
            print(f"  [404] {g}:{a}:{v}")
            continue
        out_dir = os.path.join(REPO, g.replace(".", "_"), a, v)
        os.makedirs(out_dir, exist_ok=True)
        with open(os.path.join(out_dir, a + ext), "wb") as f:
            f.write(data)
        # 从 aar 提取 classes.jar + res + manifest
        if ext == ".aar":
            try:
                zf = zipfile.ZipFile(io.BytesIO(data))
                if "classes.jar" in zf.namelist():
                    with open(os.path.join(out_dir, "classes.jar"), "wb") as f:
                        f.write(zf.read("classes.jar"))
                for n in zf.namelist():
                    # libs/*.jar 必须一起提取：部分 aar（如 emoji2）把
                    # androidx/emoji2/text/flatbuffer 的实现放在 libs/repackaged.jar，
                    # 只取 classes.jar 会导致装机后 NoClassDefFoundError。
                    if (n.startswith("res/") or n == "AndroidManifest.xml"
                            or n.startswith("assets/")
                            or (n.startswith("libs/") and n.endswith(".jar"))):
                        zf.extract(n, out_dir)
            except Exception as e:
                print(f"  [extract err] {g}:{a}:{v}: {e}")
        ok += 1
        has_cls = "classes.jar" if os.path.exists(os.path.join(out_dir, "classes.jar")) else "no-cls"
        print(f"  [OK {ext} {has_cls}] {g}:{a}:{v} ({len(data)}B)")
    # 汇总 classpath
    classes_jars = []
    for root, dirs, files in os.walk(REPO):
        for fn in files:
            if fn == "classes.jar":
                classes_jars.append(os.path.join(root, fn))
    with open(os.path.join(REPO, "classpath.txt"), "w") as f:
        f.write(";".join(classes_jars))
    print(f"\n=== {ok}/{len(ARTIFACTS)} downloaded, {len(classes_jars)} classes.jar ===")
    if fail:
        print(f"=== FAILED ({len(fail)}) ===")
        for fl in fail: print("  " + fl)

if __name__ == "__main__":
    main()
