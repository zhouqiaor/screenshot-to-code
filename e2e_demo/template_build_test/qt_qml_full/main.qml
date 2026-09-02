import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import QtQuick.Controls.Material 2.15

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

    RowLayout {
        anchors.fill: parent
        spacing: 0

        // Sidebar
        Rectangle {
            Layout.preferredWidth: 240
            Layout.fillHeight: true
            color: "#ffffff"

            ColumnLayout {
                anchors.fill: parent
                anchors.margins: 16
                spacing: 8

                Text {
                    text: "Settings"
                    font.pixelSize: 24
                    font.bold: true
                    color: "#212121"
                    Layout.bottomMargin: 16
                }

                TextField {
                    placeholderText: "Search settings"
                    Layout.fillWidth: true
                    Material.accent: "#1677ff"
                    Layout.bottomMargin: 16
                }

                Repeater {
                    model: [
                        { name: "Enterprise Service", active: false },
                        { name: "Sound & Display", active: true },
                        { name: "Camera", active: false },
                        { name: "Wallpaper", active: false, status: "Set" },
                        { name: "Wi-Fi", active: false, status: "Connected" },
                        { name: "Smart Features", active: false },
                        { name: "Advanced", active: false }
                    ]
                    delegate: Rectangle {
                        Layout.fillWidth: true
                        height: 48
                        color: modelData.active ? "#E6F0FF" : "transparent"
                        radius: 4

                        RowLayout {
                            anchors.fill: parent
                            anchors.leftMargin: 12
                            anchors.rightMargin: 12

                            Text {
                                text: modelData.name
                                color: modelData.active ? "#1677ff" : "#212121"
                                font.bold: modelData.active
                                font.pixelSize: 16
                                Layout.fillWidth: true
                            }

                            Text {
                                text: modelData.status || ""
                                color: "#999999"
                                font.pixelSize: 12
                                visible: modelData.status !== undefined
                            }
                        }
                    }
                }
            }
        }

        // Main content area
        ScrollView {
            Layout.fillWidth: true
            Layout.fillHeight: true
            Layout.leftMargin: 16

            ColumnLayout {
                width: parent.width
                spacing: 20

                Text {
                    text: "Sound & Display"
                    font.pixelSize: 28
                    font.bold: true
                    color: "#212121"
                }

                // Sound settings card
                Rectangle {
                    Layout.fillWidth: true
                    Layout.preferredHeight: soundColumn.implicitHeight + 32
                    color: "#ffffff"
                    radius: 8

                    ColumnLayout {
                        id: soundColumn
                        anchors.fill: parent
                        anchors.margins: 16
                        spacing: 8

                        // Speaker switch
                        RowLayout {
                            Layout.fillWidth: true
                            Text {
                                text: "Speaker"
                                color: "#212121"
                                font.pixelSize: 16
                                Layout.fillWidth: true
                            }
                            Switch {
                                checked: true
                                Material.accent: "#1677ff"
                            }
                        }

                        // Volume slider
                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 12
                            Text {
                                text: "\uD83D\uDD08"
                                font.pixelSize: 20
                            }
                            Slider {
                                Layout.fillWidth: true
                                value: 0.7
                                Material.accent: "#1677ff"
                            }
                        }

                        // Notification volume slider
                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 12
                            Text {
                                text: "\uD83D\uDD14"
                                font.pixelSize: 20
                            }
                            Slider {
                                Layout.fillWidth: true
                                value: 0.5
                                Material.accent: "#1677ff"
                            }
                        }

                        // Key press sound switch
                        RowLayout {
                            Layout.fillWidth: true
                            Text {
                                text: "Key press sound"
                                color: "#212121"
                                font.pixelSize: 16
                                Layout.fillWidth: true
                            }
                            Switch {
                                checked: true
                                Material.accent: "#1677ff"
                            }
                        }

                        // Microphone switch
                        RowLayout {
                            Layout.fillWidth: true
                            Text {
                                text: "Microphone"
                                color: "#212121"
                                font.pixelSize: 16
                                Layout.fillWidth: true
                            }
                            Switch {
                                checked: false
                                Material.accent: "#1677ff"
                            }
                        }
                    }
                }

                // Brightness settings card
                Rectangle {
                    Layout.fillWidth: true
                    Layout.preferredHeight: brightnessRow.implicitHeight + 32
                    color: "#ffffff"
                    radius: 8

                    RowLayout {
                        id: brightnessRow
                        anchors.fill: parent
                        anchors.margins: 16
                        spacing: 12

                        Text {
                            text: "\u2600\uFE0F"
                            font.pixelSize: 20
                        }

                        Slider {
                            Layout.fillWidth: true
                            value: 0.8
                            Material.accent: "#1677ff"
                        }
                    }
                }
            }
        }
    }
}
