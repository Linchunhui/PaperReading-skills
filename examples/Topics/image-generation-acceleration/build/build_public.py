"""Build the public edition while keeping the supplied report read-only.
Usage: python build_public.py --source ORIGINAL_REPORT_DIR --corpus PDF_DIR
Requires beautifulsoup4, pymupdf, pillow. No network calls.
"""
from pathlib import Path
import argparse,base64,hashlib,json,re,shutil,html,math
from bs4 import BeautifulSoup
import pymupdf
from PIL import Image,ImageDraw

ap=argparse.ArgumentParser();ap.add_argument('--source',type=Path,required=True);ap.add_argument('--corpus',type=Path,required=True);ap.add_argument('--output',type=Path);a=ap.parse_args()
ROOT=Path(__file__).resolve().parent;OUT=a.output or ROOT/'repo/examples/Topics/image-generation-acceleration';OUT.mkdir(parents=True,exist_ok=True)
def read(p):return json.loads(p.read_text())
def write(p,d):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def clean(x):
 if isinstance(x,dict):
  out={k:clean(v) for k,v in x.items() if k not in ['source_pdf','local_pdf','entry_source_file','browser_evidence_files']}
  for k,v in x.items():
   if k.endswith('href') and isinstance(v,str) and not v.startswith(('http:','https:','#')):
    out[k]='#'+v.split('#',1)[1] if '#paper-' in v else None
  return out
 if isinstance(x,list):return [clean(v) for v in x]
 if isinstance(x,str):
  if x.startswith(('/Users/','/tmp/','../')):return '原调研归档：'+Path(x).name
  return re.sub(r'/Users/[^\s"<>]+','[本地归档路径已隐藏]',x)
 return x
topic=read(a.source/'topic.json');adds=read(ROOT/'additions.json');specs=read(ROOT/'figure-additions.json')
s=BeautifulSoup((a.source/'index.html').read_text(),'html.parser')
def fragment(x):return BeautifulSoup(x,'html.parser')
papers={p['arxiv_id']:p for b in topic['branches'] for p in b['papers']}
figures=read(a.source/'figures-manifest.json');outfig=[]
for i,f in enumerate(figures):
 f['arxiv_id']=f.get('arxiv_id') or f['paper_id']
 p=papers[f['arxiv_id']];version=f.get('version') or f.get('source_version') or p.get('checked_version') or p.get('pdf_version') or ''
 f['version']=version if re.fullmatch(r'v\d+',str(version)) else ''
 src=a.source/f['file'];dest=OUT/'figures'/Path(f['file']).name;dest.parent.mkdir(exist_ok=True);shutil.copyfile(src,dest)
 item=clean(f);item['file']=str(dest.relative_to(OUT));item['source_url']='https://arxiv.org/pdf/'+f['arxiv_id']+f['version']+'#page='+str(f['page']);item['png_sha256']=sha(dest);item['status']='原稿图与核验记录保留；本轮文件哈希确认';outfig.append(item)
for f in specs:
 # Tight crops exclude body text and retain all diagram labels.
 if f['id']=='2607.26004':f['bbox']=[302,98,534,244]
 if f['id']=='2505.21136':f['bbox'][3]=179
 src=a.corpus/('arxiv_'+f['id'].replace('.','_')+'.pdf');d=pymupdf.open(src);page=d[f['page']-1]
 dest=OUT/'figures'/f"{f['id']}-fig{f['figure']}-v3edition.png";page.get_pixmap(matrix=pymupdf.Matrix(2.5,2.5),clip=pymupdf.Rect(f['bbox'])).save(dest)
 item={**f,'arxiv_id':f['id'],'file':str(dest.relative_to(OUT)),'pdf_sha256':sha(src),'png_sha256':sha(dest),'pdf_pages':len(d),'source_url':f"https://arxiv.org/pdf/{f['id']}{f['version']}#page={f['page']}",'coordinate_system':'PyMuPDF points; top-left origin','scale':2.5,'status':'固定版本本地PDF；全页已查看，最终裁图另行QA'};outfig.append(item)
for im in s.select('img[src^="data:image/png;base64,"]'):
 raw=base64.b64decode(im['src'].split(',',1)[1]);h=hashlib.sha256(raw).hexdigest();match=next((f for f in outfig if f['png_sha256']==h),None)
 assert match,'Original embedded PNG not found in manifest';im['src']=match['file'];im['loading']='lazy';im['decoding']='async'
