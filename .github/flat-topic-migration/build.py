#!/usr/bin/env python3
from pathlib import Path
from html.parser import HTMLParser
from html import escape,unescape
from urllib.parse import urlsplit,unquote
from collections import Counter
import argparse,base64,json,mimetypes,re,shutil,hashlib,datetime

ap=argparse.ArgumentParser()
ap.add_argument('--repo',type=Path,required=True)
ap.add_argument('--snapshot',type=Path,required=True)
ap.add_argument('--qa',type=Path,required=True)
args=ap.parse_args()
R=args.repo.resolve();T=R/'examples/Topics';C=T/'knowledge-systems-22-20261105';S=args.snapshot.resolve();Q=args.qa.resolve()
if not S.exists():shutil.copytree(C,S)
P=[S/t['href']for t in json.loads((S/'reading-manifest.json').read_text())['topics']]
assert len(P)==22,len(P)
M={p.resolve():p.parent.name+'-topic.html' for p in P};A={};info={};records=[]
def jtext(x):return json.dumps(x,ensure_ascii=False,separators=(',',':')).replace('</','<\\/')
def local(h,source):
 u=urlsplit(h)
 return (None,unquote(u.fragment)) if u.scheme or u.netloc or not u.path else ((source.parent/unquote(u.path)).resolve(),unquote(u.fragment))

class Info(HTMLParser):
 def __init__(self,text):
  super().__init__(convert_charrefs=True);self.ids=[];self.articles=[];self.title=[];self.deck=[];self.h=0;self.d=0;self.images=0;self.feed(text)
 def handle_starttag(self,t,a):
  a=dict(a)
  if a.get('id'):self.ids.append(a['id'])
  if t=='article' and a.get('id'):self.articles.append(a['id'])
  if t=='h1':self.h+=1
  if t=='p' and 'deck' in (a.get('class')or'').split():self.d+=1
  if t=='img':self.images+=1
 def handle_endtag(self,t):
  if t=='h1':self.h=max(0,self.h-1)
  if t=='p':self.d=0
 def handle_data(self,d):
  if self.h:self.title.append(d)
  if self.d:self.deck.append(d)

for p in P:
 tid=p.parent.name;i=Info(p.read_text())
 aux=[p.parent/x for x in ['legacy.html','baseline.html','deep-reading.html','remote-baseline/index.html'] if (p.parent/x).exists()]
 assert len(aux)<=1
 if aux:A[aux[0].resolve()]=tid+'-topic.html'
 info[tid]={'title':''.join(i.title).strip(),'desc':''.join(i.deck).strip(),'ids':set(i.ids),'articles':i.articles,'aux':aux[0]if aux else None,'auxids':set(Info(aux[0].read_text()).ids)if aux else set()}

def href(h,source,tid,aux=False,auxids=None):
 dest,frag=local(h,source);auxids=auxids or set();name=tid+'-topic.html'
 if dest is None:return h,False
 own=(S/'topics'/tid/'index.html').resolve()
 if dest==own:
  if aux:
   if frag and frag not in info[tid]['ids'] and frag in auxids:return '#'+frag,False
   return name+('#'+frag if frag else '#top'),False
  return '#'+frag if frag else '#top',False
 if dest in A:
  if A[dest]==name:
   if aux:return '#'+frag if frag else '#top',False
   return '#expanded-reading--'+frag if frag else '#expanded-reading',True
  return A[dest]+('#expanded-reading--'+frag if frag else '#expanded-reading'),False
 if dest in M:return M[dest]+('#'+frag if frag else ''),False
 if dest.is_dir()and(dest/'index.html').resolve()in M:return M[(dest/'index.html').resolve()]+('#'+frag if frag else ''),False
 if dest==S or dest==S/'index.html':return '../../index.html#topics',False
 if dest.exists()and dest.is_file():
  if dest.suffix.lower()=='.html':raise ValueError('Unclassified HTML '+str(dest))
  return uri(dest)+('#'+frag if frag else ''),False
 if dest.name=='index.html'and(not frag or frag in ['topics','top']):return '../../index.html#topics',False
 raise ValueError(f'Unresolved {h} in {source}')

