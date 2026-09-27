#!/usr/bin/env python3
"""Aid Atlas local research workbench. Loopback-only, no external dependencies."""
import argparse, contextlib, datetime, difflib, hashlib, json, math, re, sqlite3, threading, time
from html.parser import HTMLParser
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse, parse_qs, unquote
from urllib.request import Request, build_opener, HTTPRedirectHandler

ROOT=Path(__file__).resolve().parent
DEFAULT_DB=ROOT/'.data'/'atlas.sqlite3'
SOURCES=[
 {'id':'lsc-intake','title':'LSC — Online Intake & Triage','url':'https://www.lsc.gov/i-am-grantee/grantee-guidance/lsc-reporting-requirements/tig-reporting/online-intake-triage','scope':'U.S. civil legal aid · Historical operational case studies'},
 {'id':'lsc-justice-gap','title':'LSC — 2022 Justice Gap','url':'https://justicegap.lsc.gov/resource/section-1-introduction/','scope':'U.S. civil legal aid · 2021 survey and intake data'},
 {'id':'lsc-technology','title':'LSC — Technology in Legal Aid','url':'https://www.lsc.gov/i-am-grantee/model-practices-innovations/technology','scope':'U.S. civil legal aid · Program technology guidance'}]
SOCIETIES=[{'id':'pilot','name':'Community Aid Society','demo':True},{'id':'partner','name':'Partner Aid Society','demo':True}]
BRANCHES=[{'id':'north','society':'pilot','name':'North branch'},{'id':'central','society':'pilot','name':'Central branch'},{'id':'south','society':'pilot','name':'South branch'},{'id':'partner-main','society':'partner','name':'Partner office'}]
JOB_LOCK=threading.Lock()
RUNNING=False

def now():return datetime.datetime.now(datetime.timezone.utc).isoformat(timespec='seconds')
@contextlib.contextmanager
def connection(db):
 c=sqlite3.connect(str(db),timeout=15);c.row_factory=sqlite3.Row
 try:
  yield c;c.commit()
 except Exception:c.rollback();raise
 finally:c.close()
def society_check(s):
 if s not in {x['id'] for x in SOCIETIES}:raise ValueError('Unknown society.')
def init_db(db):
 Path(db).parent.mkdir(parents=True,exist_ok=True)
 with connection(db) as c:
  c.executescript('''
  CREATE TABLE IF NOT EXISTS metric_rows(society TEXT,branch_id TEXT,period TEXT,intakes INTEGER,completed INTEGER,staff_minutes REAL,recontacts INTEGER,referrals INTEGER,accepted_referrals INTEGER,origin TEXT,updated_at TEXT,PRIMARY KEY(society,branch_id,period));
  CREATE TABLE IF NOT EXISTS sources(id TEXT PRIMARY KEY,title TEXT,url TEXT,scope TEXT,last_checked TEXT,last_error TEXT);
  CREATE TABLE IF NOT EXISTS snapshots(id INTEGER PRIMARY KEY,source_id TEXT,hash TEXT,text TEXT,created_at TEXT);
  CREATE TABLE IF NOT EXISTS source_reviews(id INTEGER PRIMARY KEY,source_id TEXT,snapshot_id INTEGER,status TEXT,created_at TEXT,reviewed_at TEXT);
  CREATE TABLE IF NOT EXISTS policies(id INTEGER PRIMARY KEY,society TEXT,title TEXT,body TEXT,status TEXT,created_at TEXT);
  CREATE TABLE IF NOT EXISTS audit(id INTEGER PRIMARY KEY,society TEXT,action TEXT,detail TEXT,created_at TEXT);
  CREATE TABLE IF NOT EXISTS jobs(id INTEGER PRIMARY KEY,status TEXT,started_at TEXT,finished_at TEXT,result TEXT);
  CREATE TABLE IF NOT EXISTS settings(key TEXT PRIMARY KEY,value TEXT);
  ''')
  for s in SOURCES:c.execute('INSERT OR IGNORE INTO sources(id,title,url,scope) VALUES(?,?,?,?)',(s['id'],s['title'],s['url'],s['scope']))
  c.execute("INSERT OR IGNORE INTO settings VALUES('auto_refresh','false')")
  if not c.execute('SELECT 1 FROM metric_rows LIMIT 1').fetchone():
   for i,b in enumerate(BRANCHES):
    for month in [7,8]:
     n=85+i*19+(month-7)*12;done=int(n*(.70+i*.035));minutes=done*(29-i*2)
     c.execute('INSERT INTO metric_rows VALUES(?,?,?,?,?,?,?,?,?,?,?)',(b['society'],b['id'],f'2026-{month:02}',n,done,minutes,18+i*3,20+i*2,14+i*2,'Synthetic demo',now()))

