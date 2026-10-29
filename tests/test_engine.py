import math,unittest
from recommender.engine import tokens,rank,recommend
def row(doi,title,year=2020):return dict(doi=doi,title=title,year=year,type='journal-article')
def exercise_contract(fn):
 docs=[row('10.1234/b','graph neural networks'),row('10.1234/a','graph neural networks'),row('10.1234/c','graph methods'),row('10.1234/d','bread baking')]
 got=fn('Graph neural networks',docs,'jaccard')
 assert [r['doi'] for r in got]==['10.1234/a','10.1234/b'];assert all(r['score']==1 for r in got);assert all(r['terms']==['graph','networks','neural'] for r in got)
 assert fn('',docs,'jaccard')==[];assert fn('the and of',docs,'jaccard')==[];assert fn('zzzx qqqx',docs,'jaccard')==[]
 one=fn('graph neural extra',[docs[0]],'jaccard');assert len(one)==1 and one[0]['score']==.5
 assert fn('graph',[docs[0]],'jaccard')==[]
 assert [r['doi'] for r in fn('graph neural networks',list(reversed(docs)),'jaccard')]==[r['doi'] for r in got]
 assert docs[0]==row('10.1234/b','graph neural networks')
 return 10
class EngineTests(unittest.TestCase):
 def test_exercise_contract(self):self.assertEqual(exercise_contract(rank),10)
 def test_normalization(self):self.assertEqual(tokens('THE Ｇraph &amp; <b>Neural</b> systems'),['graph','neural','systems'])
 def test_cosine_contributions(self):
  results=rank('graph neural neural networks',[row('10.1234/a','graph neural networks'),row('10.1234/b','graph methods systems')],'cosine')
  self.assertEqual(len(results),1);self.assertAlmostEqual(results[0]['score'],sum(results[0]['contributions'].values()),places=11);self.assertGreater(results[0]['score'],0);self.assertLessEqual(results[0]['score'],1)
 def test_threshold_boundary(self):
  docs=[row('10.1234/a','graph neural network')];r=recommend('graph neural',docs,method='jaccard',threshold=2/3);self.assertFalse(r['abstained']);self.assertTrue(recommend('graph neural',docs,method='jaccard',threshold=.7)['abstained'])
 def test_known_doi_and_year(self):
  docs=[row('10.1234/query','graph neural networks',2022),row('10.1234/old','graph neural networks',2021),row('10.1234/same','graph neural networks',2022),row('10.1234/future','graph neural networks',2023)]
  r=recommend('https://doi.org/10.1234/query',docs,method='jaccard',threshold=0);self.assertEqual([x['doi'] for x in r['results']],['10.1234/old']);self.assertEqual(r['candidate_count'],1)
 def test_label_blindness(self):
  docs=[dict(row('10.1234/a','graph neural networks'),reference=['10.1234/x'],partition='held')];self.assertEqual(recommend('graph neural',docs,method='jaccard',threshold=0)['results'],recommend('graph neural',[row('10.1234/a','graph neural networks')],method='jaccard',threshold=0)['results'])
 def test_unmatched_abstain(self):self.assertTrue(recommend('zzzx qqqx',[row('10.1234/a','graph neural')],method='cosine',threshold=0)['abstained'])
 def test_validation(self):
  for kw in [dict(threshold=float('nan')),dict(threshold=-1),dict(threshold=True),dict(limit=True),dict(limit=0),dict(before_year=2101),dict(method='unknown')]:
   with self.assertRaises(ValueError):recommend('graph neural',[],method=kw.pop('method','jaccard'),threshold=kw.pop('threshold',0),**kw)
 def test_query_limit(self):
  with self.assertRaises(ValueError):recommend('x'*501,[],method='jaccard',threshold=0)
if __name__=='__main__':unittest.main()
