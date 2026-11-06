'use strict';
const fs=require('fs'),path=require('path'),cp=require('child_process');
const {chromium}=require('playwright');
const qa='/tmp/flat-qa',base='http://127.0.0.1:8765/';
const plan=JSON.parse(fs.readFileSync(path.join(qa,'flat-topic-mapping.json'),'utf8'));
const rows=plan.topics;
fs.mkdirSync(path.join(qa,'screenshots'),{recursive:true});
const wait=ms=>new Promise(r=>setTimeout(r,ms));
(async()=>{
 const server=cp.spawn('python3',['-m','http.server','8765','--bind','127.0.0.1','--directory',process.cwd()],{stdio:'ignore'});
 let browser;
 const checks=[];
 try{
  for(let i=0;i<50;i++){try{const r=await fetch(base);if(r.ok)break;}catch(e){}await wait(100);}
  const chrome=cp.execFileSync('which',['google-chrome'],{encoding:'utf8'}).trim();
  browser=await chromium.launch({headless:true,executablePath:chrome});
  const context=await browser.newContext({viewport:{width:1280,height:900}});
  const home=await context.newPage();
  const errors=[];home.on('pageerror',e=>errors.push(e.message));
  await home.goto(base+'index.html',{waitUntil:'load'});
  await home.waitForSelector('#topics .card');
  const cards=await home.locator('#topics .card').evaluateAll(es=>es.map(e=>({href:e.getAttribute('href'),title:e.innerText})));
  for(const row of rows)if(!cards.some(x=>x.href===row.file))throw Error('Missing homepage card '+row.topic_id);
  if(!cards.some(x=>x.href==='examples/Topics/speculative-decoding-topic.html'))throw Error('Speculative card missing');
  if(!cards.some(x=>x.href==='examples/Topics/rsi-knowledge-system.html'))throw Error('RSI card missing');
  if(cards.some(x=>x.href.includes('knowledge-systems-22')))throw Error('Collection card remains');
  const expand=home.locator('#topics .expand-button');
  if(await expand.count()&&await expand.isVisible()&&(await expand.getAttribute('aria-expanded'))==='false')await expand.click();
  await home.locator('#topics').screenshot({path:path.join(qa,'screenshots/topics-siblings.png')});
  checks.push({page:'index.html',direct_flat_topics:rows.length,topic_cards:cards.length,page_errors:errors.slice()});
  if(errors.length)throw Error('Homepage JS '+errors.join(';'));
  await home.close();
  for(const row of rows){
   const page=await context.newPage();const errs=[];
   page.on('pageerror',e=>errs.push(e.message));
   const response=await page.goto(base+row.file,{waitUntil:'load'});
   if(!response.ok())throw Error('HTTP '+response.status()+' '+row.file);
   const desktop=await page.evaluate(()=>({title:document.title,h1:document.querySelector('h1')?.innerText,width:document.documentElement.clientWidth,scroll:document.documentElement.scrollWidth,broken:[...document.images].filter(x=>x.complete&&!x.naturalWidth).length}));
   if(!desktop.h1||desktop.broken||desktop.scroll>desktop.width+2)throw Error('Desktop layout '+row.topic_id+' '+JSON.stringify(desktop));
   await page.setViewportSize({width:390,height:844});
   const mobile=await page.evaluate(()=>({width:document.documentElement.clientWidth,scroll:document.documentElement.scrollWidth}));
   if(mobile.scroll>mobile.width+2)throw Error('Mobile overflow '+row.topic_id+' '+JSON.stringify(mobile));
   let appendix=null;
   const box=page.locator('#expanded-reading');
   if(await box.count()){
    await box.locator('summary').click();
    await page.locator('#expanded-reading iframe').waitFor();
    const frame=page.frames().find(f=>f.parentFrame()===page.mainFrame());
    if(!frame)throw Error('Missing frame '+row.topic_id);
    await frame.waitForLoadState('load');
    await page.waitForFunction(()=>{const f=document.querySelector('#expanded-reading iframe');return f&&parseInt(f.style.height)>1000;},{timeout:30000});
    appendix=await frame.evaluate(()=>({title:document.title,h1:document.querySelector('h1')?.innerText,articles:document.querySelectorAll('article[id]').length,images:document.images.length,broken:[...document.images].filter(x=>x.complete&&!x.naturalWidth).length,scroll:document.documentElement.scrollWidth,width:document.documentElement.clientWidth,links:[...document.querySelectorAll('a[href]')].map(a=>a.getAttribute('href')).filter(h=>h.startsWith('#')&&h.length>1&&document.getElementById(decodeURIComponent(h.slice(1))))}));
    if(!appendix.h1||appendix.broken||appendix.scroll>appendix.width+3)throw Error('Appendix load/layout '+row.topic_id+' '+JSON.stringify(appendix));
    if(appendix.links.length){
     const target=appendix.links.find(h=>h.startsWith('#paper-'))||appendix.links[0];
     await frame.locator('a[href='+JSON.stringify(target)+']').first().click({force:true});
     await page.waitForFunction(()=>location.hash.startsWith('#expanded-reading--'),{timeout:10000});
     const expected='#expanded-reading--'+encodeURIComponent(decodeURIComponent(target.slice(1)));
     if(new URL(page.url()).hash!==expected)throw Error('Aux hash not preserved '+row.topic_id+' '+new URL(page.url()).hash+' '+expected);
    }
    if(row.topic_id==='opd-main'||row.topic_id==='image-acceleration'){
     await page.locator('#expanded-reading').scrollIntoViewIfNeeded();
     await page.screenshot({path:path.join(qa,'screenshots',row.topic_id+'-expanded-mobile.png')});
    }
    delete appendix.links;
   }
   const ownLinks=await page.locator('a[href^="index.html#"]').count();
   if(ownLinks)throw Error('Old dynamic self URLs remain '+row.topic_id+' '+ownLinks);
   if(errs.length)throw Error('JS errors '+row.topic_id+' '+errs.join(';'));
   checks.push({topic_id:row.topic_id,desktop,mobile,appendix,page_errors:errs});
   await page.close();
  }
  fs.writeFileSync(path.join(qa,'browser-results.json'),JSON.stringify({ok:true,method:'Headless Chrome on isolated GitHub Actions runner; real page loads, mobile widths, iframe expansion and actual anchor clicks',checks},null,2)+'\n');
  console.log(JSON.stringify({ok:true,topics:rows.length,expanded:checks.filter(x=>x.appendix).length}));
 }catch(e){
  fs.writeFileSync(path.join(qa,'browser-failure.json'),JSON.stringify({ok:false,message:e.stack,checks},null,2)+'\n');
  console.error(e.stack);process.exitCode=1;
 }finally{if(browser)await browser.close();server.kill();}
})();