def payload(x,source,tid,aux,ids):
 if isinstance(x,list):return[payload(v,source,tid,aux,ids)for v in x]
 if not isinstance(x,dict):return x
 d={k:payload(v,source,tid,aux,ids)for k,v in x.items()}
 for key in ['href','body_href','pdf_href']:
  if isinstance(d.get(key),str)and d[key]:d[key]=href(d[key],source,tid,aux,ids)[0]
 for item in d.get('other_topics',[]):
  if item.get('id')in info:item['href']=item['id']+'-topic.html#local-materials'
 return d

def svg_owner(p):
 try:tid=p.relative_to(S/'topics').parts[0]
 except ValueError:return None,False
 return tid,('remote-baseline'in p.parts or p.name in ['legacy.html','baseline.html','deep-reading.html','deep-reading.svg'])
def portable_svg(text,source):
 tid,aux=svg_owner(source)
 if tid not in info:return text
 def change(m):
  tag=m[0];hm=re.search(r'((?:xlink:)?href)\s*=\s*(["\'])(.*?)\2',tag,re.S)
  if not hm:return tag
  old=unescape(hm[3])
  if old.startswith('#'):dest=tid+'-topic.html'+('#expanded-reading--'if aux else'#')+old[1:]
  else:
   dest,_=href(old,source,tid,aux,info[tid].get('auxids',set()))
   if dest.startswith('#'):dest=tid+'-topic.html'+('#expanded-reading--'+dest[1:]if aux else dest)
  return tag[:hm.start()]+hm[1]+'="'+escape(dest,quote=True)+'"'+tag[hm.end():]
 return re.sub(r'<(?:[A-Za-z_][\w.-]*:)?a\b[^>]*>',change,text)
def uri(p):
 raw=p.read_bytes()
 if p.suffix.lower()=='.svg':raw=portable_svg(raw.decode(),p).encode()
 return 'data:'+(mimetypes.guess_type(str(p))[0]or'application/octet-stream')+';base64,'+base64.b64encode(raw).decode()
def css(text,source):
 def sub(m):
  v=m[1].strip(' "\'');p,_=local(v,source)
  return 'url('+uri(p)+')'if p is not None and p.exists()else m[0]
 return re.sub(r'url\(([^)]+)\)',sub,text)
def inline_svg(text,source,tid,aux,prefix):
 ids=set(Info(text).ids)
 def identity(m):return m[1]+m[2]+prefix+m[3]+m[2]if m[3]in ids else m[0]
 text=re.sub(r'(\bid\s*=\s*)(["\'])(.*?)\2',identity,text)
 for ident in sorted(ids,key=len,reverse=True):
  text=text.replace('url(#'+ident+')','url(#'+prefix+ident+')')
  text=re.sub(r'((?:xlink:)?href\s*=\s*["\'])#'+re.escape(ident)+r'(["\'])',lambda m:m[1]+'#'+prefix+ident+m[2],text)
 def aria(m):return m[1]+m[2]+' '.join(prefix+x if x in ids else x for x in m[3].split())+m[2]
 text=re.sub(r'(\baria-(?:labelledby|describedby)\s*=\s*)(["\'])(.*?)\2',aria,text)
 return '<div class="standalone-inline-svg" style="width:100%">'+Rewrite(text,source,tid,aux).result()+'</div>'

