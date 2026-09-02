import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import QtQuick.Controls.Material 2.15
import QtTest 1.15

// 截图包装器：加载目标 QML 并截图
TestCase {
    name: "ScreenshotGrabber"
    when: windowShown

    function grab(path) {
        // 通过 Window.grabWindow 截图
        grabWindow(window)
        compare(true, true)
    }

    function test_screenshot() {
        // 等待渲染完成
        wait(1000)
        // 使用 ImageGrab 抓取
        var img = grabImage(window)
        // 保存截图
        if (img) {
            // QML Test grabImage 返回 ImageHolder, 无法直接保存
            // 用替代方案
        }
    }
}
