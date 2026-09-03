#!/usr/bin/env python3
"""只重跑依赖 dex（deps_repo 全部 jar + kotlin-stdlib + coroutines core/android）。
用于修 NoClassDefFoundError: kotlin/jvm/internal/Intrinsics —— 之前 d8 输入漏了 stdlib。
跑完接 repack_multidex.py 即可，无需重编 Kotlin。"""
import os, sys, subprocess, importlib.util

ROOT = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("bca", os.path.join(ROOT, "build_compose_apk.py"))
bca = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bca)

dep_jars = bca.collect_dep_jars()
extra_jars = bca.collect_extra_jars()
print("[deps] %d compose jars + %d extra" % (len(dep_jars), len(extra_jars)))
for p in extra_jars:
    print("   extra: %s" % os.path.basename(p))

deps_dex_dir = os.path.join(bca.OUT, "deps_dex")
if os.path.exists(deps_dex_dir):
    bca.force_rmtree(deps_dex_dir)
os.makedirs(deps_dex_dir, exist_ok=True)

cmd = [bca.D8, "--release", "--output", deps_dex_dir, "--min-api", "24"] + dep_jars + extra_jars
print("\n>>> d8 deps dex (%d jars)" % (len(dep_jars) + len(extra_jars)))
p = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
if p.stdout.strip():
    print(p.stdout.strip()[:3000])
if p.returncode != 0:
    print("[FAIL] rc=%d" % p.returncode)
    print((p.stderr or "").strip()[:5000])
    sys.exit(1)
if p.stderr.strip():
    print("[stderr] " + p.stderr.strip()[:1500])
print("[OK] d8 deps dex")
for fn in sorted(os.listdir(deps_dex_dir)):
    print("   %-16s %12d bytes" % (fn, os.path.getsize(os.path.join(deps_dex_dir, fn))))
