// Fulfil every resource from disk while the browser is offline, even at first launch.
const { chromium } = require(process.env.PPL_PLAYWRIGHT_PATH || 'playwright');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const root = path.resolve(__dirname, 'ios/BundledWeb');
const mime = { '.html':'text/html', '.js':'text/javascript', '.css':'text/css', '.wasm':'application/wasm', '.json':'application/json' };

(async () => {
 const browser = await chromium.launch({headless:true,...(process.env.PPL_CHROME ? {executablePath:process.env.PPL_CHROME}: {})});
 try {
  const context = await browser.newContext({viewport:{width:320,height:568},offline:true});
  const external = [], errors=[];
  await context.route('**/*', async route => {
   const url=new URL(route.request().url());
   if(url.host!=='offline.ppl.test') {external.push(url.href);await route.abort();return;}
   const file=path.resolve(root,'.'+(url.pathname==='/'?'/index.html':decodeURIComponent(url.pathname)));
   if(!file.startsWith(root+path.sep)||!fs.existsSync(file)) {await route.fulfill({status:404,body:'Missing bundled resource'});return;}
   await route.fulfill({status:200,body:fs.readFileSync(file),contentType:mime[path.extname(file)]||'application/octet-stream'});
  });
  const page=await context.newPage();
  page.on('pageerror',error=>{errors.push(error.message);console.error('PAGE:',error.message);});
  page.on('console',msg=>{if(msg.type()==='error')console.error('CONSOLE:',msg.text());});
  await page.goto('https://offline.ppl.test/',{waitUntil:'domcontentloaded'});
  await page.waitForFunction(()=>document.documentElement.dataset.offlineReady||document.documentElement.dataset.offlineError,{},{timeout:120000});
  assert.equal(await page.evaluate(()=>document.documentElement.dataset.offlineError),undefined);
  await page.evaluate(()=>window.pplOfflineReady);
  const cases=JSON.parse(fs.readFileSync(path.resolve(__dirname,'ios/build/parity-cases.json'),'utf8'));
  for(const sample of cases) {
   const actual=await page.evaluate(async sample=>{
    const options={method:sample.method};
    if(sample.method==='POST') {
     if(sample.json){options.body=JSON.stringify(sample.body);options.headers={'Content-Type':'application/json'};}
     else {options.body=new FormData();Object.entries(sample.body).forEach(([k,v])=>options.body.set(k,v));}
    }
    const response=await fetch(sample.path,options);return{status:response.status,body:await response.json()};
   },sample);
   // Floating point NumPy/Python output must match the website, allowing tiny libm differences.
   function compare(a,b,label) {
    if(typeof a==='number'&&typeof b==='number')assert.ok(Math.abs(a-b)<=1e-8*Math.max(1,Math.abs(b)),label);
    else if(a&&b&&typeof a==='object'&&typeof b==='object') {assert.deepEqual(Object.keys(a).sort(),Object.keys(b).sort(),label);for(const key of Object.keys(b))compare(a[key],b[key],label+'.'+key);}
    else assert.equal(a,b,label);
   }
   compare(actual,sample.expected,sample.name);
  }
  for(const phase of ['takeoff','landing','cruise','climb','weight-balance']){
   await page.locator(`[data-tab="${phase}"]`).click();
   await page.locator(`#${phase} form`).evaluate(form=>form.requestSubmit());
   await page.locator(`#${phase} .metric`).first().waitFor();
   assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=document.documentElement.clientWidth+1),phase);
  }
  await page.evaluate(()=>window.pplPlatform.download('offline backup','test.json','application/json'));
  await page.locator('[data-tab="aircraft"]').click();
  await page.locator('#aircraft-editor [name="name"]').fill('Offline persistence check');
  await page.locator('#aircraft-editor').evaluate(form=>form.requestSubmit());
  await page.waitForFunction(()=>JSON.parse(localStorage.getItem('pplAircraftProfilesV1')).profiles.some(p=>p.name==='Offline persistence check'));
  // Save and reload uses the same origin; no server/database is involved.
  const before=await page.evaluate(()=>localStorage.getItem('pplAircraftProfilesV1'));
  await page.reload({waitUntil:'domcontentloaded'});
  await page.waitForFunction(()=>document.documentElement.dataset.offlineReady,{},{timeout:120000});
  assert.equal(await page.evaluate(()=>localStorage.getItem('pplAircraftProfilesV1')),before);
  await page.locator('[data-tab="takeoff"]').click();
  await page.locator('#takeoff form').evaluate(form=>form.requestSubmit());
  await page.locator('#takeoff .metric').first().waitFor();
  await page.evaluate(()=>scrollTo(0,0));
  await page.screenshot({path:path.resolve(__dirname,'ios/build/offline-320.png')});
  assert.deepEqual(external,[]);assert.deepEqual(errors,[]);
  console.log(`PASS: offline first launch and reload, ${cases.length} website parity cases, 5 calculator UIs, persisted profiles; zero external requests.`);
 } finally {await browser.close();}
})().catch(error=>{console.error(error);process.exitCode=1;});
