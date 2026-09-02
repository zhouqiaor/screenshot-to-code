import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

ApplicationWindow {
    visible: true
    width: 400
    height: 500
    title: "Settings"

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 16

        Label {
            text: "Settings"
            font.pixelSize: 24
            font.bold: true
            Layout.bottomMargin: 16
        }

        RowLayout {
            Layout.fillWidth: true

            Label {
                text: "Dark Mode"
                Layout.fillWidth: true
            }

            Switch {
                id: darkModeSwitch
            }
        }

        RowLayout {
            Layout.fillWidth: true

            Label {
                text: "Language"
                Layout.fillWidth: true
            }

            ComboBox {
                model: ["English", "Chinese", "Japanese"]
            }
        }

        Button {
            text: "Save"
            Layout.fillWidth: true
            Layout.topMargin: 16
            onClicked: {
                console.log("Settings saved")
            }
        }
    }
}
