#!/usr/bin/env python3
"""Local-first Divyasree WOW voice agent demo; stdlib only."""
import json, os, re, sqlite3, urllib.parse, urllib.request, uuid
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
DB=ROOT/'data'/'voice_agent.db'
DB.parent.mkdir(exist_ok=True)
# Load local development configuration without requiring python-dotenv.
env_file=ROOT/'.env'
if env_file.exists():
 for line in env_file.read_text().splitlines():
  line=line.strip()
  if line and not line.startswith('#') and '=' in line:
   k,v=line.split('=',1); os.environ.setdefault(k.strip(),v.strip().strip('"\''))
PROMPT=(ROOT/'docs'/'system-prompt.md').read_text() if (ROOT/'docs'/'system-prompt.md').exists() else ''

def connect():
 c=sqlite3.connect(DB); c.row_factory=sqlite3.Row; return c

def init_db():
 with connect() as c:
  c.executescript('''CREATE TABLE IF NOT EXISTS leads(id TEXT PRIMARY KEY,name TEXT NOT NULL,phone TEXT DEFAULT '',email TEXT DEFAULT '',language TEXT DEFAULT 'English',intent TEXT DEFAULT '',location_fit TEXT DEFAULT '',budget TEXT DEFAULT '',timeline TEXT DEFAULT '',follow_up INTEGER DEFAULT 0,do_not_call INTEGER DEFAULT 0,status TEXT DEFAULT 'new',created_at TEXT NOT NULL,updated_at TEXT NOT NULL);
  CREATE TABLE IF NOT EXISTS calls(id TEXT PRIMARY KEY,lead_id TEXT NOT NULL,mode TEXT NOT NULL,status TEXT NOT NULL,transcript TEXT DEFAULT '[]',summary TEXT DEFAULT '',provider_sid TEXT DEFAULT '',created_at TEXT NOT NULL,ended_at TEXT,FOREIGN KEY(lead_id) REFERENCES leads(id));''')
  cols={r['name'] for r in c.execute('PRAGMA table_info(leads)')}
  if 'do_not_call' not in cols: c.execute('ALTER TABLE leads ADD COLUMN do_not_call INTEGER DEFAULT 0')

def now(): return datetime.now(timezone.utc).isoformat()
def rowdict(r): return dict(r) if r else None

def create_lead(data):
 name=(data.get('name') or 'New prospect').strip()[:100]; ident=str(uuid.uuid4()); t=now()
 with connect() as c: c.execute('INSERT INTO leads(id,name,phone,email,language,created_at,updated_at) VALUES(?,?,?,?,?,?,?)',(ident,name,data.get('phone','')[:30],data.get('email','')[:150],data.get('language','English'),t,t))
 return ident

def classify(text, lang):
 s=text.lower()
 out={}
 if any(k in s for k in ['investment','invest','rental','returns','roi','निवेश']): out['intent']='Investment'
 elif any(k in s for k in ['self','live','family','weekend home','retirement','खुद','परिवार']): out['intent']='Self-use'
 if any(k in s for k in ['nandi','devanahalli','north bengaluru','nearby','comfortable with the location','नंदी','देवनहल्ली']): out['location_fit']='Yes'
 if any(k in s for k in ['too far','far away','not interested in location','location is a concern','दूर है']): out['location_fit']='No'
 amounts=re.findall(r'(?:₹|rs\.?\s*|inr\s*)?([0-9]+(?:\.[0-9]+)?)\s*(crore|cr|lakh|lac|लाख|करोड़)?',s)
 for n,u in amounts:
  val=float(n); unit=u.lower()
  if unit in ('crore','cr','करोड़'): val*=100
  if unit in ('lakh','lac','लाख','') and val>1000: val/=100000
  if unit or val>=50: out['budget']='Fit' if val>=92.4 else 'Below range'; break
 if any(k in s for k in ['92.4','1 crore','one crore','budget is fine','within budget','afford','बजट']): out.setdefault('budget','Fit')
 if any(k in s for k in ['2029','timeline is fine','december','okay with waiting','works for me','ठीक है']): out['timeline']='Comfortable'
 if any(k in s for k in ['too long','too late','need it now','not comfortable waiting','बहुत देर']): out['timeline']='Concern'
 if any(k in s for k in ['call me','follow up','property expert','site visit','schedule','yes please','ज़रूर','कॉल']): out['follow_up']=True
 if any(k in s for k in ['stop calling','do not call','don’t call','dont call','not interested','remove me','angry','irritated','बात नहीं']): out['dnc']=True
 if any(k in s for k in ['no time','busy','not a good time','call later']): out['busy']=True
 if any(k in s for k in ['hindi','हिंदी','नमस्ते','जी']): out['language']='Hindi'
 return out

