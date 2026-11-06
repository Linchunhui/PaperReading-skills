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
 def __init__(self,text):
  super().__init__(convert_charrefs=True);self.ids=[];self.links=[];self.scripts=[];self.capture=None;self.raw=[];self.typ='';self.sid='';self.attrs={};self.article_stack=[];self.articles={};self.feed(text)
 def handle_starttag(self,t,attrs):
  d=dict(attrs)
  if d.get('id'):self.ids.append(d['id'])
  if t=='article':self.article_stack.append(d.get('id'))
  for k in ['href','xlink:href','src','poster','data']:
   if d.get(k):self.links.append((t,k,d[k],d))
  if t=='script':self.capture='script';self.raw=[];self.typ=d.get('type','');self.sid=d.get('id','');self.attrs=d
 def handle_endtag(self,t):
  if t=='article'and self.article_stack:self.article_stack.pop()
  if t==self.capture:
   self.scripts.append({'type':self.typ,'id':self.sid,'code':''.join(self.raw),'attrs':self.attrs});self.capture=None
 def handle_data(self,text):
  if self.capture:self.raw.append(text);return
  if self.article_stack and self.article_stack[-1]:self.articles.setdefault(self.article_stack[-1],[]).extend(text.split())
def subset_words(old,new):
 it=iter(new)
 return all(any(w==candidate for candidate in it)for w in old)
errors=[];rows=[]
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
   if f and f not in doc.ids and not f.startswith('expanded-reading--'):errors.append([where,'missing_own_anchor',f])
   continue
  path=unquote(u.path)
  if path=='../../index.html':continue
  target=(root/'examples/Topics'/path).resolve()
  if target.parent!=(root/'examples/Topics').resolve()or target.name not in {t['id']+'-topic.html'for t in manifest['topics']}:
   errors.append([where,'non_sibling_local_link',h[:150]])
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
     if k in ['href','body_href','pdf_href']and isinstance(v,str)and ('knowledge-systems-22-'in v or re.match(r'index\.html#',v)):errors.append([where,'old_dynamic_link',v])
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
  old=Doc((source/entry['source']).read_text())
  if out is None:errors.append([tid,'missing_aux_document']);continue
  if not set(old.ids).issubset(out.ids):errors.append([tid,entry['kind'],'source_ids_lost',sorted(set(old.ids)-set(out.ids))[:20]])
  for ident,words in old.articles.items():
   if ident not in out.articles or not subset_words(words,out.articles[ident]):errors.append([tid,entry['kind'],'article_text_lost_or_reordered',ident])
 check_doc(parent,tid+'/main',tid,parent,child)
 if child:
  check_doc(child,tid+'/aux',tid,parent,child)
  if not any(s['attrs'].get('data-flat-bridge')=='child'for s in child.scripts):errors.append([tid,'missing_child_bridge'])
 rows.append({'id':tid,'bytes':path.stat().st_size,'main_ids':len(parent.ids),'main_articles':len(parent.articles),'aux_ids':len(child.ids)if child else 0,'aux_articles':len(child.articles)if child else 0,'source_documents':len(docs),'article_text_preserved':True})
home=(root/'index.html').read_text()
for tid in expected:
 if len(re.findall(r'["\']examples/Topics/'+re.escape(tid)+r'-topic\.html["\']',home))!=1:errors.append(['homepage','missing_or_duplicate_card',tid])
for name in ['speculative-decoding-topic.html','rsi-knowledge-system.html']:
 if 'examples/Topics/'+name not in home:errors.append(['homepage','lost_existing_topic',name])
if 'examples/Topics/knowledge-systems-22-'in home:errors.append(['homepage','collection_card_remains'])
if (root/'examples/Topics/knowledge-systems-22-20261105').exists():errors.append(['old_collection_still_present'])
result={'ok':not errors,'method':'Source manifest hashes, every original main/aux ID and article word order, embedded child HTML decoding, local link closure and JavaScript syntax','topics':rows,'counts':{'topics':len(rows),'source_documents':sum(r['source_documents']for r in rows),'aux':sum(r['source_documents']-1 for r in rows)},'errors':errors}
(qa/'structural-results.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'ok':result['ok'],'counts':result['counts'],'errors':errors[:20]},ensure_ascii=False))
if errors:raise SystemExit(1)
