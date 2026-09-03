import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import QtQuick.Controls.Material 2.15

// QML 骨架模板 — 替换 ApplicationWindow 内容为 LLM 生成的 QML
ApplicationWindow {
    id: window
    width: 900
    height: 600
    visible: true
    title: "Settings"
    Material.theme: Material.Light
    Material.primary: "#1677ff"
    Material.accent: "#1677ff"
    background: Rectangle { color: "#f5f5f5" }

    // {{QML_CONTENT}}
    // 替换为 LLM 生成的 QML 组件树
}
