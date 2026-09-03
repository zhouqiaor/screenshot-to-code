# A2UI 统一 Schema 规范（2026-09-02 落地）

> 背景：本 fork 的「A2UI」是**自定义方言**，非 Google 官方 A2UI 协议。此前仓库内
> 三处 schema 彼此不统一，且渲染器 `buildTree` 仅认 `parent`、生成侧却输出 `children`，
> 导致生成的 `llm_a2ui.jsonl` 渲染出**整屏空白**（已实证）。本次修复后统一为下方契约。

## 统一契约（canonical）

每个节点 = 一行 JSON 对象，字段如下：

| 字段 | 必填 | 类型 | 说明 |
|---|---|---|---|
| `id` | ✅ | string | 唯一标识，建议语义化（`root`/`header`/`save-btn`） |
| `type` | ✅ | string | 组件类型（见下） |
| `children` | ✅ | string[] | **主树链接**：子节点 id 数组。叶子写 `[]` |
| `parent` | ⬜ | string | **可选回退链接**：父节点 id（兼容旧格式） |
| `props` | ⬜ | object | 所有视觉/行为属性（见下） |
| `bind` | ⬜ | object | 数据绑定 `{source, path}`（渲染器暂未消费） |
| `onClick` | ⬜ | string | 事件处理器 id（渲染器暂未消费） |

**根节点**：`id == "root"` 且不被任何其他节点的 `children` 引用；`buildTree` 优先以
`root` 为唯一根，否则取「未被任何节点引用」的节点作根。

### `type` 合法值

`button` `card` `column` `container` `image` `input` `list` `row` `stack` `text`
（基础）+ 渲染器额外支持：`switch` `toggle` `slider` `range` `dropdown`
`divider` `separator` `text_secondary` `text_title`

### `props` 合法键

- 文本：`text` `label` `title`
- 图片：`src`
- 输入/开关/滑块：`value` `min` `max` `step` `checked` `options` `selectedIndex` `placeholder`
- 主题：`primaryColor` `className`
- CSS 类（camelCase，渲染器转 kebab）：`width` `height` `backgroundColor` `color`
  `fontSize` `fontWeight` `borderRadius` `padding` `margin` `flexDirection`
  `justifyContent` `alignItems` `gap` `flex` `display` `minHeight` `maxWidth` `overflow`

## 最小示例

```jsonl
{"id":"root","type":"column","children":["title","row1"],"props":{"gap":12}}
{"id":"title","type":"text","children":[],"props":{"text":"Settings","fontSize":20}}
{"id":"row1","type":"row","children":["t","sw"],"props":{"gap":8}}
{"id":"t","type":"text","children":[],"props":{"text":"Enable"}}
{"id":"sw","type":"switch","children":[],"props":{"checked":true}}
```

## 涉及文件与改动（2026-09-02）

| 文件 | 角色 | 改动 |
|---|---|---|
| `e2e_demo/templates/a2ui/a2ui_runner.html` | 渲染器 | **核心修复**：`buildTree` 改为优先 `children`、回退 `parent`；原实现覆盖 `children` 为 `[]` 且只认 `parent` → 白屏 |
| `backend/agent/tools/validate_code.py` | 校验器 | schema 增加 `props`/`parent`；`allowed_types` 扩展渲染器支持类型（消除 `switch`/`dropdown` 误告警）；新增**悬空引用告警**（兜底树断裂） |
| `backend/e2e/common.py` | 生产生成 prompt | A2UI `req` 补全统一 schema 说明，确保模型输出与渲染器一致 |
| `backend/prompts/a2ui_system.py` | 死代码（未接线） | 对齐到统一契约（`children`+`props`+`parent`），若将来接线即一致 |

## 校验

- `python _verify_a2ui_validator.py`（临时，已删）：A2UI 样本 0 error/0 warning；
  parent 写法 0 error/0 warning；悬空引用 1 warning。
- `node e2e_demo/_verify_a2ui.mjs`（临时，已删）：原始 `buildTree` 仅渲染 1 个空
  `root`；修复后渲染完整 Settings 树。

## 待办（非本次范围）

- 中期：对齐 Google 官方 A2UI 协议 v0.9.1，复用官方 Lit/Angular/Flutter/React 渲染器 + `a2ui-agent-sdk`。
- `a2ui_system.py` 仍为死代码（无 import），如需启用需接入 `generate_stacks` 路由。
- 渲染器未消费 `bind`/`onClick`，如需真正「Agent-Driven」交互需补事件/数据绑定层。
