"""Build a signed APK for an Android XML (View) stack WITHOUT Gradle.

Why this exists
---------------
On this machine the Gradle/AAPT2 daemon pipeline deadlocks on Windows
(see the "zombie daemon holds merged_res_blame_folder" + MAX_PATH notes in
``design-docs/one-click-generation-pipeline.md``).  Building a **pure framework
widget** XML layout does not need Gradle at all: aapt2 + javac + d8 + zipalign +
apksigner is enough, and that pipeline runs in ~90 s.

Constraints (important)
-----------------------
* The generated layout must use **framework widgets only**
  (LinearLayout/TextView/ImageView/Switch/ScrollView/... ) with **no** ``app:``
  namespace, no Material/AppCompat/ConstraintLayout widgets.
* The theme must be a framework theme (e.g.
  ``@android:style/Theme.Material.Light.NoActionBar``) so no app resources are
  required.
* Every ``@drawable/...`` referenced by the layout must exist in the resources
  dir (use :mod:`e2e.gen_drawables`-style generation first).

Usage
-----
    python -m e2e.build_xml_apk <layout.xml> <res_drawable_dir> <out_dir>
        [--package com.e2e.xmlgen] [--label "E2E XML Generated"]
        [--sdk C:/Programs/Android/Sdk] [--build-tools 34.0.0] [--platform android-36]

Prints the path of the signed APK on success; exits non-zero on failure.

Compose stacks CANNOT use this path (the Compose compiler plugin requires
Gradle) — they still go through the Gradle host project.
"""
from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

MANIFEST_TMPL = """<?xml version="1.0" encoding="utf-8"?>
<manifest xmlns:android="http://schemas.android.com/apk/res/android"
    package="{package}">
    <uses-sdk android:minSdkVersion="24" android:targetSdkVersion="{target}" />
    <application
        android:label="{label}"
        android:theme="@android:style/Theme.Material.Light.NoActionBar">
        <activity
            android:name=".MainActivity"
            android:exported="true">
            <intent-filter>
                <action android:name="android.intent.action.MAIN" />
                <category android:name="android.intent.category.LAUNCHER" />
            </intent-filter>
        </activity>
    </application>
</manifest>
"""

MAIN_ACTIVITY_TMPL = """package {package};

import android.app.Activity;
import android.os.Bundle;

public class MainActivity extends Activity {{
    @Override
    protected void onCreate(Bundle savedInstanceState) {{
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_main);
    }}
}}
"""


def run(cmd: list[str], cwd: Path | None = None) -> None:
    """Run a command, echoing it, and raise on failure."""
    printable = " ".join(str(c) for c in cmd)
    print(f"\n$ {printable}")
    proc = subprocess.run(
        [str(c) for c in cmd],
        cwd=str(cwd) if cwd else None,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if proc.stdout:
        print(proc.stdout.strip())
    if proc.returncode != 0:
        sys.stderr.write(proc.stderr or "")
        print(f"\n[FAIL] exit={proc.returncode}: {printable}", file=sys.stderr)
        sys.exit(proc.returncode)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("layout", help="generated android_xml.xml")
    ap.add_argument("drawables", help="directory containing the generated res/drawable/*.xml")
    ap.add_argument("out", help="build output directory (created/cleaned)")
    ap.add_argument("--package", default="com.e2e.xmlgen")
    ap.add_argument("--label", default="E2E XML Generated")
    ap.add_argument("--sdk", default="C:/Programs/Android/Sdk")
    ap.add_argument("--build-tools", default="34.0.0")
    ap.add_argument("--platform", default="android-36")
    ap.add_argument("--keystore", default=None,
                    help="debug keystore; default <HOME>/.android/debug.keystore")
    args = ap.parse_args()

    sdk = Path(args.sdk)
    bt = sdk / "build-tools" / args.build_tools
    android_jar = sdk / "platforms" / args.platform / "android.jar"
    for tool in (bt / "aapt2.exe", bt / "d8.bat", bt / "apksigner.bat", bt / "zipalign.exe", android_jar):
        if not tool.exists():
            sys.exit(f"[FAIL] missing SDK component: {tool}")

    out = Path(args.out)
    if out.exists():
        shutil.rmtree(out)
    res = out / "res"
    (res / "layout").mkdir(parents=True)
    (res / "drawable").mkdir(parents=True)
    (out / "src").mkdir()
    (out / "obj").mkdir()
    (out / "dex_out").mkdir()
    (out / "gen").mkdir()

    # 1. resources
    shutil.copy(args.layout, res / "layout" / "activity_main.xml")
    drawables = sorted(Path(args.drawables).glob("*.xml"))
    for d in drawables:
        shutil.copy(d, res / "drawable" / d.name)
    print(f"[1/7] resources: 1 layout + {len(drawables)} drawables")

    pkg_path = args.package.replace(".", "/")
    (out / "AndroidManifest.xml").write_text(
        MANIFEST_TMPL.format(package=args.package, label=args.label, target=args.build_tools.split(".")[0]),
        encoding="utf-8",
    )
    (out / "src" / "MainActivity.java").write_text(
        MAIN_ACTIVITY_TMPL.format(package=args.package), encoding="utf-8"
    )

    # 2. aapt2 compile
    run([bt / "aapt2.exe", "compile", "--dir", "res", "-o", "compiled.zip"], cwd=out)
    print("[2/7] aapt2 compile OK")

    # 3. aapt2 link -> base.apk + R.java
    run([
        bt / "aapt2.exe", "link", "-o", "base.apk", "-I", android_jar,
        "--manifest", "AndroidManifest.xml", "--java", "gen",
        "--auto-add-overlay", "compiled.zip",
    ], cwd=out)
    print("[3/7] aapt2 link OK (base.apk + R.java)")

    # 4. javac
    r_java = out / "gen" / pkg_path / "R.java"
    run([
        "javac", "--release", "11", "-classpath", android_jar, "-d", "obj",
        r_java, out / "src" / "MainActivity.java",
    ], cwd=out)
    print("[4/7] javac OK")

    # 5. d8
    classes = sorted((out / "obj" / pkg_path).glob("*.class"))
    run([bt / "d8.bat", "--lib", android_jar, "--release", "--output", "dex_out", *classes], cwd=out)
    print("[5/7] d8 OK -> classes.dex")

    # 6. pack dex + zipalign
    shutil.copy(out / "base.apk", out / "with_dex.apk")
    with zipfile.ZipFile(out / "with_dex.apk", "a", zipfile.ZIP_DEFLATED) as z:
        z.write(out / "dex_out" / "classes.dex", "classes.dex")
    run([bt / "zipalign.exe", "-f", "4", "with_dex.apk", "aligned.apk"], cwd=out)
    print("[6/7] zipalign OK")

    # 7. sign
    ks = Path(args.keystore) if args.keystore else Path.home() / ".android" / "debug.keystore"
    if not ks.exists():
        sys.exit(f"[FAIL] keystore not found: {ks}")
    signed = out / "app-debug.apk"
    run([
        bt / "apksigner.bat", "sign", "--ks", ks,
        "--ks-pass", "pass:android", "--key-pass", "pass:android",
        "--ks-key-alias", "androiddebugkey", "--out", signed.name, "aligned.apk",
    ], cwd=out)
    print(f"[7/7] signed OK -> {signed}")

    print(f"\n=== APK READY: {signed} ({signed.stat().st_size} bytes) ===")


if __name__ == "__main__":
    main()
