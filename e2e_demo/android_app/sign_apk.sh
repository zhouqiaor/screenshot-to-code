#!/bin/bash
APKSIGNER="C:\Programs\Android\Sdk\build-tools\35.0.0\apksigner.bat"
ZIPALIGN="C:\Programs\Android\Sdk\build-tools\35.0.0\zipalign.exe"
KEYSTORE="C:/Code/s2c-work/e2e_demo/android_app/build/debug.keystore"
APK="C:/Code/s2c-work/e2e_demo/android_app/build/settings.apk"

echo "=== zipalign ==="
"$ZIPALIGN" -f -v 4 "$APK" "${APK}.aligned" 2>&1 | tail -3
cp "${APK}.aligned" "$APK"

echo "=== apksigner sign ==="
"$APKSIGNER" sign --ks "$KEYSTORE" --ks-pass pass:android --ks-key-alias androiddebugkey --key-pass pass:android "$APK" 2>&1

echo "=== verify ==="
"$APKSIGNER" verify --verbose "$APK" 2>&1 | head -5
