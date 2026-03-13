import { chromium } from 'playwright';

const browser = await chromium.launch();
const page = await browser.newPage();

const logs = [];
page.on('console', msg => logs.push(`[${msg.type()}] ${msg.text()}`));

await page.goto('http://localhost:3002');
await page.waitForTimeout(6000);

console.log('=== Console logs ===');
logs.forEach(l => console.log(l));

await page.screenshot({ path: 'D:/ai/Sierac-tm/3d/screenshot4.png' });
console.log('Screenshot saved.');
await browser.close();
