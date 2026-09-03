#!/bin/bash
# Android APK 手动编译脚本
set -e

APP_DIR="C:/Code/s2c-work/e2e_demo/android_app"
BUILD_DIR="$APP_DIR/build"

JBR="C:\Program Files\Android\Android Studio\jbr\bin\java.exe"
KOTLIN_JAR="C:\Program Files\Android\Android Studio\plugins\Kotlin\kotlinc\lib\kotlin-compiler.jar"
ANDROID_JAR="C:\Programs\Android\Sdk\platforms\android-33\android.jar"
AAPT2="C:\Programs\Android\Sdk\build-tools\35.0.0\aapt2.exe"
D8="C:\Programs\Android\Sdk\build-tools\35.0.0\d8.bat"
APKSIGNER="C:\Programs\Android\Sdk\build-tools\35.0.0\apksigner.bat"
KEYTOOL="C:\Program Files\Android\Android Studio\jbr\bin\keytool.exe"
JARSIGNER="C:\Program Files\Android\Android Studio\jbr\bin\jarsigner.exe"

# 路径检查
echo "=== Step 1: Check tools ==="
ls "$ANDROID_JAR" 2>/dev/null && echo "android.jar OK"
ls "$AAPT2" 2>/dev/null && echo "aapt2 OK"
ls "$D8" 2>/dev/null && echo "d8 OK"

# Step 2: Compile resources with aapt2
echo ""
echo "=== Step 2: Compile resources ==="
rm -rf "$BUILD_DIR" 2>/dev/null || true
mkdir -p "$BUILD_DIR/obj" "$BUILD_DIR/apk" "$BUILD_DIR/libs"
"$AAPT2" compile --dir "$APP_DIR/res" -o "$BUILD_DIR/resources.zip" 2>&1
echo "Resources compiled"

# Step 3: Link resources and manifest
echo ""
echo "=== Step 3: Link resources ==="
"$AAPT2" link \
    -I "$ANDROID_JAR" \
    --manifest "$APP_DIR/AndroidManifest.xml" \
    -o "$BUILD_DIR/base.apk" \
    "$BUILD_DIR/resources.zip" 2>&1
echo "Resources linked"

# Step 4: Generate R.java
echo ""
echo "=== Step 4: Generate R.java ==="
"$AAPT2" link \
    -I "$ANDROID_JAR" \
    --manifest "$APP_DIR/AndroidManifest.xml" \
    --java "$BUILD_DIR/obj" \
    -o "$BUILD_DIR/base2.apk" \
    "$BUILD_DIR/resources.zip" 2>&1 || echo "R.java generation may have warnings"
# Try aapt (legacy) for R.java
AAPT="C:\Programs\Android\Sdk\build-tools\35.0.0\aapt.exe"
"$AAPT" package -f -m \
    -J "$BUILD_DIR/obj" \
    -I "$ANDROID_JAR" \
    -M "$APP_DIR/AndroidManifest.xml" \
    -S "$APP_DIR/res" 2>&1
echo "R.java generated"

# Find R.java
RJAVA=$(find "$BUILD_DIR/obj" -name "R.java" | head -1)
echo "R.java: $RJAVA"

# Step 5: Compile Kotlin + R.java
echo ""
echo "=== Step 5: Compile Kotlin ==="
"$JBR" -jar "$KOTLIN_JAR" \
    -classpath "$ANDROID_JAR" \
    -d "$BUILD_DIR/classes" \
    "$APP_DIR/src/MainActivity.kt" "$RJAVA" 2>&1
echo "Kotlin compiled"

# Step 6: Convert to DEX
echo ""
echo "=== Step 6: Convert to DEX ==="
# Collect all class files
cd "$BUILD_DIR/classes"
find . -name "*.class" > "$BUILD_DIR/class_list.txt"
"$D8" --output "$BUILD_DIR" @$BUILD_DIR/class_list.txt 2>&1 || {
    # fallback: use d8 with all class files directly
    CLASSES=$(find "$BUILD_DIR/classes" -name "*.class" | tr '\n' ' ')
    "$D8" --output "$BUILD_DIR" $CLASSES 2>&1
}
echo "DEX generated"
ls -la "$BUILD_DIR/classes.dex" 2>&1

# Step 7: Package APK
echo ""
echo "=== Step 7: Package APK ==="
cd "$BUILD_DIR"
cp base.apk settings.apk
# Add classes.dex to APK
"C:\Program Files\Android\Android Studio\jbr\bin\jar.exe" uf settings.apk classes.dex 2>&1 || \
    zip -j settings.apk classes.dex 2>&1
echo "APK packaged"

# Step 8: Sign APK
echo ""
echo "=== Step 8: Sign APK ==="
KEYSTORE="$BUILD_DIR/debug.keystore"
if [ ! -f "$KEYSTORE" ]; then
    "$KEYTOOL" -genkey -v -keystore "$KEYSTORE" \
        -storepass android -alias androiddebugkey \
        -keypass android \
        -keyalg RSA -keysize 2048 -validity 10000 \
        -dname "CN=Android Debug, O=Android, C=US" 2>&1
fi
"$JARSIGNER" -keystore "$KEYSTORE" \
    -storepass android -keypass android \
    "$BUILD_DIR/settings.apk" androiddebugkey 2>&1
echo "APK signed"

echo ""
echo "=== Done ==="
ls -la "$BUILD_DIR/settings.apk"