for b in topic['branches']:
 for p in adds:
  if p['branch']!=b['id']:continue
  pid='paper-p'+p['id'].replace('.','-');entry=f'''<article class="paper new-paper" id="{pid}"><p class="paper-meta">{p['name']} · 首发 {p['date']} · 采用 {p['version']} · 本轮增补 {p['round']}</p><div class="paper-label"><h3>{html.escape(p['title'])}</h3></div><p class="paper-goal">{p['method']}</p><ol class="steps">{''.join('<li>'+x+'</li>' for x in p['steps'])}</ol><aside class="experiment"><h4>原文证据与实验范围</h4><p>{p['evidence']}</p></aside><p class="boundary"><strong>适用边界</strong>{p['boundary']}</p><p class="source"><a href="{p['url']}" target="_blank" rel="noopener">固定来源与原图入口 ↗</a></p></article>'''
  s.select_one('#'+b['id']).append(fragment(entry));b['papers'].append({'arxiv_id':p['id'],'id':'p'+p['id'].replace('.','-'),'name':p['name'],'date':p['date'],'url':p['url'],'method':p['method'],'version':p['version'],'evidence_status':'官方代码与摘要' if p['name']=='EDM' else '本轮方法与实验相关原文核验','addition':p})
  papers[p['id']]=b['papers'][-1]
for f in specs:
 p=papers[f['id']];art=s.select_one('#paper-p'+f['id'].replace('.','-'));assert art
 info=next(x for x in outfig if x['arxiv_id']==f['id'] and 'v3edition' in x['file']);img=Image.open(OUT/info['file']);w,h=img.size;fid='newfig-'+f['id'].replace('.','-')
 fig=f'''<figure class="original-figure"><div class="original-figure-head"><strong>{p['name']} · 作者原图 {f['figure']}</strong><button class="figure-zoom" aria-controls="{fid}" aria-pressed="false" type="button">放大原图</button></div><div class="original-art" id="{fid}" style="--reading-width:1100px;--native-width:{w}px"><img src="{info['file']}" width="{w}" height="{h}" loading="lazy" decoding="async" alt="{html.escape(f['reading'])}"></div><figcaption><b>读图：</b>{f['reading']}<p class="figure-source">作者原图，{f['version']}，PDF文件第{f['page']}页。仅裁切周围正文，未重绘。<a href="{info['source_url']}" target="_blank" rel="noopener">原文该页 ↗</a></p></figcaption></figure>'''
 target=art.select_one('.experiment');target.insert_before(fragment(fig)) if target else art.append(fragment(fig))
for p in adds:
 if not any(f['arxiv_id']==p['id'] for f in outfig):
  s.select_one('#paper-p'+p['id'].replace('.','-')).append(fragment(f'<details class="figure-unavailable"><summary>原图阅读线索 · 本地缺图</summary><p>{p["figure_hint"]}</p><p class="small">未嵌入作者图。图注/相关方法已读；PDF下载未完成或版本未确认。请从上方原文入口查看，不以自绘图代替。</p></details>'))
s.select_one('#paper-p2206-00364').append(fragment('<p class="source"><a href="https://github.com/NVlabs/edm/blob/62072d2612c7da05165d6233d13d17d71f213fee/generate.py">官方采样实现固定提交</a> · <a href="https://github.com/NVlabs/edm">官方README与复现配置</a></p>'))
# Remove private file links and retain the corresponding public paper-page links.
for link in s.select('a[href]'):
 href=link['href']
 if 'paper-corpus-' in href:
  art=link.find_parent('article');aid=next((k for k in papers if art and art.get('id')=='paper-p'+k.replace('.','-')),None)
  f=next((v for v in outfig if v['arxiv_id']==aid),None)
  if f:link['href']=f['source_url'];link.string='固定版本PDF该页 ↗'
  else:link.decompose()
 elif href.startswith('../knowledge-systems-'):
  link['href']='../index.html';link.string='← 专题目录'
 elif href=='source-manifest.json':link['href']='provenance/source-manifest.json'
 elif not href.startswith(('http','#','data:')) and (a.source/href.split('#')[0]).is_file():
  src=a.source/href.split('#')[0];dest=OUT/'provenance'/href;dest.parent.mkdir(parents=True,exist_ok=True)
  if src.name=='all-candidate-statuses.json':
   rows=read(src);bundle=json.loads(s.select_one('script[type="application/json"]').string);allowed={v.get('paper_id') for v in bundle['papers']}|{v.get('canonical_id') for v in bundle['papers']}
   kept=[{k:v for k,v in row.items() if k in ['paper_id','canonical_id','title','status','reason','url','branches','routes']} for row in rows if row.get('paper_id') in allowed or row.get('canonical_id') in allowed]
   write(dest,{'scope':'公开版只列当前专题候选的简要归属记录，未发布其他领域全量本地语料','original_record_count':len(rows),'public_related_count':len(kept),'records':clean(kept)})
  elif src.suffix=='.json':write(dest,clean(read(src)))
  else:shutil.copyfile(src,dest)
  link['href']='provenance/'+href