def next_question(lead):
 missing=[]
 for key,label,q in [('intent','intent','Are you considering this for self-use or as an investment?'),('location_fit','location_fit','How do you feel about the Nandi Hills and Devanahalli corridor in North Bengaluru?'),('budget','budget','Plots start at ₹92.4 lakh inclusive of taxes. Is that within your comfortable budget range?'),('timeline','timeline','Possession is planned for December 2029 as part of phased development. Does that timeline work for you?')]:
  if not lead.get(key): return q
 return None

def generate_reply(lead, user_text, mode='demo'):
 facts=classify(user_text,lead.get('language','English'))
 if facts.get('dnc'):
  lead['do_not_call']=True
  return 'Understood. I am sorry for the interruption. I will mark your preference and end the call. Goodbye.'
 if facts.get('busy'): return 'Of course. I can let you go. Would you prefer a call at another time, or shall I close this enquiry?'
 if facts.get('language'): lead['language']=facts['language']
 for k,v in facts.items():
  if k in ('intent','location_fit','budget','timeline','follow_up'): lead[k]=v
 if lead.get('language')=='Hindi':
  # Hindi path preserves clear, short interactions; the English facts remain in the dashboard.
  if not lead.get('intent'): return 'समझ गई। क्या आप इसे अपने उपयोग के लिए देख रहे हैं या निवेश के लिए?'
  if not lead.get('location_fit'): return 'नंदी हिल्स और देवनहल्ली कॉरिडोर का स्थान आपके लिए कैसा रहेगा?'
  if not lead.get('budget'): return 'प्लॉट की शुरुआती कीमत ₹92.4 लाख है। क्या यह बजट आपके लिए ठीक है?'
  if not lead.get('timeline'): return 'कब्ज़ा दिसंबर 2029 के लिए प्रस्तावित है। क्या यह समय आपके लिए ठीक है?'
  if not lead.get('follow_up'): return 'यहाँ 74% खुली जगह, 20,000 वर्ग फुट क्लब हाउस, इको पार्क और पहाड़ियों के दृश्य हैं। क्या प्रॉपर्टी एक्सपर्ट से बात करना चाहेंगे?'
  return 'धन्यवाद। हमारी प्रॉपर्टी टीम आपसे संपर्क करेगी। आपका दिन शुभ हो।'
 if not lead.get('intent'): return 'Understood. Are you exploring this for your own use, perhaps a weekend home, or mainly as an investment?'
 if not lead.get('location_fit'): return 'Perfect. The project is in Nandi Valley near Nandi Hills, along the Devanahalli corridor in North Bengaluru. How does that location work for you?'
 if not lead.get('budget'): return 'The plots range from 1,200 to 3,199 square feet and start at ₹92.4 lakh inclusive of taxes. Is that in your comfortable range?'
 if not lead.get('timeline'): return 'The project is planned for phased delivery, with possession in December 2029. Would that timeline suit your plans?'
 pitch='Whispers of the Wind is designed as a Private Valley, with 74% open spaces, a 20,000 square foot clubhouse, eco-parks, scenic hill views and a considered community setting.'
 if lead.get('location_fit')=='No': pitch='I understand the corridor may not suit you. The project does offer a quieter Private Valley setting, with 74% open spaces, a 20,000 square foot clubhouse and scenic hill views, but location fit matters most.'
 if not lead.get('follow_up'): return f'{pitch} Based on what you shared, would you like a property expert to call you and discuss plot options or arrange a site visit?'
 return 'Thank you. I will note your interest and have a Divyasree property expert follow up. Is there anything specific you would like them to cover?'

