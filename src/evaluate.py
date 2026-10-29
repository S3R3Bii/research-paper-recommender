"""Development-only selection, then separately invoked frozen held scoring."""
import argparse,csv,hashlib,json,sys
from fractions import Fraction
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from recommender.engine import rank
TOPICS=['information retrieval','recommender systems','database query optimization','software defect prediction','graph neural networks','time series forecasting','machine translation','distributed consensus']
NEGATIVES=['sourdough starter feeding schedule','bicycle tire puncture repair','indoor orchid watering tips','watercolor landscape brush technique','packing suitcase beach holiday','sour cherry jam recipe','acoustic guitar string replacement','puppy house training schedule']
def read(name):return json.loads((ROOT/name).read_text(encoding='utf-8'))
def dump(name,x):
 p=ROOT/name;p.parent.mkdir(exist_ok=True,parents=True);p.write_bytes((json.dumps(x,indent=2,ensure_ascii=False,sort_keys=True)+'\n').encode())
def csvout(name,rows):
 p=ROOT/name;p.parent.mkdir(exist_ok=True,parents=True)
 with p.open('w',encoding='utf-8',newline='') as f:
  writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
def coverage():
 catalog=read('data/catalog.json');meta=read('data/query_metadata.json');labels=read('data/citation_labels.json');out=[]
 for q in meta:
  older={r['doi'] for r in catalog if r['year']<q['year']};positive=set(labels[q['doi']])&older
  out.append(dict(doi=q['doi'],partition=q['partition'],stratum=q['stratum'],year=q['year'],candidate_count=len(older),deposited_reference_count=len(labels[q['doi']]),in_corpus_older_references=len(positive),evaluable=int(bool(positive))))
 return catalog,meta,labels,out
def summarize(rows):
 n=len(rows);answered=sum(r['answered'] for r in rows);hits=sum(r['hit5'] for r in rows)
 fractions={'coverage':Fraction(answered,n),'hit5_all':Fraction(hits,n),'hit5_answered':Fraction(hits,answered) if answered else Fraction(0),'recall5':sum((Fraction(r['hits'],r['positives']) for r in rows),Fraction(0))/n,'mrr5':sum((Fraction(1,r['first_hit_rank']) if r['first_hit_rank'] else Fraction(0) for r in rows),Fraction(0))/n,'utility':sum((Fraction(1) if r['hit5'] else Fraction(-1,4) if r['answered'] else Fraction(0) for r in rows),Fraction(0))/n}
 return dict(queries=n,answered=answered,hits=hits,**{k:float(v) for k,v in fractions.items()},exact={k:str(v) for k,v in fractions.items()})
def run(partition,configs):
 catalog,meta,labels,covered=coverage();eligible={r['doi'] for r in covered if r['partition']==partition and r['evaluable']}
 assert len(eligible)>=10,'Coverage hold; do not change fixed source requests'
 rows=[];predictions=[]
 for q in meta:
  if q['doi'] not in eligible:continue
  candidates=[r for r in catalog if r['year']<q['year']];positive=set(labels[q['doi']])&{r['doi'] for r in candidates}
  for method in sorted({x[0] for x in configs}):
   ordered=rank(q['title'],candidates,method)
   for m,t in configs:
    if m!=method:continue
    key=f'{method}-t{t:.1f}';answered=int(bool(ordered) and ordered[0]['score']>=t);chosen=ordered[:5] if answered else []
    ranks=[i for i,r in enumerate(chosen,1) if r['doi'] in positive]
    rows.append(dict(config=key,method=method,threshold=t,doi=q['doi'],stratum=q['stratum'],positives=len(positive),answered=answered,hits=len(ranks),hit5=int(bool(ranks)),first_hit_rank=min(ranks) if ranks else 0,top_score=ordered[0]['score'] if ordered else 0))
    for i,r in enumerate(chosen,1):predictions.append(dict(config=key,query_doi=q['doi'],candidate_doi=r['doi'],rank=i,score=r['score'],is_deposited_reference=int(r['doi'] in positive),terms=json.dumps(r['terms']),contributions=json.dumps(r['contributions'],sort_keys=True)))
 summaries=[]
 for m,t in configs:
  selected=[r for r in rows if r['method']==m and r['threshold']==t]
  summaries.append(dict(method=m,threshold=t,overall=summarize(selected),strata={topic:summarize([r for r in selected if r['stratum']==topic]) for topic in TOPICS if any(r['stratum']==topic for r in selected)}))
 csvout('results/'+partition+'_queries.csv',rows);csvout('results/'+partition+'_rankings.csv',predictions);dump('results/'+partition+'_metrics.json',summaries)
 return summaries
def main():
 p=argparse.ArgumentParser();p.add_argument('stage',choices=['development','held']);a=p.parse_args()
 if a.stage=='development':
  _,_,_,covered=coverage();csvout('results/coverage.csv',covered)
  summaries=run('development',[(m,t) for m in ['jaccard','cosine'] for t in [0,.1,.2,.3,.4]])
  chosen=sorted(summaries,key=lambda r:(-Fraction(r['overall']['exact']['utility']),r['threshold'],0 if r['method']=='jaccard' else 1))[0]
  dump('results/selection.json',dict(method=chosen['method'],threshold=chosen['threshold'],primary_metric='mean hypothetical citation-proxy utility',exact_utility=chosen['overall']['exact']['utility'],candidates=10,tie_break='lower threshold then Jaccard',uses_held_labels=False))
  print(json.dumps(dict(stage='development',selection=read('results/selection.json'),metrics=chosen['overall'])))
 else:
  frozen=read('results/frozen_dependencies.json')
  for name,digest in frozen['sha256'].items():assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==digest,name
  chosen=read('results/selection.json');configs=list(dict.fromkeys([(chosen['method'],chosen['threshold']),('jaccard',0.0)]));summaries=run('held',configs)
  from recommender.engine import recommend
  negatives=[dict(input=q,output=recommend(q,method=chosen['method'],threshold=chosen['threshold'])) for q in NEGATIVES]
  dump('results/synthetic_negative_controls.json',negatives)
  print(json.dumps(dict(stage='held',metrics=summaries,synthetic_abstentions=sum(x['output']['abstained'] for x in negatives))))
if __name__=='__main__':main()
