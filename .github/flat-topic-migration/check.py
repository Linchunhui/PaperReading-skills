#!/usr/bin/env python3
from pathlib import Path
from html.parser import HTMLParser
from html import unescape
from urllib.parse import urlsplit,unquote
from collections import Counter
import argparse,base64,json,hashlib,re,subprocess
p=argparse.ArgumentParser();p.add_argument('--repo',type=Path,required=True);p.add_argument('--snapshot',type=Path,required=True);p.add_argument('--qa',type=Path,required=True);a=p.parse_args()
root=a.repo.resolve();source=a.snapshot.resolve();qa=a.qa.resolve()
manifest=json.loads((source/'reading-manifest.json').read_text());mapping=json.loads((qa/'flat-topic-mapping.json').read_text())
class Doc(HTMLParser):
 def __init__(self,text,source_path=None):
  super().__init__(convert_charrefs=True);self.source_path=source_path;self.blocked=0;self.skip_home=False;self.visible=[];self.excluded_home=[];self.ids=[];self.links=[];self.scripts=[];self.capture=None;self.raw=[];self.typ='';self.sid='';self.attrs={};self.article_stack=[];self.articles={};self.feed(text)
 def handle_starttag(self,t,attrs):
  d=dict(attrs)
  if t in ['head','style']:self.blocked+=1
  if t=='a':
   h=d.get('href','');u=urlsplit(h);dest=(self.source_path.parent/unquote(u.path)).resolve()if(self.source_path is not None and u.path and not u.scheme and not u.netloc)else None
   self.skip_home=(h=='../../index.html#topics'or dest==source/'index.html')
  if d.get('id'):self.ids.append(d['id'])
  if t=='article':self.article_stack.append(d.get('id'))
  for k in ['href','xlink:href','src','poster','data']:
   if d.get(k):self.links.append((t,k,d[k],d))
  if t=='script':self.capture='script';self.raw=[];self.typ=d.get('type','');self.sid=d.get('id','');self.attrs=d
 def handle_endtag(self,t):
  if t in ['head','style']:self.blocked=max(0,self.blocked-1)
  if t=='a':self.skip_home=False
  if t=='article'and self.article_stack:self.article_stack.pop()
  if t==self.capture:
   self.scripts.append({'type':self.typ,'id':self.sid,'code':''.join(self.raw),'attrs':self.attrs});self.capture=None
 def handle_data(self,text):
  if self.capture:self.raw.append(text);return
  if self.blocked:return
  if self.skip_home:
   if text.strip():self.excluded_home.append(text)
   return
  if text.strip():self.visible.append(text)
  if self.article_stack and self.article_stack[-1]:self.articles.setdefault(self.article_stack[-1],[]).extend(text.split())
def subset_words(old,new):
 it=iter(new)
 return all(any(w==candidate for candidate in it)for w in old)
errors=[];rows=[];pending_anchors=[];anchor_catalog={}
def check_doc(doc,where,owner,main,aux):
 dup=[k for k,n in Counter(doc.ids).items()if n>1]
 if dup:errors.append([where,'duplicate_ids',dup[:12]])
 for tag,key,h,attrs in doc.links:
  u=urlsplit(unescape(h))
  if u.scheme in ['http','https','mailto','tel','data']or u.netloc:
   if tag in ['img','script','link']and u.scheme in ['http','https']:errors.append([where,'external_render_dependency',h[:140]])
   continue
  if u.scheme:errors.append([where,'unexpected_protocol',h[:140]]);continue
  if not u.path:
   f=unquote(u.fragment)
   if f.startswith('expanded-reading--'):pending_anchors.append((where,owner+'-topic.html',f))
   if f and f not in doc.ids and not f.startswith('expanded-reading--'):errors.append([where,'missing_own_anchor',f])
   continue
  path=unquote(u.path)
  if path=='../../index.html':continue
  target=(root/'examples/Topics'/path).resolve()
  if target.parent!=(root/'examples/Topics').resolve()or target.name not in {t['id']+'-topic.html'for t in manifest['topics']}:
   errors.append([where,'non_sibling_local_link',h[:150]])
  elif u.fragment:pending_anchors.append((where,target.name,unquote(u.fragment)))
 for s in doc.scripts:
  if s['type']in ['application/json','application/ld+json']:
   try:json.loads(s['code'])
   except Exception as e:errors.append([where,'invalid_json_script',str(e)])
  elif s['code'].strip():
   r=subprocess.run(['node','--check'],input=s['code'],text=True,capture_output=True)
   if r.returncode:errors.append([where,'javascript_syntax',r.stderr[:600]])
 for script in doc.scripts:
  if script['type']!='application/json'or script['id']=='standalone-reading-data':continue
  def walk(x):
   if isinstance(x,dict):
    for k,v in x.items():
     if k in ['href','body_href','pdf_href']and isinstance(v,str):
      u=urlsplit(v)
      if 'knowledge-systems-22-'in v or re.match(r'index\.html#',v):errors.append([where,'old_dynamic_link',v])
      if not u.scheme and u.path.endswith('-topic.html')and u.fragment:pending_anchors.append((where+'/json',Path(u.path).name,unquote(u.fragment)))
     walk(v)
   elif isinstance(x,list):
    for v in x:walk(v)
  try:walk(json.loads(script['code']))
  except Exception:pass
