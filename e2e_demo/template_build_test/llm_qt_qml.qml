import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import QtQuick.Controls.Material 2.15

ApplicationWindow {
    id: window
    width: 900
    height: 600
    visible: true
    title: "设置 - 声音与显示"
    Material.theme: Material.Light
    Material.primary: "#1677ff"
    Material.accent: "#1677ff"
    background: Rectangle { color: "#f5f5f5" }

    // 窗口关闭按钮
    Button {
        text: "×"
        font.pixelSize: 24
        flat: true
        anchors.top: parent.top
        anchors.right: parent.right
        anchors.margins: 16
        onClicked: window.close()
    }

    // 主体水平布局
    RowLayout {
        anchors.fill: parent
        anchors.margins: 16
        anchors.topMargin: 64
        spacing: 16

        // 侧边栏
        Rectangle {
            Layout.preferredWidth: 240
            Layout.fillHeight: true
            color: "white"
            radius: 12

            ColumnLayout {
                anchors.fill: parent
                anchors.margins: 16
                spacing: 16

                // 侧边栏标题
                Text {
                    text: "设置"
                    font.pixelSize: 24
                    font.bold: true
                    color: "#212121"
                }

                // 搜索输入框
                TextField {
                    Layout.fillWidth: true
                    placeholderText: "搜索设置项"
                    leftPadding: 32
                    Text {
                        text: "\uD83D\uDD0D"
                        font.pixelSize: 14
                        color: "#666666"
                        anchors.left: parent.left
                        anchors.leftMargin: 8
                        anchors.verticalCenter: parent.verticalCenter
                    }
                }

                // 导航列表
                ListView {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    clip: true
                    model: ListModel {
                        ListElement { name: "企业服务配置"; status: ""; selected: false }
                        ListElement { name: "声音与显示"; status: ""; selected: true }
                        ListElement { name: "摄像机"; status: ""; selected: false }
                        ListElement { name: "壁纸"; status: "已设置"; selected: false }
                        ListElement { name: "Wi-Fi"; status: "已连接"; selected: false }
                        ListElement { name: "智慧功能"; status: ""; selected: false }
                        ListElement { name: "高级设置"; status: ""; selected: false }
                    }
                    delegate: Item {
                        width: parent.width
                        height: 44
                        Rectangle {
                            anchors.fill: parent
                            color: selected ? "#1677ff20" : "transparent"
                            radius: 8
                        }
                        Row {
                            anchors.fill: parent
                            anchors.leftMargin: 12
                            anchors.rightMargin: 12
                            Text {
                                text: name
                                color: selected ? "#1677ff" : "#212121"
                                font.weight: selected ? Font.Medium : Font.Normal
                                Layout.fillWidth: true
                            }
                            Text {
                                text: status
                                color: selected ? "#1677ff" : "#999999"
                                font.pixelSize: 12
                                visible: status !== ""
                            }
                        }
                        MouseArea {
                            anchors.fill: parent
                            onClicked: {
                                for (let i = 0; i < model.count; i++) {
                                    model.setProperty(i, "selected", false)
                                }
                                model.setProperty(index, "selected", true)
                            }
                        }
                    }
                }
            }
        }

        // 主内容区
        ScrollView {
            Layout.fillWidth: true
            Layout.fillHeight: true
            clip: true

            ColumnLayout {
                anchors.fill: parent
                anchors.margins: 8
                spacing: 20

                // 页面标题
                Text {
                    text: "声音与显示"
                    font.pixelSize: 28
                    font.bold: true
                    color: "#212121"
                    Layout.bottomMargin: 8
                }

                // 声音设置卡片
                Rectangle {
                    Layout.fillWidth: true
                    color: "white"
                    radius: 12

                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: 16
                        spacing: 16

                        // 扬声器开关
                        RowLayout {
                            Layout.fillWidth: true
                            Text {
                                text: "扬声器"
                                color: "#212121"
                                font.pixelSize: 16
                                Layout.fillWidth: true
                            }
                            Switch { checked: true }
                        }

                        // 音量滑块
                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 12
                            Text {
                                text: "\uD83D\uDD0A"
                                font.pixelSize: 18
                                color: "#212121"
                            }
                            Slider {
                                value: 0.7
                                Layout.fillWidth: true
                            }
                        }

                        // 提示音量滑块
                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 12
                            Text {
                                text: "\uD83D\uDD14"
                                font.pixelSize: 18
                                color: "#212121"
                            }
                            Slider {
                                value: 0.5
                                Layout.fillWidth: true
                            }
                        }

                        // 按键音开关
                        RowLayout {
                            Layout.fillWidth: true
                            Text {
                                text: "按键音"
                                color: "#212121"
                                font.pixelSize: 16
                                Layout.fillWidth: true
                            }
                            Switch { checked: true }
                        }

                        // 麦克风开关
                        RowLayout {
                            Layout.fillWidth: true
                            Text {
                                text: "麦克风"
                                color: "#212121"
                                font.pixelSize: 16
                                Layout.fillWidth: true
                            }
                            Switch { checked: false }
                        }
                    }
                }

                // 亮度设置卡片
                Rectangle {
                    Layout.fillWidth: true
                    color: "white"
                    radius: 12

                    RowLayout {
                        anchors.fill: parent
                        anchors.margins: 16
                        spacing: 12
                        Text {
                            text: "\u2600\uFE0F"
                            font.pixelSize: 18
                            color: "#212121"
                        }
                        Slider {
                            value: 0.8
                            Layout.fillWidth: true
                        }
                    }
                }
            }
        }
    }
}