def metrics(db,society):
 society_check(society)
 with connection(db) as c:return [dict(r) for r in c.execute('SELECT * FROM metric_rows WHERE society=? ORDER BY period,branch_id',(society,))]
def import_metrics(db,society,rows):
 society_check(society)
 fields={'branch_id','period','intakes','completed','staff_minutes','recontacts','referrals','accepted_referrals'}
 if not isinstance(rows,list) or not rows or len(rows)>1200:raise ValueError('Import 1–1,200 aggregate rows.')
 allowed={b['id'] for b in BRANCHES if b['society']==society};keys=set()
 for r in rows:
  if not isinstance(r,dict) or set(r)!=fields:raise ValueError('Use exactly the eight aggregate metric columns. No client information.')
  if r['branch_id'] not in allowed:raise ValueError('Branch does not belong to selected society.')
  if not isinstance(r['period'],str) or not re.fullmatch(r'20\d{2}-(0[1-9]|1[0-2])',r['period']):raise ValueError('Period must be YYYY-MM.')
  key=(r['branch_id'],r['period'])
  if key in keys:raise ValueError('Duplicate branch/month in import.')
  keys.add(key)
  for k in fields-{'branch_id','period'}:
   v=r[k]
   if isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v) or v<0 or v>10000000:raise ValueError('Metrics must be finite non-negative numbers, at most 10 million.')
   if k!='staff_minutes' and int(v)!=v:raise ValueError('Counts must be whole numbers.')
  if r['completed']>r['intakes']:raise ValueError('Completed intakes cannot exceed intakes.')
  if r['accepted_referrals']>r['referrals']:raise ValueError('Accepted referrals cannot exceed referrals.')
 with connection(db) as c:
  for r in rows:c.execute('INSERT OR REPLACE INTO metric_rows VALUES(?,?,?,?,?,?,?,?,?,?,?)',(society,r['branch_id'],r['period'],r['intakes'],r['completed'],r['staff_minutes'],r['recontacts'],r['referrals'],r['accepted_referrals'],'User imported',now()))
  c.execute('INSERT INTO audit(society,action,detail,created_at) VALUES(?,?,?,?)',(society,'metrics_import',f'{len(rows)} branch-month rows imported',now()))
 return len(rows)

def validate_source_url(url):
 p=urlparse(url)
 if p.scheme!='https' or p.hostname not in {'www.lsc.gov','lsc.gov','justicegap.lsc.gov'} or p.username or p.password or p.port not in (None,443):raise ValueError('Only approved HTTPS LSC source hosts are allowed.')
 return url
class RestrictedRedirect(HTTPRedirectHandler):
 def redirect_request(self,req,fp,code,msg,headers,newurl):
  validate_source_url(newurl);return super().redirect_request(req,fp,code,msg,headers,newurl)