expected={t['id']for t in manifest['topics']}
assert len(expected)==22
assert {t['topic_id']for t in mapping['topics']}==expected
for item in manifest['files']:
 f=source/item['path']
 if hashlib.sha256(f.read_bytes()).hexdigest()!=item['sha256']:errors.append(['source','changed_original_source',item['path']])
for row in mapping['topics']:
 tid=row['topic_id'];path=root/'examples/Topics'/(tid+'-topic.html');text=path.read_text()
 if 'knowledge-systems-22-20261105/'in text or '/Users/'in text or 'file:///'in text:errors.append([tid,'old_path_in_parent'])
 parent=Doc(text);data=next((json.loads(s['code'])for s in parent.scripts if s['id']=='standalone-reading-data'),None)
 child=Doc(base64.b64decode(data['html']).decode())if data else None
 docs=[(d,parent if d['kind']=='main'else child)for d in row['documents']]
 for entry,out in docs:
  old=Doc((source/entry['source']).read_text(),source/entry['source'])
  if out is None:errors.append([tid,'missing_aux_document']);continue
  if not set(old.ids).issubset(out.ids):errors.append([tid,entry['kind'],'source_ids_lost',sorted(set(old.ids)-set(out.ids))[:20]])
  source_visible=[re.sub(r'\s+','',unescape(x))for x in old.visible]
  target_visible=re.sub(r'\s+','',unescape(' '.join(out.visible)))
  cursor=0;missing=[]
  for chunk in source_visible:
   pos=target_visible.find(chunk,cursor)
   if pos<0:missing.append(chunk[:120])
   else:cursor=pos+len(chunk)
  if missing:errors.append([tid,entry['kind'],'visible_source_text_lost',missing[:10]])
  def strip_urls(x):
   if isinstance(x,list):return[strip_urls(v)for v in x]
   if isinstance(x,dict):return{k:strip_urls(v)for k,v in x.items()if k not in ['href','body_href','pdf_href']}
   return x
  old_json=[json.loads(s['code'])for s in old.scripts if s['type']=='application/json']
  new_json=[json.loads(s['code'])for s in out.scripts if s['type']=='application/json'and s['id']!='standalone-reading-data']
  if strip_urls(old_json)!=strip_urls(new_json):errors.append([tid,entry['kind'],'research_metadata_changed'])
  for ident,words in old.articles.items():
   if ident not in out.articles or not subset_words(words,out.articles[ident]):errors.append([tid,entry['kind'],'article_text_lost_or_reordered',ident])
 combined=text+'\n'+(base64.b64decode(data['html']).decode()if data else '')
 for asset in manifest['files']:
  if not asset['path'].startswith('topics/'+tid+'/'):continue
  original=source/asset['path']
  if original.suffix.lower()in ['.html','.svg','.css','.js']:continue
  encoded=base64.b64encode(original.read_bytes()).decode()
  if encoded not in combined:errors.append([tid,'original_asset_not_embedded',asset['path']])
 anchor_catalog[tid+'-topic.html']={'main':set(parent.ids),'aux':set(child.ids)if child else set()}
 check_doc(parent,tid+'/main',tid,parent,child)
 if child:
  check_doc(child,tid+'/aux',tid,parent,child)
  if not any(s['attrs'].get('data-flat-bridge')=='child'for s in child.scripts):errors.append([tid,'missing_child_bridge'])
 rows.append({'id':tid,'bytes':path.stat().st_size,'main_ids':len(parent.ids),'main_articles':len(parent.articles),'aux_ids':len(child.ids)if child else 0,'aux_articles':len(child.articles)if child else 0,'source_documents':len(docs),'article_text_preserved':True,'excluded_home_navigation':{'main':parent.excluded_home,'aux':child.excluded_home if child else []}})
for origin,target,fragment in pending_anchors:
 catalog=anchor_catalog.get(target)
 if catalog is None:errors.append([origin,'missing_peer_topic',target]);continue
 if fragment.startswith('expanded-reading--'):
  valid=fragment[18:]in catalog['aux']
 else:valid=fragment in catalog['main']or fragment in catalog['aux']
 if not valid:errors.append([origin,'missing_cross_document_anchor',target,fragment])
home=(root/'index.html').read_text()
for tid in expected:
 if len(re.findall(r'["\']examples/Topics/'+re.escape(tid)+r'-topic\.html["\']',home))!=1:errors.append(['homepage','missing_or_duplicate_card',tid])
for name in ['speculative-decoding-topic.html','rsi-knowledge-system.html']:
 if 'examples/Topics/'+name not in home:errors.append(['homepage','lost_existing_topic',name])
if 'examples/Topics/knowledge-systems-22-'in home:errors.append(['homepage','collection_card_remains'])
if (root/'examples/Topics/knowledge-systems-22-20261105').exists():errors.append(['old_collection_still_present'])
result={'ok':not errors,'method':'Source manifest hashes, every original main/aux ID and article word order, embedded child HTML decoding, local link closure and JavaScript syntax','topics':rows,'counts':{'topics':len(rows),'source_documents':sum(r['source_documents']for r in rows),'aux':sum(r['source_documents']-1 for r in rows)},'errors':errors,'cross_document_links_checked':len(pending_anchors)}
(qa/'structural-results.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'ok':result['ok'],'counts':result['counts'],'errors':errors[:20]},ensure_ascii=False))
if errors:raise SystemExit(1)
