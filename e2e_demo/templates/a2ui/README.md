# A2UI 可渲染骨架

## 快速使用

### 方式一：内嵌 JSONL
1. 将 LLM 生成的 A2UI JSONL 内容粘贴到 `a2ui_runner.html` 的 `// {{A2UI_CONTENT}}` 位置
2. 用浏览器打开 `a2ui_runner.html`

### 方式二：外部文件加载
```bash
# 用 Edge 打开，加载外部 JSONL 文件
msedge --headless=new --screenshot=output.png "file:///path/to/a2ui_runner.html?file=generated.jsonl"
```

### 方式三：脚本调用
```python
# 在 quick_verify.py 中已集成
from e2e_deep_verify import a2ui_to_html
html_content = a2ui_to_html("generated.jsonl")
# 生成自包含 HTML，可直接用 Edge 截图
```

## A2UI JSONL 协议

每行一个 JSON 对象，字段：
- `id`: 节点唯一标识
- `type`: 节点类型（column/row/container/card/text/button/input/image/list/divider）
- `parent`: 父节点 id（root 的 parent 为 null）
- `props`: CSS 样式和属性键值对

## 环境要求

- 任意现代浏览器（Chrome/Edge/Firefox）
- 无需编译器
- Edge headless 可用于 CI 截图

## 文件结构

```
a2ui/
├── template.jsonl       # 根节点模板（最小骨架）
├── a2ui_runner.html     # 独立渲染器（含 JSONL 解析 + 树构建 + DOM 渲染）
└── README.md
```
