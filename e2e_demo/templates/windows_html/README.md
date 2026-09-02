# Windows HTML 模板

## 快速使用

1. 将 LLM 生成的 HTML 组件粘贴到 `template.html` 的 `<!-- {{HTML_CONTENT}} -->` 位置
2. 如有自定义 CSS，粘贴到 `/* {{CSS_CONTENT}} */` 位置
3. 用浏览器直接打开，或用 Edge headless 截图：
   ```bash
   msedge --headless=new --disable-gpu --window-size=960,720 --screenshot=out.png "file:///path/to/template.html"
   ```

## 说明

Windows HTML 栈是唯一不需要编译器的栈：
- LLM 生成的 HTML 自包含（含内联 CSS/JS）
- 可直接在浏览器中打开
- Edge headless 可直接截图

此模板提供基础样式重置 + 常用工具类，减少 LLM 生成代码中的重复 CSS。

## 文件结构

```
windows_html/
├── template.html    # HTML5 模板（含基础 CSS + 占位符）
└── README.md
```
