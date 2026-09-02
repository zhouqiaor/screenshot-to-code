// 纯 Kotlin 测试文件（不依赖 Android/Compose）
// 用于验证 kotlinc 完整编译流程

class SettingsItem(val name: String, val enabled: Boolean)
class SettingsModel {
    var notifications: Boolean = true
    var darkTheme: Boolean = false
    var language: String = "English"
    val items = listOf(
        SettingsItem("Enable notifications", true),
        SettingsItem("Dark theme", false),
        SettingsItem("Language", true)
    )
    fun save(): String = "Settings saved: notif=$notifications, dark=$darkTheme, lang=$language"
}

fun main() {
    val model = SettingsModel()
    println("=== Settings Screen ===")
    model.items.forEach { item ->
        println("  ${item.name}: ${if (item.enabled) "ON" else "OFF"}")
    }
    println(model.save())
}
