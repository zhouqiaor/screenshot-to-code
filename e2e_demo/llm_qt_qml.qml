import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

ApplicationWindow {
    width: 480
    height: 600
    visible: true
    title: "Settings"
    color: "#f5f5f5"

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 24
        spacing: 16

        Label {
            text: "Settings"
            font.pixelSize: 24
            font.bold: true
            Layout.bottomMargin: 8
        }

        Switch {
            text: "Enable notifications"
            checked: true
            Layout.fillWidth: true
        }

        Switch {
            text: "Dark theme"
            checked: false
            Layout.fillWidth: true
        }

        Label {
            text: "Language"
            Layout.topMargin: 8
        }

        ComboBox {
            model: ["English", "简体中文"]
            currentIndex: 0
            Layout.fillWidth: true
        }

        Button {
            text: "Save"
            highlighted: true
            Layout.fillWidth: true
            Layout.topMargin: 16
            contentItem: Label {
                text: parent.text
                color: "white"
                horizontalAlignment: Text.AlignHCenter
            }
            background: Rectangle {
                color: parent.down ? "#0066cc" : "#007AFF"
                radius: 4
            }
        }
    }
}