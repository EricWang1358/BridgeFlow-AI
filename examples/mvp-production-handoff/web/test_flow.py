"""HTTP checks on a temporary database. No real messages or models."""
import base64,json,sqlite3,tempfile,threading
from pathlib import Path
from urllib.request import Request,urlopen
from urllib.error import HTTPError
from server import make_server,SAMPLE
results=[]
with tempfile.TemporaryDirectory() as t:
 db=str(Path(t)/'test.sqlite');server,store=make_server(db,0)
 th=threading.Thread(target=server.serve_forever,daemon=True);th.start();base=f'http://127.0.0.1:{server.server_port}'
 with urlopen(base+'/api/state',timeout=5) as r: token=json.load(r)['token']
 def post(path,p,expected=200):
  req=Request(base+path,data=json.dumps(p).encode(),headers={'Content-Type':'application/json','X-Demo-Token':token})
  try: r=urlopen(req,timeout=5)
  except HTTPError as e: r=e
  with r: code,j=r.status,json.load(r)
  assert code==expected,(path,code,j)
  return j.get('doc',j)
 def act(d,a,**kw):
  expected=kw.pop('expected',200)
  return post(f"/api/docs/{d['id']}/{a}",{'version':d['version'],**kw},expected)
 try:
  d=post('/api/create',{'sample':True});assert d['checked']['missing']==['实际量'];act(d,'submit',expected=422)
  with sqlite3.connect(db) as c: assert c.execute('SELECT COUNT(*) FROM submissions').fetchone()[0]==0
  results.append('缺失阻断入库')
  d=act(d,'patch',values={**d['checked']['values'],'实际量':'97.5 方'},note='合成依据');assert d['version']==2
  act(d,'submit',expected=422);results.append('补充后仍需复核')
  d=act(d,'approve',note='演示复核');d=act(d,'submit',simulate_notification_failure=True)
  assert d['notification']=='failed' and d['receipt'];results.append('入库与通知失败分开记录')
  act(d,'submit')
  with sqlite3.connect(db) as c:
   assert c.execute('SELECT COUNT(*) FROM submissions').fetchone()[0]==1
   assert c.execute('SELECT COUNT(*) FROM outbox').fetchone()[0]==1
  results.append('重复提交不重复入库或通知')
  d=act(d,'retry');assert d['notification']=='simulated_sent';results.append('通知独立重试')
  act(d,'complete',note='跳步',expected=409)
  d=act(d,'accept');d=act(d,'return',note='请重新核实实际量');old=d.copy()
  d=act(d,'patch',values={**d['checked']['values'],'实际量':'97'},note='合成修订');assert d['approved_version'] is None and d['receipt'] is None
  act(old,'approve',note='旧版本',expected=409);act(d,'submit',expected=422);results.append('退回修订与旧版本失效')
  d=act(d,'approve',note='修订复核');d=act(d,'submit');d=act(d,'accept');d=act(d,'complete',note='差异核对完成')
  assert d['state']=='completed';results.append('市场部接收并完成')
  import csv,io
  out=io.StringIO();w=csv.writer(out);w.writerow(SAMPLE.keys());w.writerow(SAMPLE.values())
  x=post('/api/create',{'filename':'sample.csv','data':base64.b64encode(out.getvalue().encode()).decode()});assert x['checked']['missing']==['实际量']
  post('/api/create',{'filename':'empty.csv','data':base64.b64encode('项目名称,实际量\n'.encode()).decode()},422);results.append('CSV 上传与空模板拒绝')
  x=act(x,'patch',values={**x['checked']['values'],'实际量':'-1'},note='错误样例');assert x['checked']['errors'];act(x,'approve',note='错误',expected=422);results.append('负数量拒绝')
  # Minimal XLSX fixture is generated in memory for parser verification only.
  from openpyxl import Workbook
  b=io.BytesIO();w=Workbook();s=w.active;s.append(list(SAMPLE));s.append(list(SAMPLE.values()));w.save(b)
  x=post('/api/create',{'filename':'synthetic.xlsx','data':base64.b64encode(b.getvalue()).decode()});assert x['checked']['missing']==['实际量'];results.append('XLSX 解析')
  assert any(x['id']==d['id'] and x['state']=='completed' for x in type(store)(db).all());results.append('数据库重开恢复')
  with urlopen(base+'/export/'+d['id']) as r: exported=r.read().decode('utf-8-sig')
  assert '实际量' in exported and '97' in exported;results.append('标准 CSV 导出')
  print(json.dumps({'checks_passed':len(results),'checks':results,'real_messages':0,'llm_calls':0},ensure_ascii=False,indent=2))
 finally: server.shutdown();server.server_close();th.join()
