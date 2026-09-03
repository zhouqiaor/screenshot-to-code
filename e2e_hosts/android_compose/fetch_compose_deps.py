#!/usr/bin/env python3
"""
从 Google Maven (maven.google.com) 手动下载 Compose 依赖并提取 classes.jar。
BFS 解析 POM 传递依赖。绕过死锁的 Gradle。
输出: deps_repo/ 下按 group/artifact/version 组织，classes 提取为 .jar。
"""
import os, sys, re, json, urllib.request, urllib.error, zipfile, io, hashlib, time
from xml.etree import ElementTree as ET

MAVEN = "https://maven.google.com"
NS = {"m": "http://maven.apache.org/POM/4.0.0"}
REPO = os.path.join(os.path.dirname(os.path.abspath(__file__)), "deps_repo")
os.makedirs(REPO, exist_ok=True)

# 依赖版本规则：Compose 1.7.x 系列对齐
ROOTS = [
    ("androidx.compose.ui", "ui", "1.7.3"),
    ("androidx.compose.ui", "ui-graphics", "1.7.3"),
    ("androidx.compose.ui", "ui-tooling-preview", "1.7.3"),
    ("androidx.compose.foundation", "foundation", "1.7.3"),
    ("androidx.compose.material3", "material3", "1.3.0"),
    ("androidx.compose.material", "material-icons-extended", "1.7.3"),
    ("androidx.compose.runtime", "runtime", "1.7.3"),
    ("androidx.activity", "activity-compose", "1.9.2"),
    ("androidx.core", "core-ktx", "1.13.1"),
]

# 已知传递依赖版本锁定（避免 BFS 拉到不一致版本）
VERSION_LOCK = {
    ("androidx.compose.runtime", "runtime"): "1.7.3",
    ("androidx.compose.runtime", "runtime-saveable"): "1.7.3",
    ("androidx.compose.runtime", "runtime-android"): "1.7.3",
    ("androidx.compose.ui", "ui"): "1.7.3",
    ("androidx.compose.ui", "ui-graphics"): "1.7.3",
    ("androidx.compose.ui", "ui-geometry"): "1.7.3",
    ("androidx.compose.ui", "ui-text"): "1.7.3",
    ("androidx.compose.ui", "ui-unit"): "1.7.3",
    ("androidx.compose.ui", "ui-android"): "1.7.3",
    ("androidx.compose.ui", "ui-graphics-android"): "1.7.3",
    ("androidx.compose.ui", "ui-tooling-preview-android"): "1.7.3",
    ("androidx.compose.foundation", "foundation"): "1.7.3",
    ("androidx.compose.foundation", "foundation-layout"): "1.7.3",
    ("androidx.compose.foundation", "foundation-android"): "1.7.3",
    ("androidx.compose.animation", "animation"): "1.7.3",
    ("androidx.compose.animation", "animation-core"): "1.7.3",
    ("androidx.compose.animation", "animation-android"): "1.7.3",
    ("androidx.compose.material3", "material3"): "1.3.0",
    ("androidx.compose.material3", "material3-android"): "1.3.0",
    ("androidx.compose.material", "material-icons-extended"): "1.7.3",
    ("androidx.compose.material", "material-icons-core"): "1.7.3",
    ("androidx.activity", "activity"): "1.9.2",
    ("androidx.activity", "activity-compose"): "1.9.2",
    ("androidx.activity", "activity-ktx"): "1.9.2",
    ("androidx.core", "core"): "1.13.1",
    ("androidx.core", "core-ktx"): "1.13.1",
    ("androidx.lifecycle", "lifecycle-runtime"): "2.8.4",
    ("androidx.lifecycle", "lifecycle-runtime-ktx"): "2.8.4",
    ("androidx.lifecycle", "lifecycle-viewmodel"): "2.8.4",
    ("androidx.lifecycle", "lifecycle-viewmodel-compose"): "2.8.4",
    ("androidx.lifecycle", "lifecycle-common"): "2.8.4",
    ("androidx.lifecycle", "lifecycle-runtime-android"): "2.8.4",
    ("androidx.lifecycle", "lifecycle-viewmodel-android"): "2.8.4",
    ("androidx.lifecycle", "lifecycle-common-java8"): "2.8.4",
    ("androidx.savedstate", "savedstate"): "1.2.1",
    ("androidx.profileinstaller", "profileinstaller"): "1.3.1",
    ("androidx.collection", "collection"): "1.4.0",
    ("androidx.startup", "startup-runtime"): "1.1.1",
    ("androidx.tracing", "tracing"): "1.1.0",
    ("androidx.annotation", "annotation"): "1.7.0",
    ("androidx.annotation", "annotation-experimental"): "1.3.1",
    ("org.jetbrains.kotlinx", "kotlinx-coroutines-android"): "1.7.3",
    ("org.jetbrains.kotlinx", "kotlinx-coroutines-core"): "1.7.3",
    ("org.jetbrains.kotlinx", "kotlinx-coroutines-bom"): "1.7.3",
    ("org.jetbrains.kotlin", "kotlin-stdlib"): "1.9.24",
    ("org.jetbrains.kotlin", "kotlin-stdlib-jdk8"): "1.9.24",
    ("org.jetbrains.kotlin", "kotlin-stdlib-jdk7"): "1.9.24",
    ("org.jetbrains.kotlin", "kotlin-stdlib-common"): "1.9.24",
}