def call_openai(lead,history,user_text):
 key=os.getenv('OPENAI_API_KEY')
 if not key: return None
 try:
  body={'model':os.getenv('OPENAI_MODEL','gpt-4o-mini'),'messages':[{'role':'system','content':PROMPT+'\nConversation facts (JSON): '+json.dumps(lead,ensure_ascii=False)+'\nRespond in the lead language, one concise spoken turn, honoring already captured facts.'}]+history+[{'role':'user','content':user_text}], 'temperature':0.4}
  req=urllib.request.Request('https://api.openai.com/v1/chat/completions',data=json.dumps(body).encode(),headers={'Authorization':'Bearer '+key,'Content-Type':'application/json'})
  with urllib.request.urlopen(req,timeout=15) as res: return json.load(res)['choices'][0]['message']['content']
 except Exception: return None

def add_turn(call_id,role,text):
 with connect() as c:
  r=c.execute('SELECT transcript FROM calls WHERE id=?',(call_id,)).fetchone()
  if not r: return []
  arr=json.loads(r['transcript'] or '[]'); arr.append({'role':role,'text':text,'at':now()})
  c.execute('UPDATE calls SET transcript=? WHERE id=?',(json.dumps(arr,ensure_ascii=False),call_id)); return arr

def twiml(s):
 safe=(s.replace('&','&amp;').replace('<','&lt;').replace('>','&gt;'))
 return '<?xml version="1.0" encoding="UTF-8"?><Response><Gather input="speech" action="/twilio/turn" method="POST" speechTimeout="auto" language="en-IN"><Say language="en-IN">'+safe+'</Say></Gather><Say language="en-IN">I did not hear a response. Thank you for your time. Goodbye.</Say><Hangup/></Response>'