class Rewrite(HTMLParser):
 def __init__(self,text,source,tid,aux=False):
  super().__init__(convert_charrefs=False)
  self.source=source;self.tid=tid;self.aux=aux;self.ids=set(Info(text).ids);self.out=[];self.capture=None;self.raw=[];self.replacement=None;self.kind='';self.svgserial=0;self.feed(text);self.close()
 def tag(self,t,a):return '<'+t+''.join(' '+k+('="'+escape(str(v),quote=True)+'"'if v is not None else'')for k,v in a.items())+'>'
 def handle_starttag(self,t,attrs):
  a=dict(attrs)
  if t=='img'and a.get('src'):
   value=a['src'];sp,_=local(value,self.source);svg=None;ss=self.source
   if sp is not None and sp.suffix.lower()=='.svg':svg=sp.read_text();ss=sp
   elif value.lower().startswith('data:image/svg+xml'):
    hd,body=value.split(',',1);svg=base64.b64decode(body).decode()if';base64'in hd else unquote(body)
   if svg is not None:
    self.svgserial+=1;self.out.append(inline_svg(svg,ss,self.tid,self.aux,'flat-svg-'+self.tid+'-'+str(self.svgserial)+'-'));return
  if t=='svg':a['style']=(a.get('style')or'')+';max-width:100%;height:auto'
  if t=='link'and'stylesheet'in(a.get('rel')or'')and a.get('href'):
   p,_=local(a['href'],self.source)
   if p is not None:self.out.append('<style>'+css(p.read_text(),p)+'</style>');return
  if t in ['script','style']:
   self.capture=t;self.raw=[];self.kind=a.get('type','');self.replacement=None
   if t=='script'and a.get('src'):
    p,_=local(a['src'],self.source)
    if p is not None:self.replacement=p.read_text();del a['src']
  for k in ['src','poster','data']:
   if a.get(k):
    p,_=local(a[k],self.source)
    if p is not None:a[k]=uri(p)
  for k in ['href','xlink:href']:
   if not a.get(k):continue
   original=a[k];a[k],expanded=href(original,self.source,self.tid,self.aux,self.ids)
   if expanded:a['data-expanded-anchor']=unquote(urlsplit(original).fragment)
   if t=='a'and a[k].startswith('data:'):a['download']=Path(urlsplit(original).path).name
   if self.aux and t=='a'and not a[k].startswith(('#','data:')):a['target']='_top'if not urlsplit(a[k]).scheme else'_blank'
  self.out.append(self.tag(t,a))
 def handle_startendtag(self,t,a):
  self.handle_starttag(t,a)
  if t not in ['area','base','br','col','embed','hr','img','input','link','meta','param','source','track','wbr']:self.handle_endtag(t)
 def handle_endtag(self,t):
  if t==self.capture:
   text=self.replacement if self.replacement is not None else ''.join(self.raw)
   if t=='script'and self.kind=='application/json':text=jtext(payload(json.loads(text),self.source,self.tid,self.aux,self.ids))
   if t=='style':text=css(text,self.source)
   self.out.append(text);self.capture=None;self.raw=[]
  self.out.append('</'+t+'>')
 def handle_data(self,d):(self.raw if self.capture else self.out).append(d)
 def handle_entityref(self,n):(self.raw if self.capture else self.out).append('&'+n+';')
 def handle_charref(self,n):(self.raw if self.capture else self.out).append('&#'+n+';')
 def handle_comment(self,d):self.out.append('<!--'+d+'-->')
 def handle_decl(self,d):self.out.append('<!'+d+'>')
 def result(self):return ''.join(self.out)

def append_body(html,extra):
 pos=html.lower().rfind('</body>');assert pos>=0
 return html[:pos]+extra+html[pos:]
def home_label(text):
 return re.sub(r'(<a\b[^>]*href="\.\./\.\./index\.html#topics"[^>]*>).*?(</a>)',lambda m:m[1]+'← 返回阅读首页'+m[2],text,flags=re.S)

