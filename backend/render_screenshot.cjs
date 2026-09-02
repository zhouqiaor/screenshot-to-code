// Render HTML screenshot using puppeteer-core + Edge
const path = require('path');
const puppeteer = require('C:/Code/screenshot-to-code/node_modules/puppeteer-core');

const HTML_PATH = 'C:/Code/screenshot-to-code/e2e_demo/run_20260901/llm_windows_html.html';
const PNG_PATH = 'C:/Code/screenshot-to-code/e2e_demo/run_20260901/render_html_screenshot.png';
const EDGE_PATH = 'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe';

(async () => {
  try {
    const browser = await puppeteer.launch({
      headless: 'new',
      executablePath: EDGE_PATH,
      args: ['--no-sandbox', '--disable-setuid-sandbox', '--disable-gpu']
    });
    const page = await browser.newPage();
    await page.setViewport({ width: 960, height: 720 });
    await page.goto('file:///' + HTML_PATH, { waitUntil: 'networkidle0', timeout: 30000 });
    await new Promise(r => setTimeout(r, 1000));
    await page.screenshot({ path: PNG_PATH, fullPage: false });
    await browser.close();
    console.log('Screenshot saved: ' + PNG_PATH);
    process.exit(0);
  } catch (e) {
    console.error('Error: ' + e.message);
    process.exit(1);
  }
})();
