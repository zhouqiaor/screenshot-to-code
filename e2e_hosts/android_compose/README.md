# Kotlin Compose 可编译骨架

## 快速使用

1. 复制此目录到工作区
2. 复制 `local.properties.template` 为 `local.properties`，修改 SDK 路径
3. 将 LLM 生成的 `.kt` 文件中的 `@Composable` 函数粘贴到 `MainActivity.kt` 的 `// {{COMPOSABLE_FUNCTION_CALL}}` 位置
4. 运行 `./gradlew assembleDebug`（或 Windows 上 `gradlew.bat assembleDebug`）
5. APK 输出：`app/build/outputs/apk/debug/app-debug.apk`

## 环境要求

- Android SDK 34（compileSdk）
- JDK 17
- Gradle 8.9（wrapper 已内置，无需全局安装）
- AGP 8.5.2 + Kotlin 1.9.24 + Compose 1.7.3

## 已验证

- 2026-09-01：Gradle assembleDebug 39s BUILD SUCCESSFUL，15MB APK
- 安装到 Android 设备 + screencap 截图成功

## 文件结构

```
kotlin_compose/
├── settings.gradle.kts          # 项目设置
├── build.gradle.kts             # 根构建文件
├── gradle.properties            # Gradle 配置
├── local.properties.template    # SDK 路径模板
├── gradlew / gradlew.bat        # Gradle Wrapper 脚本
├── gradle/wrapper/
│   ├── gradle-wrapper.jar       # Gradle Wrapper 二进制
│   └── gradle-wrapper.properties # Gradle 版本配置 (8.9)
└── app/
    ├── build.gradle.kts         # 模块构建文件
    └── src/main/
        ├── AndroidManifest.xml  # 清单文件
        ├── java/com/e2e/settings/
        │   └── MainActivity.kt  # 入口 Activity (含占位符)
        └── res/values/
            ├── strings.xml      # 字符串资源
            ├── themes.xml        # 主题
            └── colors.xml        # 颜色定义
```