class Handler(BaseHTTPRequestHandler):
 def log_message(self,*args): pass
 def send(self,code,obj,typ='application/json; charset=utf-8'):
  b=obj if isinstance(obj,bytes) else (json.dumps(obj,ensure_ascii=False).encode() if typ.startswith('application/json') else str(obj).encode())
  self.send_response(code); self.send_header('Content-Type',typ); self.send_header('Content-Length',str(len(b))); self.end_headers(); self.wfile.write(b)
 def body(self):
  n=int(self.headers.get('Content-Length','0')); raw=self.rfile.read(n)
  if self.headers.get('Content-Type','').startswith('application/x-www-form-urlencoded'): return urllib.parse.parse_qs(raw.decode())
  return json.loads(raw or b'{}')
 def do_GET(self):
  path=urllib.parse.urlparse(self.path).path
  if path=='/twilio/start':
   call_id=urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query).get('call',[''])[0]
   with connect() as c: call=c.execute('SELECT * FROM calls WHERE id=?',(call_id,)).fetchone()
   if not call: return self.send(404,twiml('Thank you for your time.'),'text/xml; charset=utf-8')
   return self.send(200,twiml('Hello, this is a Divyasree property consultant calling about Whispers of the Wind in Nandi Valley, near Nandi Hills. Is now a convenient time for a brief conversation?'),'text/xml; charset=utf-8')
  if path=='/': return self.send(200,(ROOT/'frontend'/'index.html').read_bytes(),'text/html; charset=utf-8')
  if path.startswith('/assets/'): return self.send(200,(ROOT/'frontend'/path.split('/')[-1]).read_bytes(),'text/css; charset=utf-8' if path.endswith('.css') else 'application/javascript; charset=utf-8')
  if path=='/api/leads':
   with connect() as c: return self.send(200,[rowdict(x) for x in c.execute('SELECT * FROM leads ORDER BY updated_at DESC')])
  if path=='/api/calls':
   with connect() as c: return self.send(200,[rowdict(x) for x in c.execute('SELECT * FROM calls ORDER BY created_at DESC')])
  if path.startswith('/api/calls/'):
   with connect() as c: r=c.execute('SELECT * FROM calls WHERE id=?',(path.rsplit('/',1)[-1],)).fetchone()
   return self.send(200,rowdict(r) or {})
  if path=='/api/config': return self.send(200,{'call_mode':os.getenv('CALL_MODE','demo').lower(),'ai_enabled':bool(os.getenv('OPENAI_API_KEY'))})
  return self.send(404,{'error':'Not found'})
 def do_POST(self):
  path=urllib.parse.urlparse(self.path).path
  try: data=self.body()
  except Exception: data={}
  if path=='/api/leads':
   ident=create_lead(data); return self.send(201,{'id':ident})
  if path=='/api/calls':
   with connect() as c: lead=c.execute('SELECT * FROM leads WHERE id=?',(data.get('lead_id'),)).fetchone()
   if not lead: return self.send(404,{'error':'Lead not found'})
   mode=os.getenv('CALL_MODE','demo').lower(); ident=str(uuid.uuid4()); t=now(); status='simulated'
   with connect() as c: c.execute('INSERT INTO calls(id,lead_id,mode,status,created_at) VALUES(?,?,?,?,?)',(ident,lead['id'],mode,status,t))
   greeting='Hello, this is a Divyasree property consultant calling about Whispers of the Wind in Nandi Valley, near Nandi Hills. Is now a convenient time for a brief conversation?'
   add_turn(ident,'agent',greeting)
   if mode=='twilio':
    sid,err=self.start_twilio(ident,lead['phone'])
    if err: return self.send(400,{'error':err})
    with connect() as c: c.execute("UPDATE calls SET status='calling',provider_sid=? WHERE id=?",(sid,ident))
   return self.send(201,{'id':ident,'mode':mode,'status':status,'message':greeting})
  if path.startswith('/api/calls/') and path.endswith('/turn'):
   cid=path.split('/')[-2]; utter=(data.get('text') or '').strip()
   with connect() as c:
    call=c.execute('SELECT * FROM calls WHERE id=?',(cid,)).fetchone()
    leadrow=c.execute('SELECT * FROM leads WHERE id=?',(call['lead_id'],)).fetchone() if call else None
   if not call or not leadrow: return self.send(404,{'error':'Call not found'})
   lead=rowdict(leadrow); add_turn(cid,'user',utter)
   response=generate_reply(lead,utter)
   if not lead.get('do_not_call') and not classify(utter,lead.get('language','English')).get('busy'):
    response=call_openai(lead,[],utter) or response
   hist=[]
   with connect() as c:
    status='opted_out' if lead.get('do_not_call') else ('qualified' if lead.get('location_fit')=='Yes' and lead.get('budget')=='Fit' and lead.get('timeline')=='Comfortable' and lead.get('intent') else ('nurture' if any(lead.get(k) in ('No','Below range','Concern') for k in ('location_fit','budget','timeline')) else 'in_progress'))
    c.execute('UPDATE leads SET intent=?,location_fit=?,budget=?,timeline=?,follow_up=?,do_not_call=?,language=?,status=?,updated_at=? WHERE id=?',(lead.get('intent',''),lead.get('location_fit',''),lead.get('budget',''),lead.get('timeline',''),int(bool(lead.get('follow_up'))),int(bool(lead.get('do_not_call'))),lead.get('language','English'),status,now(),lead['id']))
   add_turn(cid,'agent',response)
   with connect() as c:
    r=c.execute('SELECT transcript FROM calls WHERE id=?',(cid,)).fetchone(); arr=json.loads(r['transcript'])
    c.execute('UPDATE calls SET transcript=?,summary=?,status=?,ended_at=? WHERE id=?',(json.dumps(arr,ensure_ascii=False),response,'ended' if lead.get('do_not_call') else call['status'],now() if lead.get('do_not_call') else call['ended_at'],cid))
   return self.send(200,{'reply':response,'lead':lead,'transcript':arr})
  if path=='/twilio/turn':
   form=data; cid=form.get('CallSid',[''])[0]; speech=form.get('SpeechResult',[''])[0]
   with connect() as c: call=c.execute('SELECT * FROM calls WHERE provider_sid=?',(cid,)).fetchone()
   if not call: return self.send(404,'<Response><Hangup/></Response>','text/xml')
   add_turn(call['id'],'user',speech)
   with connect() as c: lead=rowdict(c.execute('SELECT * FROM leads WHERE id=?',(call['lead_id'],)).fetchone())
   reply=generate_reply(lead,speech)
   if not lead.get('do_not_call') and not classify(speech,lead.get('language','English')).get('busy'):
    reply=call_openai(lead,[],speech) or reply
   with connect() as c:
    status='opted_out' if lead.get('do_not_call') else ('qualified' if lead.get('location_fit')=='Yes' and lead.get('budget')=='Fit' and lead.get('timeline')=='Comfortable' and lead.get('intent') else ('nurture' if any(lead.get(k) in ('No','Below range','Concern') for k in ('location_fit','budget','timeline')) else 'in_progress'))
    c.execute('UPDATE leads SET intent=?,location_fit=?,budget=?,timeline=?,follow_up=?,do_not_call=?,status=?,updated_at=? WHERE id=?',(lead.get('intent',''),lead.get('location_fit',''),lead.get('budget',''),lead.get('timeline',''),int(bool(lead.get('follow_up'))),int(bool(lead.get('do_not_call'))),status,now(),lead['id']))
   add_turn(call['id'],'agent',reply)
   if lead.get('do_not_call'):
    with connect() as c: c.execute("UPDATE calls SET status='ended',ended_at=?,summary=? WHERE id=?",(now(),reply,call['id']))
    return self.send(200,'<?xml version="1.0" encoding="UTF-8"?><Response><Say language="en-IN">Understood. I will respect your preference. Goodbye.</Say><Hangup/></Response>','text/xml; charset=utf-8')
   return self.send(200,twiml(reply),'text/xml; charset=utf-8')
  if path=='/api/calls/outbound':
   return self.send(400,{'error':'Create calls from a lead in the dashboard.'})
  return self.send(404,{'error':'Not found'})
 def start_twilio(self,call_id,to):
  sid=os.getenv('TWILIO_ACCOUNT_SID'); token=os.getenv('TWILIO_AUTH_TOKEN'); src=os.getenv('TWILIO_FROM_NUMBER'); base=os.getenv('BASE_URL')
  if not all([sid,token,src,base,to]): return None,'Twilio needs credentials, caller ID, BASE_URL, and a lead phone number.'
  try:
   from base64 import b64encode
   url=f'https://api.twilio.com/2010-04-01/Accounts/{sid}/Calls.json'
   params=urllib.parse.urlencode({'To':to,'From':src,'Url':base.rstrip('/')+'/twilio/start?call='+call_id}).encode()
   req=urllib.request.Request(url,data=params,headers={'Authorization':'Basic '+b64encode(f'{sid}:{token}'.encode()).decode()})
   with urllib.request.urlopen(req,timeout=15) as resp: return json.load(resp)['sid'],None
  except Exception as e: return None,'Twilio request failed: '+str(e)
 def do_GET_twilio(self): pass
 def do_PUT(self): pass

def main():
 init_db()
 print('Divyasree WOW demo running at http://localhost:8000')
 ThreadingHTTPServer(('127.0.0.1',8000),Handler).serve_forever()
if __name__=='__main__': main()