class PageText(HTMLParser):
 def __init__(self):super().__init__();self.skip=0;self.parts=[]
 def handle_starttag(self,tag,attrs):
  if tag in ('script','style','noscript','svg','nav','footer','header'):self.skip+=1
  if not self.skip and tag in ('p','div','li','h1','h2','h3','section','br'):self.parts.append('\n')
 def handle_endtag(self,tag):
  if tag in ('script','style','noscript','svg','nav','footer','header') and self.skip:self.skip-=1
  if not self.skip and tag in ('p','div','li','h1','h2','h3'):self.parts.append('\n')
 def handle_data(self,data):
  if not self.skip:self.parts.append(data)
 def result(self):return '\n'.join(s for s in (re.sub(r'\s+',' ',x).strip() for x in ''.join(self.parts).splitlines()) if s)
def fetch_source(url):
 validate_source_url(url)
 with build_opener(RestrictedRedirect).open(Request(url,headers={'User-Agent':'AidAtlasLocalResearch/0.1 (public source change monitoring)'}),timeout=20) as response:
  validate_source_url(response.geturl())
  if 'text/html' not in response.headers.get('Content-Type',''):raise ValueError('Expected an HTML source page.')
  raw=response.read(2_000_001)
  if len(raw)>2_000_000:raise ValueError('Source exceeds the 2 MB limit.')
  parser=PageText();parser.feed(raw.decode('utf-8',errors='replace'));text=parser.result()
  if len(text)<300:raise ValueError('Too little source text; manual inspection required.')
  return text[:200000]
def record_snapshot(db,source_id,text):
 digest=hashlib.sha256(text.encode()).hexdigest()
 with connection(db) as c:
  old=c.execute('SELECT hash FROM snapshots WHERE source_id=? ORDER BY id DESC LIMIT 1',(source_id,)).fetchone()
  c.execute('UPDATE sources SET last_checked=?,last_error=NULL WHERE id=?',(now(),source_id))
  if old and old['hash']==digest:return 'unchanged'
  snap=c.execute('INSERT INTO snapshots(source_id,hash,text,created_at) VALUES(?,?,?,?)',(source_id,digest,text,now())).lastrowid
  c.execute("INSERT INTO source_reviews(source_id,snapshot_id,status,created_at) VALUES(?,?,'needs_review',?)",(source_id,snap,now()))
  return 'changed' if old else 'first_snapshot'
def run_refresh(db,job):
 global RUNNING
 results=[]
 try:
  for source in SOURCES:
   try:status=record_snapshot(db,source['id'],fetch_source(source['url']));results.append({'source':source['id'],'status':status})
   except Exception as e:
    error=str(e)[:300]
    with connection(db) as c:c.execute('UPDATE sources SET last_checked=?,last_error=? WHERE id=?',(now(),error,source['id']))
    results.append({'source':source['id'],'status':'failed','error':error})
  with connection(db) as c:c.execute('UPDATE jobs SET status=?,finished_at=?,result=? WHERE id=?',('completed' if all(r['status']!='failed' for r in results) else 'completed_with_errors',now(),json.dumps(results),job))
 finally:
  with JOB_LOCK:RUNNING=False
def start_refresh(db):
 global RUNNING
 with JOB_LOCK:
  if RUNNING:return None
  RUNNING=True
  with connection(db) as c:job=c.execute("INSERT INTO jobs(status,started_at) VALUES('running',?)",(now(),)).lastrowid
 threading.Thread(target=run_refresh,args=(db,job),daemon=True).start();return job

def bootstrap(db,society):
 society_check(society)
 with connection(db) as c:
  sources=[dict(r) for r in c.execute('SELECT s.*, (SELECT count(*) FROM snapshots n WHERE n.source_id=s.id) AS versions FROM sources s')]
  reviews=[dict(r) for r in c.execute('SELECT r.*,s.title,s.url FROM source_reviews r JOIN sources s ON s.id=r.source_id ORDER BY r.id DESC LIMIT 30')]
  policies=[dict(r) for r in c.execute('SELECT * FROM policies WHERE society=? ORDER BY id DESC',(society,))]
  jobs=[dict(r) for r in c.execute('SELECT * FROM jobs ORDER BY id DESC LIMIT 5')]
  audit=[dict(r) for r in c.execute('SELECT * FROM audit WHERE society=? ORDER BY id DESC LIMIT 15',(society,))]
  auto=c.execute("SELECT value FROM settings WHERE key='auto_refresh'").fetchone()[0]=='true'
 return {'societies':SOCIETIES,'branches':[b for b in BRANCHES if b['society']==society],'metrics':metrics(db,society),'sources':sources,'reviews':reviews,'policies':policies,'jobs':jobs,'audit':audit,'auto_refresh':auto,'localPrototype':True}

