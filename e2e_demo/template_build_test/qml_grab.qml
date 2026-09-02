import QtQuick 2.15
import QtQuick.Window 2.15

Window {
    id: root
    width: 900
    height: 600
    visible: true
    color: "#f5f5f5"

    // 加载目标 QML 内容
    Loader {
        id: loader
        anchors.fill: parent
        source: "llm_qt_qml.qml"
    }

    Timer {
        interval: 2000
        running: true
        repeat: false
        onTriggered: {
            // grabWindow 返回 QImage，save 到文件
            var img = root.grabWindow()
            img.save("C:/Code/screenshot-to-code/e2e_demo/template_build_test/qml_native_screenshot.png")
            console.log("Screenshot saved!")
            Qt.quit()
        }
    }

    Component.onCompleted: {
        console.log("Window ready, waiting 2s for render...")
    }
}
