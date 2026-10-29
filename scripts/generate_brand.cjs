#!/usr/bin/env node
// Development-only renderer. The installed runtime has no Node dependency.
const fs = require('node:fs/promises');
const path = require('node:path');
const { chromium } = require('playwright');
const root = path.resolve(__dirname, '..');
(async () => {
  const executablePath = process.env.PLOVI_CHROMIUM || undefined;
  const browser = await chromium.launch({ headless: true, ...(executablePath ? {executablePath} : {}) });
  try {
    const font = await fs.readFile(path.join(root, 'design/fonts/Geist-Variable.woff2'));
    const mono = await fs.readFile(path.join(root, 'design/fonts/GeistMono-Variable.woff2'));
    for (const [name, width, height] of [['og', 1200, 630], ['apple-touch-icon', 180, 180]]) {
      const page = await browser.newPage({ viewport: {width, height}, deviceScaleFactor: 1 });
      await page.route('**/*', route => route.abort());
      const svg = await fs.readFile(path.join(root, 'docs/assets/brand', name + '.svg'), 'utf8');
      await page.setContent(`<style>@font-face{font-family:Geist;src:url(data:font/woff2;base64,${font.toString('base64')});font-weight:100 900}@font-face{font-family:'Geist Mono';src:url(data:font/woff2;base64,${mono.toString('base64')});font-weight:100 900}html,body{margin:0;width:100%;height:100%}svg{width:100%;height:100%;display:block}</style>${svg}`);
      await page.evaluate(() => document.fonts.ready);
      await page.screenshot({path:path.join(root, 'docs/assets/brand',name+'.png'), omitBackground:true});
      await page.close();
      console.log(`Rendered ${name}.png (${width}×${height}).`);
    }
  } finally { await browser.close(); }
})().catch(error => { console.error(error.message); process.exitCode = 1; });