for b in topic['branches']:
 chapter=s.select_one('#'+b['id']);chapter.attrs.pop('style',None)
 tree=chapter.select_one('.method-tree')
 links=''.join(f'<a href="#paper-{p["id"]}">{p["name"]}<small>{p.get("date","")}</small></a>' for p in sorted(b['papers'],key=lambda p:p.get('date','')))
 if tree:tree.replace_with(fragment(f'<nav class="paper-directory" aria-label="{b["label"]}全部论文">{links}</nav>'))
 # Old compact paper-name links are retained, current full directory supersedes them.
count=sum(len(b['papers']) for b in topic['branches']);assert count==72
for node in list(s.find_all(string=True)):
 if node.parent.name in ['style','script']:continue
 st=str(node).replace('共约100次网络评估','共约100次等效单分支评估').replace('全部64项正文','既有64项正文').replace('64篇/份论文与技术报告','72篇/份论文与技术资料（64项保留、8项增补）')
 if st!=str(node):node.replace_with(st)
s.select_one('#cost code').string='T总 ≈ T固定 + Σₜ[T计算(t)+T通信(t)−T重叠(t)] + T排队'
s.select_one('#cost').append(fragment('<p class="small">NFE统一口径与重叠通信说明见<a href="#accounting">成本记账</a>。旧论文表内NFE保持作者定义；教学账本使用等效单分支评估数。</p>'))
s.select_one('#paper-p2603-24800').insert(0,fragment('<p class="editor-note">分类补注：Calibri是黑盒标量对齐，可改善同质量下的NFE；与轨迹蒸馏分开理解。</p>'))
s.select_one('#paper-p2410-10629').append(fragment('<p class="editor-note">图2条件补注：4096²、A100、batch=1；469→41→24→21→9.6秒是累计设计步骤，不是独立可相乘倍率；1023秒FLUX基线另列。</p>'))
for id,text in {'2410.10629':'先沿柱图逐项看空间压缩、线性注意力、调度与内核的累计影响，再看A100/batch1条件。柱高是秒，不能把每项收益当独立变量。','2605.06376':'先看顶部动态时间锚点，再看下部CA、DM和离轨迹CDM三类监督。颜色区分训练信号，不能从图推断推理额外运行三套网络。','2402.19481':'从左向右看不同GPU的patch计算与异步all-gather。关键是把上一时刻上下文通信与当前计算重叠，不能把计算与全部通信耗时简单相加。'}.items():
 art=s.select_one('#paper-p'+id.replace('.','-'));cap=art.select_one('figcaption')
 if cap:cap.insert(0,fragment('<p><b>读图顺序：</b>'+text+'</p>'))
# New vector atlas: all current papers, with explicit problem-membership edges.
(OUT/'diagrams').mkdir(exist_ok=True)
colors=['#6d28d9','#0369a1','#047857','#b45309','#be185d','#4338ca']
def svg_for(b,idx):
 ps=sorted(b['papers'],key=lambda p:p.get('date',''));cols=3 if len(ps)>22 else 2;rows=math.ceil(len(ps)/cols);rh=min(75,760/rows);cw=1700/cols
 z=[f'<svg xmlns="http://www.w3.org/2000/svg" width="1920" height="1080" viewBox="0 0 1920 1080"><title>{html.escape(b["label"])}：全部{len(ps)}项</title><rect width="1920" height="1080" fill="#f8fafc"/><text x="80" y="95" font-size="42" font-weight="700" fill="{colors[idx]}" font-family="sans-serif">{idx+1:02} · {html.escape(b["label"])} / {len(ps)}项</text><text x="80" y="145" font-size="23" fill="#334155" font-family="sans-serif">按首发日期排列；连线表示问题归属；有色条为本轮增补。论文详解与证据见正文。</text><path d="M80 180 H1840" stroke="{colors[idx]}" stroke-width="3"/>']
 for i,p in enumerate(ps):
  col=i//rows;row=i%rows;x=100+cw*col;y=220+rh*row;new='addition' in p
  z.append(f'<a href="../index.html#paper-{p["id"]}" target="_top"><path d="M{x} 180 V{y+20} H{x+18}" stroke="#94a3b8" fill="none"/><rect x="{x+18}" y="{y}" width="{cw-40}" height="{rh-8}" rx="8" fill="white" stroke="#cbd5e1"/><rect x="{x+18}" y="{y}" width="6" height="{rh-8}" fill="{colors[idx] if new else "#cbd5e1"}"/><text x="{x+38}" y="{y+27}" fill="#172033" font-size="25" font-weight="600" font-family="sans-serif">{html.escape(p["name"])}</text><text x="{x+38}" y="{y+49}" fill="#475569" font-size="17" font-family="sans-serif">{p.get("date", "日期待核")} · {"增补" if new else "保留"}</text></a>')
 z.append('<text x="80" y="1030" font-size="20" fill="#475569" font-family="sans-serif">PaperReading · 图像生成推理加速 · 2026-11-05 · 原创整理图，非论文作者原图</text></svg>');return ''.join(z)
