(()=>{
 const theme=document.querySelector('#theme');
 let preference='system';try{preference=localStorage.getItem('iga-reader-theme')||'system'}catch{}
 if(!['system','light','dark'].includes(preference))preference='system';
 theme.value=preference;document.documentElement.dataset.theme=preference;
 theme.addEventListener('change',()=>{document.documentElement.dataset.theme=theme.value;try{localStorage.setItem('iga-reader-theme',theme.value)}catch{}});
 const search=document.querySelector('#paper-search'),links=[...document.querySelectorAll('.quick-index a')],status=document.querySelector('#search-status');
 search.addEventListener('input',()=>{const q=search.value.trim().toLocaleLowerCase();let count=0;links.forEach(a=>{const match=a.dataset.name.includes(q);a.hidden=!match;if(match)count++});status.textContent=count?`${count} 篇匹配论文`:'没有匹配论文，请试试英文简称或路线名称。'});
 const mapButton=document.querySelector('#map-toggle'),map=document.querySelector('#map-frame');
 mapButton.addEventListener('click',()=>{const expanded=map.classList.toggle('expanded');mapButton.setAttribute('aria-expanded',String(expanded));mapButton.textContent=expanded?'收起路线图':'展开路线图'});
 const dialog=document.querySelector('#figure-dialog'),art=document.querySelector('#dialog-art'),caption=document.querySelector('#dialog-caption');let trigger=null;
 document.querySelectorAll('.zoom').forEach(button=>button.addEventListener('click',()=>{trigger=button;const fig=button.closest('figure');art.replaceChildren(...[...fig.querySelectorAll('img')].map(im=>{const clone=im.cloneNode(true);clone.loading='eager';return clone}));caption.textContent=fig.querySelector('figcaption').textContent;dialog.showModal();document.querySelector('#close-dialog').focus()}));
 document.querySelector('#close-dialog').addEventListener('click',()=>dialog.close());dialog.addEventListener('click',event=>{if(event.target===dialog){const r=dialog.getBoundingClientRect();if(event.clientX<r.left||event.clientX>r.right||event.clientY<r.top||event.clientY>r.bottom)dialog.close()}});dialog.addEventListener('close',()=>{if(trigger)trigger.focus()});
})();
