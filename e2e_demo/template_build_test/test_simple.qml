import QtQuick 2.15
import QtQuick.Window 2.15

Window {
    id: win
    width: 400
    height: 300
    visible: true
    color: "lightblue"

    Text {
        anchors.centerIn: parent
        text: "Hello Qt!"
        font.pixelSize: 30
    }

    Timer {
        interval: 1000; running: true; repeat: false
        onTriggered: {
            var img = win.grabWindow()
            img.save("C:/Code/screenshot-to-code/e2e_demo/template_build_test/qml_simple_screenshot.png")
            console.log("Saved!")
            Qt.quit()
        }
    }
}
