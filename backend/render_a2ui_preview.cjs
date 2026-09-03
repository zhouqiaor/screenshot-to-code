// Render A2UI JSONL to HTML, then screenshot
const fs = require('fs');
const path = require('path');

const JSONL_PATH = 'C:/Code/screenshot-to-code/e2e_demo/run_20260901/llm_a2ui.jsonl';
const HTML_PATH = 'C:/Code/screenshot-to-code/e2e_demo/run_20260901/a2ui_preview.html';
const PNG_PATH = 'C:/Code/screenshot-to-code/e2e_demo/run_20260901/render_a2ui_screenshot.png';
const EDGE_PATH = 'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe';

const VALID_TYPES = ['button', 'card', 'column', 'container', 'image', 'input', 'list', 'row', 'stack', 'text'];

// Parse JSONL
const lines = fs.readFileSync(JSONL_PATH, 'utf-8').trim().split('\n');
const nodes = [];
for (const line of lines) {
  try { nodes.push(JSON.parse(line.trim())); } catch(e) { console.error('Parse error:', e.message); }
}

// Build parent->children map
const childrenMap = {};
const root = nodes.find(n => !n.parent || n.parent === null);
for (const node of nodes) {
  const p = node.parent;
  if (p && p !== null) {
    if (!childrenMap[p]) childrenMap[p] = [];
    childrenMap[p].push(node);
  }
}

function renderNode(node) {
  const props = node.props || {};
  const styleStr = Object.entries(props)
    .filter(([k]) => !['items', 'selectedItem', 'itemStatuses', 'itemPadding', 'itemBorderRadius',
      'selectedBackgroundColor', 'selectedColor', 'gap', 'inputType', 'checked', 'activeColor',
      'src', 'alt', 'value', 'min', 'max', 'placeholder', 'prefixIcon', 'accentColor',
      'justifyContent', 'alignItems', 'flex', 'overflow', 'overflowY',
      'primaryColor', 'color'].includes(k))
    .map(([k, v]) => {
      const cssKey = k.replace(/([A-Z])/g, '-$1').toLowerCase();
      let cssVal = typeof v === 'number' ? (cssKey.includes('font-size') || cssKey.includes('width') || cssKey.includes('height') || cssKey.includes('padding') || cssKey.includes('gap') ? v + 'px' : v) : v;
      return `${cssKey}: ${cssVal}`;
    })
    .join('; ');
  const children = childrenMap[node.id] || [];

  if (node.type === 'text') {
    return `<div style="${styleStr}">${node.text || ''}</div>`;
  } else if (node.type === 'button') {
    return `<button style="${styleStr}; cursor: pointer;">${node.text || ''}</button>`;
  } else if (node.type === 'input') {
    if (props.inputType === 'switch') {
      const checked = props.checked ? 'checked' : '';
      return `<label style="display: inline-flex; align-items: center; cursor: pointer;"><input type="checkbox" ${checked} style="appearance: none; width: ${props.width || '44px'}; height: ${props.height || '22px'}; background: ${props.checked ? (props.activeColor || '#1677ff') : '#ccc'}; border-radius: ${props.borderRadius || '11px'}; position: relative; cursor: pointer; transition: background 0.2s;"/><span style="position: absolute; width: 18px; height: 18px; background: white; border-radius: 50%; margin-left: ${props.checked ? '22px' : '2px'}; transition: margin 0.2s; box-shadow: 0 1px 3px rgba(0,0,0,0.2);"></span></label>`;
    } else if (props.inputType === 'range') {
      return `<input type="range" min="${props.min || 0}" max="${props.max || 100}" value="${props.value || 50}" style="flex: ${props.flex || 1}; accent-color: ${props.accentColor || '#1677ff'};" />`;
    } else {
      return `<input type="text" placeholder="${props.placeholder || node.text || ''}" style="${styleStr}" />`;
    }
  } else if (node.type === 'image') {
    return `<div style="${styleStr}; display: inline-flex; align-items: center; justify-content: center; background: #e0e0e0; border-radius: 2px;">${props.alt || 'img'}</div>`;
  } else if (node.type === 'list') {
    const items = props.items || [];
    const statuses = props.itemStatuses || {};
    return `<div style="${styleStr}; display: flex; flex-direction: column;">${items.map(item => {
      const isSel = item === props.selectedItem;
      const status = statuses[item];
      return `<div style="padding: ${props.itemPadding || '8px 12px'}; border-radius: ${props.itemBorderRadius || '4px'}; ${isSel ? `background: ${props.selectedBackgroundColor || '#e6f4ff'}; color: ${props.selectedColor || '#1677ff'};` : ''} display: flex; justify-content: space-between; align-items: center;"><span>${item}</span>${status ? `<span style="font-size: 12px; color: #999;">${status}</span>` : ''}</div>`;
    }).join('')}</div>`;
  } else {
    // container/card/column/row/stack - render children
    return `<div style="${styleStr}; display: flex;">${children.map(renderNode).join('')}</div>`;
  }
}

const rootStyle = root?.props || {};
const html = `<!DOCTYPE html>
<html lang="zh-CN">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>A2UI Preview</title>
<style>
* { margin: 0; padding: 0; box-sizing: border-box; }
body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }
</style>
</head>
<body>
${root ? renderNode(root) : '<p>No root node</p>'}
</body>
</html>`;

fs.writeFileSync(HTML_PATH, html, 'utf-8');
console.log('A2UI HTML preview written: ' + HTML_PATH);
console.log('HTML size: ' + html.length + ' chars');
