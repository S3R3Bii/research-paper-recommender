import argparse,json
from .engine import recommend
p=argparse.ArgumentParser(description='Related paper titles, not verified claim support')
p.add_argument('query');p.add_argument('--limit',type=int,default=5);p.add_argument('--before-year',type=int)
a=p.parse_args();print(json.dumps(recommend(a.query,limit=a.limit,before_year=a.before_year),ensure_ascii=False,indent=2))