def scheduler(db):
 while True:
  time.sleep(60)
  with connection(db) as c:
   enabled=c.execute("SELECT value FROM settings WHERE key='auto_refresh'").fetchone()[0]=='true'
   last=c.execute('SELECT started_at FROM jobs ORDER BY id DESC LIMIT 1').fetchone()
  if enabled and (not last or (datetime.datetime.now(datetime.timezone.utc)-datetime.datetime.fromisoformat(last[0])).total_seconds()>21600):start_refresh(db)

class Handler(SimpleHTTPRequestHandler):
 def __init__(self,*args,**kwargs):super().__init__(*args,directory=str(ROOT),**kwargs)
 def valid_host(self):return self.headers.get('Host') in {f'127.0.0.1:{self.server.server_port}',f'localhost:{self.server.server_port}'}
 def json(self,value,status=200):
  body=json.dumps(value).encode();self.send_response(status);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(body)));self.send_header('Cache-Control','no-store');self.send_header('X-Content-Type-Options','nosniff');self.end_headers();self.wfile.write(body)
 def end_headers(self):
  self.send_header('X-Content-Type-Options','nosniff');self.send_header('Referrer-Policy','same-origin');super().end_headers()
 def do_GET(self):
  if not self.valid_host():return self.json({'error':'Invalid host'},403)
  parsed=urlparse(self.path)
  if parsed.path.startswith('/api/'):
   try:
    args=parse_qs(parsed.query);society=args.get('society',['pilot'])[0]
    if parsed.path=='/api/bootstrap':return self.json(bootstrap(self.server.db,society))
    if parsed.path=='/api/source':
     source_id=args.get('id',[''])[0]
     if source_id not in {s['id'] for s in SOURCES}:raise ValueError('Unknown source')
     snapshot=int(args.get('snapshot',['2147483647'])[0])
     with connection(self.server.db) as c:snaps=[dict(r) for r in c.execute('SELECT * FROM snapshots WHERE source_id=? AND id<=? ORDER BY id DESC LIMIT 2',(source_id,snapshot))]
     if not snaps:return self.json({'source':source_id,'text':'No successful refresh yet.','diff':'','created_at':None})
     diff='\n'.join(difflib.unified_diff((snaps[1]['text'] if len(snaps)>1 else '').splitlines(),snaps[0]['text'].splitlines(),fromfile='previous',tofile='latest',lineterm=''))
     return self.json({'source':source_id,'text':snaps[0]['text'],'diff':diff[:100000],'created_at':snaps[0]['created_at']})
    if parsed.path=='/api/health':return self.json({'ok':True,'storage':'SQLite','networkScope':'loopback-only'})
    return self.json({'error':'Not found'},404)
   except ValueError as e:return self.json({'error':str(e)},400)
  path=unquote(parsed.path)
  # Expose only public assets, never database, source code, tests, or repository metadata.
  target=ROOT/path.lstrip('/')
  allowed={'/','/index.html','/workspace.html','/system.html','/style.css','/workspace-theme.css','/landing.css','/system.css','/app.js','/landing.js','/impact.js','/system.js','/favicon.svg','/logo.svg','/map.js','/paper.pdf'}
  if path not in allowed:return self.json({'error':'Not found'},404)
  return super().do_GET()
 def do_HEAD(self):
  if not self.valid_host():return self.json({'error':'Invalid host'},403)
  if urlparse(self.path).path not in {'/','/index.html','/workspace.html','/system.html','/paper.pdf'}:return self.json({'error':'Not found'},404)
  return super().do_HEAD()
 def do_POST(self):
  if not self.valid_host():return self.json({'error':'Invalid host'},403)
  origin=self.headers.get('Origin');expected={f'http://127.0.0.1:{self.server.server_port}',f'http://localhost:{self.server.server_port}'}
  if (origin and origin not in expected) or self.headers.get('X-Aid-Atlas')!='local' or 'application/json' not in self.headers.get('Content-Type',''):return self.json({'error':'Same-origin local request required'},403)
  try:
   length=int(self.headers.get('Content-Length','0'))
   if length<1 or length>2_000_000:raise ValueError('Request must be 1 byte to 2 MB.')
   body=json.loads(self.rfile.read(length));path=urlparse(self.path).path;society=body.get('society','pilot');society_check(society)
   if path=='/api/metrics/import':return self.json({'imported':import_metrics(self.server.db,society,body.get('rows'))})
   if path=='/api/research/refresh':return self.json({'job':start_refresh(self.server.db),'message':'Refresh started or already running.'})
   if path=='/api/settings':
    if type(body.get('auto_refresh')) is not bool:raise ValueError('auto_refresh must be boolean')
    with connection(self.server.db) as c:c.execute("UPDATE settings SET value=? WHERE key='auto_refresh'",('true' if body['auto_refresh'] else 'false',))
    return self.json({'saved':True})
   if path=='/api/policies':
    title=body.get('title','');text=body.get('body','')
    if not isinstance(title,str) or not isinstance(text,str) or not 3<=len(title.strip())<=120 or not 10<=len(text.strip())<=10000:raise ValueError('Use a title of 3–120 characters and policy text of 10–10,000 characters.')
    with connection(self.server.db) as c:
     pid=c.execute("INSERT INTO policies(society,title,body,status,created_at) VALUES(?,?,?,'draft',?)",(society,title.strip(),text.strip(),now())).lastrowid
     c.execute('INSERT INTO audit(society,action,detail,created_at) VALUES(?,?,?,?)',(society,'policy_draft',f'Draft {pid} created in local prototype',now()))
    return self.json({'id':pid})
   if path=='/api/reviews/acknowledge':
    rid=body.get('id')
    if type(rid) is not int:raise ValueError('Review id required')
    with connection(self.server.db) as c:
     row=c.execute('SELECT * FROM source_reviews WHERE id=?',(rid,)).fetchone()
     if not row:raise ValueError('Review not found')
     c.execute("UPDATE source_reviews SET status='acknowledged',reviewed_at=? WHERE id=?",(now(),rid))
     c.execute('INSERT INTO audit(society,action,detail,created_at) VALUES(?,?,?,?)',(society,'source_acknowledged',f'Public-source review {rid}; local operator, no authenticated identity',now()))
    return self.json({'acknowledged':True})
   return self.json({'error':'Not found'},404)
  except (ValueError,TypeError,AttributeError,json.JSONDecodeError) as e:return self.json({'error':str(e)},400)
  except Exception:return self.json({'error':'Operation failed. Check local server logs.'},500)

def main():
 parser=argparse.ArgumentParser();parser.add_argument('--port',type=int,default=8766);parser.add_argument('--db',type=Path,default=DEFAULT_DB);args=parser.parse_args();init_db(args.db)
 with connection(args.db) as c:c.execute("UPDATE jobs SET status='interrupted',finished_at=? WHERE status='running'",(now(),))
 server=ThreadingHTTPServer(('127.0.0.1',args.port),Handler);server.db=args.db
 threading.Thread(target=scheduler,args=(args.db,),daemon=True).start()
 print(f'Aid Atlas: http://127.0.0.1:{args.port} | local data: {args.db}',flush=True)
 try:server.serve_forever()
 except KeyboardInterrupt:server.server_close()
if __name__=='__main__':main()
