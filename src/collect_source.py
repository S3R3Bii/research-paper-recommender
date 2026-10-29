"""Retrieve eight fixed public requests; complete responses stay outside Git."""
import argparse, hashlib, html, json, re, time, unicodedata
from datetime import datetime, timezone
from pathlib import Path
import requests

ROOT=Path(__file__).resolve().parents[1]
TOPICS=['information retrieval','recommender systems','database query optimization','software defect prediction','graph neural networks','time series forecasting','machine translation','distributed consensus']
DOI=re.compile(r'^10\.\d{4,9}/\S+$')
def dump(p,value):
 p.parent.mkdir(parents=True,exist_ok=True)
 p.write_bytes((json.dumps(value,ensure_ascii=False,sort_keys=True,indent=2)+'\n').encode())
def clean_title(value):
 return ' '.join(unicodedata.normalize('NFKC',html.unescape(re.sub(r'<[^>]*>',' ',value))).split())
def project(private):
 records={};labels={};exclusions=[];duplicates=[];requests_manifest=[]
 for i,topic in enumerate(TOPICS):
  path=private/f'request-{i}.json';raw=path.read_bytes();response=json.loads(raw)
  assert response['status']=='ok'
  items=response['message']['items'];assert len(items)<=100
  requests_manifest.append(dict(topic=topic,rows=len(items),sha256=hashlib.sha256(raw).hexdigest(),bytes=len(raw)))
  for rank,item in enumerate(items,1):
   doi=item.get('DOI','').strip().lower();title=clean_title((item.get('title') or [''])[0]);year=(item.get('published',{}).get('date-parts') or [[None]])[0][0];kind=item.get('type')
   reasons=[]
   if not DOI.fullmatch(doi):reasons.append('invalid-doi')
   if not title:reasons.append('empty-title')
   if not isinstance(year,int) or not 2018<=year<=2024:reasons.append('year-outside-fixed-window')
   if kind not in ['journal-article','proceedings-article']:reasons.append('excluded-type')
   if reasons:
    exclusions.append(dict(request=i,rank=rank,doi=doi,reasons=reasons));continue
   refs=sorted({x['DOI'].strip().lower() for x in item.get('reference',[]) if isinstance(x.get('DOI'),str) and DOI.fullmatch(x['DOI'].strip().lower())})
   if doi in records:duplicates.append(dict(doi=doi,first_topic=records[doi]['stratum'],duplicate_topic=topic,request_rank=rank))
   else:records[doi]=dict(doi=doi,title=title,year=year,type=kind,stratum=topic,partition='development' if i<4 else 'held',request_rank=rank)
   labels.setdefault(doi,set()).update(refs)
 catalog=[records[k] for k in sorted(records)]
 features=[{k:r[k] for k in ['doi','title','year','type']} for r in catalog]
 dump(ROOT/'data/catalog.json',features)
 dump(ROOT/'data/query_metadata.json',catalog)
 dump(ROOT/'data/citation_labels.json',{k:sorted(labels[k]) for k in sorted(labels)})
 dump(ROOT/'data/source_exclusions.json',exclusions);dump(ROOT/'data/source_duplicates.json',duplicates)
 hashes={str(p.relative_to(ROOT)).replace('\\','/'):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted((ROOT/'data').glob('*.json')) if p.name!='source_manifest.json'}
 dump(ROOT/'data/source_manifest.json',dict(source='Crossref REST API',requests=requests_manifest,unique_eligible=len(catalog),exclusions=len(exclusions),duplicates=len(duplicates),source_protocol='PROTOCOL.md',projection_sha256=hashes,rights='Minimal reusable metadata; no abstracts or full text',raw_responses='Private originals excluded from Git'))
 print(json.dumps(dict(status='PROJECTED',unique=len(catalog),exclusions=len(exclusions),duplicates=len(duplicates))))
def main():
 p=argparse.ArgumentParser();p.add_argument('--private-root',required=True,type=Path);p.add_argument('--project-only',action='store_true');args=p.parse_args();private=args.private_root.resolve()
 assert not private.is_relative_to(ROOT)
 private.mkdir(parents=True,exist_ok=True)
 if not args.project_only:
  for i,topic in enumerate(TOPICS):
   path=private/f'request-{i}.json';assert not path.exists(),'Do not replace a captured snapshot'
   params={'query.title':topic,'rows':100,'select':'DOI,title,published,type,reference','filter':'from-pub-date:2018-01-01,until-pub-date:2024-12-31,has-references:true'}
   start=datetime.now(timezone.utc).isoformat();r=requests.get('https://api.crossref.org/works',params=params,headers={'User-Agent':'ResearchPaperRecommender/0.1 (bounded public metadata research)'},timeout=45)
   dump(private/f'request-{i}-receipt.json',dict(url=r.url,status=r.status_code,retrieved_utc=start,headers={k:v for k,v in r.headers.items() if 'rate-limit' in k.lower()}))
   r.raise_for_status();path.write_bytes(r.content)
   print('Captured request',i,flush=True)
   interval=r.headers.get('x-rate-limit-interval','1s');delay=1.1
   if interval.endswith('s'):
    delay=max(delay,float(interval[:-1])/max(1,int(r.headers.get('x-rate-limit-limit','1')))+0.1)
   time.sleep(delay)
 project(private)
if __name__=='__main__':main()