FRAME_JS=r'''(()=>{'use strict';
 const token=__TOKEN__;
 const emit=data=>parent.postMessage({topicStandalone:token,...data},'*');let last=0;
 const size=()=>{const h=Math.ceil(Math.max(document.body.scrollHeight,document.documentElement.scrollHeight));if(Math.abs(h-last)>2){last=h;emit({height:h})}};
 const jump=id=>{if(id){location.hash=id;window.dispatchEvent(new HashChangeEvent('hashchange'))}setTimeout(()=>{const el=id?document.getElementById(id):document.body;if(el)emit({jump:el.getBoundingClientRect().top+window.scrollY});size()},90)};
 window.addEventListener('message',e=>{if(e.source===parent&&e.data?.topicStandalone===token&&e.data.navigate!==undefined)jump(e.data.navigate)});
 document.addEventListener('click',e=>{const a=e.target.closest('a');if(!a)return;const h=a.getAttribute('href')||a.getAttribute('xlink:href')||'';if(h.startsWith('#')){e.preventDefault();emit({anchor:decodeURIComponent(h.slice(1))})}else if(h&&!h.startsWith('data:')&&!/^[a-z]+:/i.test(h))a.setAttribute('target','_top')});
 new ResizeObserver(size).observe(document.body);window.addEventListener('load',size);document.fonts?.ready.then(size);setTimeout(size,100);emit({ready:true});
})();'''
HOST_JS=r'''(()=>{'use strict';
 const data=JSON.parse(document.getElementById('standalone-reading-data').textContent);
 const box=document.getElementById('expanded-reading'),mount=document.getElementById('expanded-reading-frame');
 const mainIds=new Set(data.mainIds),auxIds=new Set(data.auxIds);let frame=null,pending='',ready=false;
 const ensure=()=>{box.open=true;if(frame)return;frame=document.createElement('iframe');frame.dataset.flatSource=data.source;frame.title='完整方法、论文原图与扩展资料';frame.style.cssText='display:block;width:100%;height:900px;border:0;background:transparent';frame.setAttribute('sandbox','allow-scripts allow-same-origin allow-downloads allow-popups allow-top-navigation-by-user-activation');frame.srcdoc=new TextDecoder().decode(Uint8Array.from(atob(data.html),c=>c.charCodeAt(0)));mount.append(frame)};
 const navigate=id=>{pending=id;ensure();if(ready)frame.contentWindow.postMessage({topicStandalone:data.token,navigate:id},'*')};
 const route=()=>{const id=decodeURIComponent(location.hash.slice(1));if(id==='expanded-reading'){navigate('');return}if(id.startsWith('expanded-reading--')){navigate(id.slice(18));return}if(!mainIds.has(id)&&(auxIds.has(id)||id.startsWith('material-')))navigate(id)};
 box.addEventListener('toggle',()=>{if(box.open)ensure()});
 document.addEventListener('click',e=>{const a=e.target.closest('a[data-expanded-anchor]');if(!a)return;e.preventDefault();const id=a.dataset.expandedAnchor;const h=id?'#expanded-reading--'+encodeURIComponent(id):'#expanded-reading';if(location.hash===h)navigate(id);else location.hash=h});
 window.addEventListener('message',e=>{if(!frame||e.source!==frame.contentWindow||e.data?.topicStandalone!==data.token)return;const m=e.data;if(Number.isFinite(m.height))frame.style.height=Math.min(2000000,Math.max(300,m.height))+'px';if(m.ready){ready=true;frame.contentWindow.postMessage({topicStandalone:data.token,navigate:pending},'*')}if(m.anchor!==undefined){pending=m.anchor;const h=m.anchor?'#expanded-reading--'+encodeURIComponent(m.anchor):'#expanded-reading';if(location.hash!==h)history.pushState(null,'',h);frame.contentWindow.postMessage({topicStandalone:data.token,navigate:m.anchor},'*')}if(Number.isFinite(m.jump))window.scrollTo({top:frame.getBoundingClientRect().top+window.scrollY+m.jump-28,behavior:'smooth'})});
 window.addEventListener('hashchange',route);route();
})();'''

for p in P:
 tid=p.parent.name;d=info[tid];aux=d['aux'];raw=p.read_text();html=Rewrite(raw,p,tid).result();auxids=set();auxbytes=0;auxarticles=[]
 if 'top'not in d['ids']:
  html=re.sub(r'<body(\s[^>]*)?>',lambda m:m[0]+'<span id="top"></span>',html,count=1);d['ids'].add('top')
 if aux:
  ar=aux.read_text();ai=Info(ar);auxids=set(ai.ids);auxarticles=ai.articles;child=Rewrite(ar,aux,tid,True).result();token='standalone-'+tid
  if 'top'not in auxids:
   child=re.sub(r'<body(\s[^>]*)?>',lambda m:m[0]+'<span id="top"></span>',child,count=1);auxids.add('top')
  child=home_label(child)
  child=append_body(child,'<script data-flat-bridge="child">'+FRAME_JS.replace('__TOKEN__',json.dumps(token))+'</script>');auxbytes=len(child.encode())
  data={'token':token,'source':str(aux.relative_to(S)),'html':base64.b64encode(child.encode()).decode(),'mainIds':sorted(d['ids']),'auxIds':sorted(auxids)}
  extra='<style>.standalone-reading{margin:40px auto;border:1px solid #aab3ae;border-radius:8px;padding:18px;max-width:1600px}.standalone-reading>summary{cursor:pointer;font-size:1.15rem;font-weight:700;line-height:1.6}.standalone-reading>p{font:15px/1.7 system-ui,sans-serif}.standalone-reading iframe{max-width:100%}</style><details id="expanded-reading" class="standalone-reading"><summary>完整方法演进、论文原图与扩展资料</summary><p>展开后可在本页连续阅读完整资料，内容已包含在当前文件中。</p><div id="expanded-reading-frame"></div></details><script type="application/json" id="standalone-reading-data">'+jtext(data)+'</script><script data-flat-bridge="parent">'+HOST_JS+'</script>'
  html=append_body(html,extra)
 dest=T/(tid+'-topic.html');html=home_label(html);dest.write_text(html)
 i=Info(html);dups=[k for k,n in Counter(i.ids).items()if n>1];assert not dups,(tid,dups)
 documents=[{'source':str(p.relative_to(S)),'section_id':'','sha256':hashlib.sha256(raw.encode()).hexdigest(),'kind':'main'}]+([{'source':str(aux.relative_to(S)),'section_id':'expanded-reading','sha256':hashlib.sha256(aux.read_bytes()).hexdigest(),'kind':'aux'}]if aux else [])
 records.append({'id':tid,'topic_id':tid,'target':'examples/Topics/'+dest.name,'file':'examples/Topics/'+dest.name,'title':d['title'],'source':str(p.relative_to(S)),'source_sha256':hashlib.sha256(raw.encode()).hexdigest(),'documents':documents,'aux_source':str(aux.relative_to(S))if aux else None,'aux_bytes_embedded':auxbytes,'main_ids':sorted(d['ids']),'aux_ids':sorted(auxids),'main_articles':d['articles'],'aux_articles':auxarticles,'output_bytes':dest.stat().st_size,'sha256':hashlib.sha256(dest.read_bytes()).hexdigest()})
 print(tid,dest.stat().st_size,flush=True)

