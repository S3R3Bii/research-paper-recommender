"""Independent synthetic-control and exercised UI record checks."""
import hashlib,json
from pathlib import Path
from verify_results import tokenize
ROOT=Path(__file__).resolve().parents[1]
def main():
 read=lambda p:json.loads((ROOT/p).read_text(encoding='utf-8'))
 chosen=read('results/selection.json');assert chosen['method']=='jaccard'
 catalog=read('data/catalog.json');controls=read('results/synthetic_negative_controls.json');checks=0
 assert len(controls)==8
 for control in controls:
  q=set(tokenize(control['input']));scores=[]
  for r in catalog:
   d=set(tokenize(r['title']));common=q&d
   if len(common)>=2:scores.append(round(len(common)/len(q|d),12))
  expected=not scores or max(scores)<chosen['threshold'];actual=control['output'];assert expected==actual['abstained'];assert actual['method']==chosen['method'] and actual['threshold']==chosen['threshold'];assert actual['candidate_count']==len(catalog);assert actual['results']==[];checks+=5
 ui=read('results/ui_verification.json')
 for name,digest in ui['file_sha256'].items():assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==digest;checks+=1
 result=dict(status='PASS',checks=checks,authored_controls=8,abstentions=sum(x['output']['abstained'] for x in controls),unknown='Human relevance, multilingual and general out-of-domain safety; finite synthetic negatives are not those validations')
 (ROOT/'results/independent_controls.json').write_bytes((json.dumps(result,indent=2)+'\n').encode());print(json.dumps(result))
if __name__=='__main__':main()