visited = set()
downloaded = []
failed = []

def group_path(g):
    return g.replace(".", "/")

def fetch(url, binary=True):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                data = r.read()
                return data if binary else data.decode("utf-8", "replace")
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
            if attempt == 2:
                raise
            time.sleep(2)
        except Exception as e:
            if attempt == 2:
                raise
            time.sleep(2)

def parse_pom_deps(xml_text):
    """返回 [(group, artifact, version, scope)] 只取 compile/runtime"""
    deps = []
    try:
        root = ET.fromstring(xml_text)
    except Exception:
        return deps
    # 处理 <parent> 版本继承（简化：忽略）
    for d in root.findall(".//m:dependency", NS):
        g = d.findtext("m:groupId", "", NS).strip()
        a = d.findtext("m:artifactId", "", NS).strip()
        v = d.findtext("m:version", "", NS).strip()
        scope = (d.findtext("m:scope", "compile", NS) or "compile").strip()
        optional = d.findtext("m:optional", "false", NS).strip()
        if optional == "true":
            continue
        if scope in ("test", "provided", "system"):
            continue
        deps.append((g, a, v, scope))
    return deps

def resolve_version(g, a, v):
    """版本变量解析 + lock 覆盖"""
    if not v or v.startswith("$"):
        v = VERSION_LOCK.get((g, a), v)
    # lock 强制对齐
    if (g, a) in VERSION_LOCK:
        v = VERSION_LOCK[(g, a)]
    return v

def download_artifact(g, a, v):
    key = (g, a, v)
    if key in visited:
        return
    visited.add(key)
    v = resolve_version(g, a, v)
    if not v or v.startswith("$"):
        failed.append(f"{g}:{a}:?? (unresolved version)")
        return
    gp = group_path(g)
    # 优先 .aar（Android 库），回退 .jar
    base = f"{MAVEN}/{gp}/{a}/{v}/{a}-{v}"
    aar_url = base + ".aar"
    jar_url = base + ".jar"
    pom_url = base + ".pom"
    # 下载 POM 解析传递依赖
    pom_text = fetch(pom_url, binary=False)
    transitive = []
    if pom_text:
        transitive = parse_pom_deps(pom_text)
    # 下载产物
    data = fetch(aar_url)
    ext = ".aar"
    if data is None:
        data = fetch(jar_url)
        ext = ".jar"
    if data is None:
        failed.append(f"{g}:{a}:{v} (no aar/jar)")
        # 仍继续解析传递依赖
    else:
        out_dir = os.path.join(REPO, g.replace(".", "_"), a, v)
        os.makedirs(out_dir, exist_ok=True)
        raw_path = os.path.join(out_dir, a + ext)
        with open(raw_path, "wb") as f:
            f.write(data)
        # 从 aar 提取 classes.jar
        classes_jar = None
        if ext == ".aar":
            try:
                zf = zipfile.ZipFile(io.BytesIO(data))
                if "classes.jar" in zf.namelist():
                    classes_jar = zf.read("classes.jar")
                    with open(os.path.join(out_dir, "classes.jar"), "wb") as f:
                        f.write(classes_jar)
                # 提取 res（material3 等有资源）
                res_names = [n for n in zf.namelist() if n.startswith("res/")]
                if res_names:
                    zf.extractall(out_dir, [n for n in zf.namelist() if n.startswith("res/") or n in ("AndroidManifest.xml",)])
            except Exception as e:
                failed.append(f"{g}:{a}:{v} (extract err: {e})")
        downloaded.append(f"{g}:{a}:{v} ({ext}, {len(data)} bytes)")
    # BFS 传递依赖
    for (tg, ta, tv, _) in transitive:
        if (tg, ta) in VERSION_LOCK or (tg.startswith("androidx") or tg.startswith("org.jetbrains")):
            download_artifact(tg, ta, tv)

def main():
    print(f"[compose-deps] repo={REPO}")
    for (g, a, v) in ROOTS:
        download_artifact(g, a, v)
    print(f"\n=== DOWNLOADED ({len(downloaded)}) ===")
    for d in downloaded:
        print("  " + d)
    if failed:
        print(f"\n=== FAILED ({len(failed)}) ===")
        for f in failed:
            print("  " + f)
    # 写 classpath 清单
    classes_jars = []
    for root, dirs, files in os.walk(REPO):
        for fn in files:
            if fn == "classes.jar" or (fn.endswith(".jar") and fn != "classes.jar" and "classes" not in fn):
                p = os.path.join(root, fn)
                classes_jars.append(p)
    with open(os.path.join(REPO, "classpath.txt"), "w") as f:
        f.write(";".join(classes_jars))
    print(f"\n[classpath] {len(classes_jars)} jars -> deps_repo/classpath.txt")

if __name__ == "__main__":
    main()
