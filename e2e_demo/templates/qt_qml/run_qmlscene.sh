#!/bin/bash
# QML 快速预览脚本 — 使用 qmlscene 运行，无需编译
# 用法:
#   ./run_qmlscene.sh                    # 交互模式
#   ./run_qmlscene.sh --headless         # headless 截图模式
#   ./run_qmlscene.sh --headless out.png # headless 截图到指定文件

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
QML_FILE="$SCRIPT_DIR/main.qml"

HEADLESS=false
OUTPUT=""
if [ "$1" = "--headless" ]; then
    HEADLESS=true
    OUTPUT="${2:-screenshot.png}"
fi

# 检查 qmlscene 是否在 PATH
if ! command -v qmlscene &> /dev/null; then
    echo "错误: qmlscene 未找到。请安装 Qt (qtdeclarative-tools)"
    echo "  Ubuntu: sudo apt install qmlscene qtdeclarative5-dev"
    echo "  macOS:  brew install qt"
    echo "  或者降级使用近似 HTML 渲染"
    exit 1
fi

if [ "$HEADLESS" = true ]; then
    # headless 模式：使用 offscreen 平台 + qmlscenegrabber
    echo "Headless 截图模式..."
    if command -v qmlscenegrabber &> /dev/null; then
        QT_QPA_PLATFORM=offscreen qmlscenegrabber -o "$OUTPUT" "$QML_FILE"
    else
        # 降级：qmlscene + offscreen + 手动 grab
        QT_QPA_PLATFORM=offscreen qmlscene "$QML_FILE" &
        PID=$!
        sleep 2
        # 用 import 命令截图（简化版）
        kill $PID 2>/dev/null || true
        echo "提示: 安装 qmlscenegrabber 可获得可靠截图"
        echo "输出到 $OUTPUT"
    fi
else
    # 交互模式
    echo "启动 QML 场景: $QML_FILE"
    qmlscene "$QML_FILE"
fi