atlas=s.select_one('#atlas');atlas.clear();atlas.append(fragment('<p class="kicker">完整方法地图</p><h2>六个成本问题 · 72个节点</h2><p>地图与正文使用同一条目集；有色条标新增，灰条标保留。连线表示问题归属，不表示学术继承。点击展开；SVG中的论文名可跳至正文。</p>'))
for i,b in enumerate(topic['branches']):
 path='diagrams/'+b['id']+'.svg';(OUT/path).write_text(svg_for(b,i));atlas.append(fragment(f'<details class="atlas-sheet"><summary>{i+1:02} · {b["label"]} · {len(b["papers"])}项</summary><div class="mapframe"><object data="{path}" type="image/svg+xml" aria-label="{b["label"]}论文图"><img src="{path}" alt="{b["label"]}全部论文图"></object></div><p><a href="{path}" download>下载SVG</a> · <a href="#{b["id"]}">读本章正文</a></p></details>'))
overview=s.select_one('#overview');overview.clear();overview.append(fragment('<summary>问题总览 · 点击展开</summary><div class="overview-grid">'+''.join(f'<a href="#{b["id"]}" style="--tile:{colors[i]}"><span>{i+1:02}</span><b>{b["label"]}</b><small>{len(b["papers"])}项 · {html.escape(b["description"])}</small></a>' for i,b in enumerate(topic['branches']))+'</div>'));overview.attrs.pop('open',None)
timeline=s.select_one('#timeline');timeline.clear();timeline.append(fragment('<h2>时间线</h2><p class="small">首次公开日；版本另列。时间先后不代表继承。FlashAttention的已读PDF修订号未确认，EDM全文待补。</p><div class="timeline-current">'+''.join(f'<a href="#paper-{p["id"]}"><time>{p.get("date","")}</time><b>{p["name"]}</b><small>{"本轮新增" if "addition" in p else "原稿保留"}</small></a>' for p in sorted(papers.values(),key=lambda x:x.get('date','')) )+'</div>'))
toc=s.select_one('.toc');toc.clear();toc.append(fragment('<div><a href="#edition">开始</a><a href="#primer">入门</a><a href="#lineage">谱系</a><a href="#selection">选型</a><a href="#accounting">口径</a><a href="#sensenova">SenseNova</a>'+''.join(f'<a href="#{b["id"]}">{b["label"]}</a>' for b in topic['branches'])+'<a href="#new-audit">核验范围</a></div>'))
s.select_one('main').insert(0,fragment((ROOT/'frontmatter.html').read_text()))
s.select_one('.mastline').append(fragment('<label class="theme-picker">阅读主题 <select id="theme-select" aria-label="阅读主题"><option value="system">跟随系统</option><option value="light">浅色</option><option value="dark">深色</option></select></label>'))
s.select_one('.report-index').clear();s.select_one('.report-index').append(fragment(f'<div><dt>成本问题</dt><dd>06</dd></div><div><dt>资料节点</dt><dd>{count}</dd></div><div><dt>作者原图</dt><dd>{len(outfig)}</dd></div>'))
s.body.insert(0,fragment('<a class="skip-link" href="#edition">跳到正文</a>'))
# Retain historical audit, make edition scope explicit.
audit=s.select_one('#research-audit');audit.insert(0,fragment('<p class="editor-note">以下为原稿调研记录（64项版本），本轮另见“新增检索与核验范围”。历史候选数量不是当前正文总数。</p>'))
if s.select_one('#local-materials'):
 s.select_one('#local-materials').insert(0,fragment('<p class="editor-note">下方为原稿本地候选库快照，不等于当前72项正文。InstaFlow等本轮新增状态请以上方正文及新增核验记录为准。</p>'))