home=R/'index.html';text=home.read_text()
cards=',\n      '.join(json.dumps({'file':r['file'],'title':r['title'],'desc':info[r['topic_id']]['desc']},ensure_ascii=False)for r in records)+',\n      '
pat=r'\{\s*file:\s*"examples/Topics/knowledge-systems-22-20261105/"[^}]*\},\s*'
text,n=re.subn(pat,lambda _:cards,text)
assert n==1 or all(r['file']in text for r in records),'Missing collection card'
text=re.sub(r'\{\s*file:\s*"examples/Topics/image-generation-acceleration/"[^}]*\},\s*','',text)
text=text.replace('cat, section, navLink, expanded: false,',"cat, section, navLink, expanded: cat.id === 'topics',")
text=text.replace('每个分类默认展示两行，展开可查看全部笔记。','专题默认全部展开，其他分类默认展示两行。')
home.write_text(text)
rows=''.join('<article><h2><a href="'+r['topic_id']+'-topic.html">'+escape(r['title'])+'</a></h2><p>'+escape(info[r['topic_id']]['desc'])+'</p></article>'for r in records)
rows+='<article><h2><a href="rsi-knowledge-system.html">RSI · 递归自我改进</a></h2><p>围绕候选生成、反馈、评估与改进器组织研究脉络。</p></article><article><h2><a href="speculative-decoding-topic.html">投机解码 · 草稿、验证与预算</a></h2><p>围绕草稿、验证与预算，结合机制对照、论文原图和适用条件。</p></article>'
(T/'index.html').write_text('<!DOCTYPE html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Topics · 研究专题</title><style>body{font:18px/1.7 system-ui,sans-serif;background:#0d1117;color:#e6edf3;max-width:1000px;margin:auto;padding:40px 24px}a{color:#58a6ff}article{background:#161b22;border:1px solid #30363d;border-radius:12px;padding:20px;margin:20px 0}h1{font-size:32px}</style></head><body><nav><a href="../../index.html#topics">返回阅读首页</a></nav><h1>Topics · 研究专题</h1><p>每个专题均为独立HTML，正文、图表和扩展阅读包含在同一文件中。</p>'+rows+'</body></html>')
readme=R/'README.md';lines=[]
for line in readme.read_text().splitlines():
 if 'examples/Topics/knowledge-systems-22-20261105/'in line:lines.extend('- ['+r['title']+'](https://linchunhui.github.io/PaperReading-skills/'+r['file']+')'for r in records)
 elif 'examples/Topics/image-generation-acceleration/'not in line:lines.append(line)
readme.write_text('\n'.join(lines)+'\n');Q.mkdir(parents=True,exist_ok=True)
(Q/'flat-topic-mapping.json').write_text(json.dumps({'built_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'source_snapshot':str(S),'topics':records,'max_html_bytes':max(r['output_bytes']for r in records),'strategy':'lazy self-contained srcdoc with automatic height and anchor bridge; research prose retained'},ensure_ascii=False,indent=2)+'\n')
if C.exists():shutil.rmtree(C)
print('DONE',Q/'flat-topic-mapping.json',flush=True)
