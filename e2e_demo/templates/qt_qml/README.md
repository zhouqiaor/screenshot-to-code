# Qt QML 可运行骨架

## 快速使用

### 方式一：qmlscene 交互预览（无需编译）
```bash
./run_qmlscene.sh
```

### 方式二：qmlscene headless 截图
```bash
./run_qmlscene.sh --headless screenshot.png
```

### 方式三：CMake 编译为可执行文件
```bash
mkdir build && cd build
cmake .. -DCMAKE_PREFIX_PATH="/path/to/qt/lib/cmake"
cmake --build .
./E2ESettings
```

## 使用 LLM 生成的 QML

1. 将 LLM 生成的 `.qml` 内容粘贴到 `main.qml` 的 `// {{QML_CONTENT}}` 位置
2. 确保保留 `ApplicationWindow` 根元素
3. 运行上述任一方式

## 环境要求

- Qt 5.15+ 或 Qt 6.x（含 Quick / Controls / Layouts / Material 模块）
- qmlscene（交互预览）或 qmlscenegrabber（headless 截图）
- CMake 3.16+（仅编译模式）

## 无 Qt 时降级

当环境中无 Qt 时，可使用近似 HTML 渲染策略：
- `backend/e2e_deep_verify.py` 中的 `qml_to_html()` 函数
- 将 QML 组件树解析为近似 HTML，用 Edge headless 截图
- 不是像素级精确，但能验证布局结构正确性

## 文件结构

```
qt_qml/
├── CMakeLists.txt       # CMake 构建配置
├── main.cpp             # C++ 入口（编译模式用）
├── main.qml             # QML 场景（含占位符）
├── run_qmlscene.sh      # 快速预览脚本
└── README.md
```