for embedded in s.select('script[type="application/json"]'):
 embedded.string=json.dumps(clean(json.loads(embedded.string)),ensure_ascii=False).replace('</','<\\/')
auditnew='''<section class="card" id="new-audit"><p class="kicker">检索与核验透明度</p><h2>本轮实际做了什么</h2><p>实际调用GPT Researcher 0.16.0的conduct_research()两次；运行模式live，由当前会话模型提供规划、web.run提供实时搜索，经技能文件桥接。每轮1次初始搜索＋4条子查询；不是独立部署的无人值守搜索服务，也未重放旧结果。</p><p>R1相关规范论文候选10项；R2为10项论文及单列官方工程文档。R2与R1交集0，重复率0%；与原稿64项重合的R2论文3项（SVDQuant、TaylorSeer、AutoTarget）。达到两轮预设上限停止，未达到85%重复率的饱和阈值。FlashAttention来自后续定向原文补核，不能记作Researcher独有发现。</p><p>新增8项：InstaFlow、ADD、LADD、EDM、TGATE、ViDiT-Q、FlashAttention、SageAttention2++。前7篇中的EDM仅官方代码＋摘要核验；FlashAttention已读公开PDF的算法与实验，但未确认修订号。SageAttention2++为本地v3方法与实验；其余新增项为固定版本HTML方法与实验段。既有64项与13图保留，另增12图，总计25图；未声称72项都配图。</p><p>新PDF下载因执行环境网络审批连续两次超时而未执行；EDM PDF另遇工具内容大小限制，OpenReview遇验证页。未绕过访问限制。缺少可核本地图的条目保留原文链接与读图线索；论文数字均为作者报告，未复现。</p><p>仍待补：Diffusion2GAN、Rectified Diffusion、Guided Distillation、近期采样兼容性研究，以及移动端/国产卡的同条件端到端测量。TeaCache原论文主要视频证据单列，不把视频倍率转作图像倍率；其官方图像实现属于额外工程线索。</p><p><a href="provenance/research-summary.json">检索与版本记录</a> · <a href="provenance/figures-manifest.json">全部原图来源/哈希/裁剪参数</a> · <a href="provenance/topic.json">结构化条目</a> · <a href="NOTICE.md">图像版权与使用说明</a></p></section>'''
audit.insert_before(fragment(auditnew))
init="try{let t=localStorage.getItem('image-acceleration-theme')||'system';document.documentElement.dataset.theme=t==='system'?(matchMedia('(prefers-color-scheme: dark)').matches?'dark':'light'):t;}catch(e){}"
st=s.new_tag('script');st.string=init;s.head.insert(2,st)
css=s.new_tag('link',rel='stylesheet',href='theme.css');s.head.append(css)
js=s.new_tag('script',src='theme.js');s.body.append(js)
# Remove obsolete map initializer; existing figure enlargement logic stays intact.
for script in s.select('script:not([src])'):
 if script.string and "const zoom =" in script.string:
  txt=script.string;start=txt.find("document.querySelectorAll('.figure-zoom')");script.string=txt[start:]
for obj in s.select('img'):
 if not obj.get('alt'):obj['alt']='专题问题图，详见邻近正文'
for t in s.select('table'):
 for th in t.select('thead th'):th['scope']='col'
 for th in t.select('tbody th'):th['scope']='row'
write(OUT/'provenance/figures-manifest.json',outfig);write(OUT/'provenance/topic.json',clean(topic));write(OUT/'provenance/source-manifest.json',clean(read(a.source/'source-manifest.json')))
(OUT/'index.html').write_text(str(s));shutil.copyfile(ROOT/'theme.css',OUT/'theme.css');shutil.copyfile(ROOT/'theme.js',OUT/'theme.js')
write(ROOT/'review/build-report.json',{'papers':count,'images':len(outfig),'original_sha256':sha(a.source/'index.html'),'html_sha256':sha(OUT/'index.html'),'added_papers':[p['id'] for p in adds]})
print(json.dumps({'papers':count,'images':len(outfig),'html_bytes':(OUT/'index.html').stat().st_size}))
