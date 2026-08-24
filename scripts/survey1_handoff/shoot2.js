const { chromium } = require('playwright-core');
const path = require('path');
const OUT = '/home/user/Unsafe-Commercial-Autonomy/survey1_figs';
const FIGS = [
  ['fig-c5-pair.html', 'fig-c5-pair.png', 1550],
  ['fig-a5-pair.html', 'fig-a5-pair.png', 1550],
  ['fig-b4-pair.html', 'fig-b4-pair.png', 1550],
  ['fig-camps.html', 'fig-camps.png', 1080],
  ['fig-unsafe.html', 'fig-unsafe-votes.png', 1080],
];
(async () => {
  const browser = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium_headless_shell-1194/chrome-linux/headless_shell' });
  for (const [html, png, w] of FIGS) {
    const p = await browser.newPage({ viewport: { width: w, height: 1200 }, deviceScaleFactor: 2 });
    await p.goto('file://' + path.join(__dirname, html));
    await p.locator('.shot').screenshot({ path: path.join(OUT, png) });
    console.log('saved', png);
    await p.close();
  }
  await browser.close();
})().catch((e) => { console.error(e); process.exit(1); });
