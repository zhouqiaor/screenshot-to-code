#!/usr/bin/env python3
"""扫描所有依赖 jar + 我们的 .class，解析 class 文件常量池里的类引用，
一次性算出「被引用但不存在」的类，避免装机后一个个撞 NoClassDefFoundError。

平台类（android.jar / java.* / javax.* / org.w3c / org.xml / dalvik 等）视为可用。
输出按 maven 坐标前缀聚合，方便一次把缺的依赖全抓下来。
"""
import os, sys, struct, zipfile, importlib.util
from collections import defaultdict

ROOT = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("bca", os.path.join(ROOT, "build_compose_apk.py"))
bca = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bca)


def parse_class_refs(data):
    """从 class 文件字节解析出所有 CONSTANT_Class 指向的类型名。"""
    if len(data) < 10 or data[:4] != b"\xca\xfe\xba\xbe":
        return set()
    cp_count = struct.unpack_from(">H", data, 8)[0]
    pos = 10
    utf8 = {}
    class_idx = []
    i = 1
    while i < cp_count:
        tag = data[pos]
        pos += 1
        if tag == 1:                       # Utf8
            n = struct.unpack_from(">H", data, pos)[0]
            pos += 2
            utf8[i] = data[pos:pos + n].decode("utf-8", "replace")
            pos += n
        elif tag == 7:                     # Class
            class_idx.append(struct.unpack_from(">H", data, pos)[0])
            pos += 2
        elif tag in (8, 16, 19, 20):       # String / MethodType / Module / Package
            pos += 2
        elif tag in (15,):                 # MethodHandle
            pos += 3
        elif tag in (3, 4, 9, 10, 11, 12, 17, 18):
            pos += 4
        elif tag in (5, 6):                # Long / Double 占两个槽
            pos += 8
            i += 1
        else:
            raise ValueError("unknown cp tag %d" % tag)
        i += 1
    out = set()
    for ci in class_idx:
        name = utf8.get(ci)
        if not name:
            continue
        while name.startswith("["):        # 数组类型
            name = name[1:]
        if name.startswith("L") and name.endswith(";"):
            name = name[1:-1]
        if name and len(name) > 1:
            out.add(name)
    return out


PLATFORM_PREFIXES = (
    "java/", "javax/", "android/", "androidx/annotation/",  # androidx.annotation 在 deps 里也有
    "dalvik/", "org/w3c/", "org/xml/", "org/xmlpull/", "org/json/",
    "org/apache/http/", "junit/", "sun/", "jdk/", "com/sun/",
    "org/jetbrains/annotations/", "org/intellij/",
)


def jar_classes(path):
    out = {}
    try:
        z = zipfile.ZipFile(path)
    except Exception as e:
        print("  [WARN] 打不开 %s (%s)" % (path, e))
        return out
    for n in z.namelist():
        if n.endswith(".class") and not n.startswith("META-INF/"):
            out[n[:-6]] = (path, n)
    return out


def main():
    dep_jars = bca.collect_dep_jars()
    extra_jars = bca.collect_extra_jars()
    all_jars = dep_jars + extra_jars

    available = {}
    for j in all_jars:
        for k, v in jar_classes(j).items():
            available.setdefault(k, v)
    print("[available] 依赖 jar 提供 %d 个类（来自 %d 个 jar）" % (len(available), len(all_jars)))

    # android.jar 平台类
    platform = set(jar_classes(bca.ANDROID_JAR).keys())
    print("[platform ] android.jar 提供 %d 个类" % len(platform))

    # 我们自己的 class
    ours = {}
    for root, _, files in os.walk(bca.OUT_CLASSES):
        for fn in files:
            if fn.endswith(".class"):
                p = os.path.join(root, fn)
                rel = os.path.relpath(p, bca.OUT_CLASSES).replace(os.sep, "/")[:-6]
                ours[rel] = (p, rel)
    print("[ours     ] 本项目 %d 个类" % len(ours))

    have = set(available) | platform | set(ours)

    referenced = set()
    scanned = 0
    for j in all_jars:
        z = zipfile.ZipFile(j)
        for n in z.namelist():
            if not n.endswith(".class") or n.startswith("META-INF/"):
                continue
            try:
                referenced |= parse_class_refs(z.read(n))
            except Exception:
                pass
            scanned += 1
    for p, _ in ours.values():
        with open(p, "rb") as f:
            try:
                referenced |= parse_class_refs(f.read())
            except Exception:
                pass
        scanned += 1
    print("[scan     ] 解析 %d 个 class，收集 %d 个类型引用" % (scanned, len(referenced)))

    missing = set()
    for r in referenced:
        if r in have:
            continue
        if any(r.startswith(p) for p in PLATFORM_PREFIXES):
            continue
        if "/" not in r:      # 无包名的基本类型残留
            continue
        missing.add(r)

    print("\n=== 缺失类 %d 个，按包聚合 ===" % len(missing))
    groups = defaultdict(list)
    for m in missing:
        pkg = "/".join(m.split("/")[:4])
        groups[pkg].append(m)
    for pkg in sorted(groups, key=lambda k: -len(groups[k])):
        items = sorted(groups[pkg])
        print("\n%-50s %d 个" % (pkg, len(items)))
        for it in items[:8]:
            print("    %s" % it)
        if len(items) > 8:
            print("    ... 及其它 %d 个" % (len(items) - 8))


if __name__ == "__main__":
    main()
