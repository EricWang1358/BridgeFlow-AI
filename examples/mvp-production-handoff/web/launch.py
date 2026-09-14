"""Start/stop this local demo only. Opening a browser is a user launch action."""
import json,os,signal,subprocess,sys,time,webbrowser
from pathlib import Path
from urllib.request import urlopen
ROOT=Path(__file__).resolve().parent
DATA=ROOT/'data';DATA.mkdir(exist_ok=True)
STATE=DATA/'process.json'
def identity(pid):
 return subprocess.run(['ps','-p',str(pid),'-o','lstart=','-o','command='],capture_output=True,text=True).stdout.strip()
def running():
 if not STATE.exists():return None
 r=json.loads(STATE.read_text());return r if r.get('identity') and identity(r['pid'])==r['identity'] else None
r=running()
if 'stop' in sys.argv:
 if r:os.kill(r['pid'],signal.SIGTERM)
 print('MVP 停止请求已发送；数据保留。')
else:
 if not r:
  with (DATA/'server.log').open('a') as log:
   p=subprocess.Popen([sys.executable,str(ROOT/'server.py')],cwd=ROOT,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
  time.sleep(.3);STATE.write_text(json.dumps({'pid':p.pid,'identity':identity(p.pid)}))
 for _ in range(20):
  if not running():raise SystemExit('启动失败，请查看 data/server.log；请检查端口 3083 是否占用。')
  try:
   with urlopen('http://127.0.0.1:3083/api/state',timeout=1) as response:
    if response.status==200:break
  except OSError:time.sleep(.3)
 else:raise SystemExit('启动超时，请查看 data/server.log。')
 print('MVP 已启动：http://127.0.0.1:3083/')
 if '--no-browser' not in sys.argv:webbrowser.open('http://127.0.0.1:3083/')
