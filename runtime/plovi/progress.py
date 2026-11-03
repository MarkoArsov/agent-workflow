"""Bounded, redacted progress events; worker heartbeat is not provider activity."""
from contextvars import ContextVar
from datetime import datetime, timezone
from pathlib import Path
import json
import threading
import time
from .util import read_json, write_json, redact

active = ContextVar('plovi_reporter', default=None)
MAX_BYTES = 1_000_000
FIELDS = {'task','stage','status','completed','provider','model','attempt','repair_round','check','passed','reason','kind'}


def clean(value):
    if isinstance(value,str):
        return ''.join(c for c in redact(value) if c in '\n\t' or ord(c)>=32)[:1000]
    if isinstance(value,list): return [clean(x) for x in value[:100]]
    if value is None or type(value) in (bool,int,float): return value
    return None


class Reporter:
    def __init__(self, root, run_id):
        self.root=Path(root); self.root.mkdir(parents=True,exist_ok=True)
        self.run_id=run_id; self.started=time.time(); self.mutex=threading.RLock()
        self.live={'schema_version':1,'run_id':run_id,'started_at':self.started}
        self.last_pulse=0; self.last_write=0

    def emit(self, event, **fields):
        from .state import lock
        with self.mutex, lock(self.root/'events.lock',wait=True):
            current=read_json(self.root/'live.json',{})
            seq=current.get('sequence',0)
            log=self.root/'events.jsonl'
            # A crash may have appended an event before replacing the summary.
            if log.exists():
                with log.open('rb') as stream:
                    stream.seek(max(0,log.stat().st_size-MAX_BYTES)); tail=stream.read(MAX_BYTES)
                for line in reversed(tail.splitlines()):
                    try:
                        seq=max(seq,json.loads(line).get('sequence',0)); break
                    except (ValueError,TypeError,AttributeError): pass
            if 'stage' in fields and fields['stage']!=self.live.get('stage'):
                for key in ('check','passed','provider','model'):self.live.pop(key,None)
            if event=='check_started':self.live.pop('passed',None)
            fields={k:clean(v) for k,v in fields.items() if k in FIELDS}
            self.live.update(fields)
            record={'type':'event','schema_version':1,'run_id':self.run_id,'sequence':seq+1,
                    'timestamp':datetime.now(timezone.utc).isoformat(),'event':event,**fields}
            if log.exists() and log.stat().st_size>=MAX_BYTES:
                log.replace(self.root/'events.previous.jsonl')
            # Discard only a crash-truncated trailing record before appending.
            if log.exists() and log.stat().st_size:
                with log.open('rb+') as stream:
                    stream.seek(-1,2)
                    if stream.read(1)!=b'\n':
                        stream.seek(max(0,log.stat().st_size-MAX_BYTES)); data=stream.read(MAX_BYTES)
                        end=data.rfind(b'\n'); stream.truncate(log.stat().st_size-len(data)+end+1)
            with log.open('a',encoding='utf-8') as stream: stream.write(json.dumps(record,ensure_ascii=False)+'\n')
            self.live.update(sequence=seq+1,heartbeat_at=time.time())
            write_json(self.root/'live.json',self.live)
            self.last_write=time.time()
            return dict(self.live)

    def activity(self, kind):
        with self.mutex:
            self.live.update(activity=kind,activity_at=time.time())
            if kind=='tool-start':self.live.update(tool_active=True,tool_started_at=time.time())
            elif kind=='tool-end':self.live['tool_active']=False
            if kind in {'tool-start','tool-end'}: self.emit(kind)
            elif time.time()-self.last_write>=1:
                write_json(self.root/'live.json',self.live);self.last_write=time.time()

    def pulse(self, *, force=False):
        with self.mutex:
            if force or time.time()-self.last_pulse>=15:
                self.last_pulse=time.time()
                return self.emit('heartbeat')
            return dict(self.live)


def read_events(root,cursor=0):
    from .state import lock
    with lock(Path(root)/'events.lock',wait=True):
        path=Path(root)/'events.jsonl'
        if not path.exists(): return [], {'offset':0, 'file_id':None, 'sequence':0}
        stat=path.stat(); file_id=[stat.st_dev,stat.st_ino]
        previous=cursor if isinstance(cursor,dict) else {'offset':cursor,'sequence':0}
        offset=previous.get('offset',0); sequence=previous.get('sequence',0)
        if previous.get('file_id',file_id)!=file_id or offset<0 or offset>stat.st_size:offset=0
        with path.open('rb') as stream:
            stream.seek(offset); data=stream.read(MAX_BYTES)
        end=data.rfind(b'\n')
        result={'offset':offset,'file_id':file_id,'sequence':sequence}
        if end<0:return [],result
        rows=[]
        for line in data[:end+1].splitlines():
            try:value=json.loads(line)
            except ValueError:continue
            if isinstance(value,dict) and value.get('schema_version')==1 and type(value.get('sequence')) is int and value['sequence']>sequence:
                rows.append(value);sequence=value['sequence']
        result.update(offset=offset+end+1,sequence=sequence)
        return rows,result


def next_command(state):
    """The exact command that continues a stopped task, or None while it runs or after it completes."""
    task = state.get('task', 'TASK'); status = state.get('status')
    if state.get('next_command'):
        return state['next_command']
    if status == 'needs_input':
        return f'plovi answer {task} --file ANSWER'
    if status == 'needs_approval':
        pending = next(iter(state.get('pending_approvals') or []), None) or state.get('approval') or {}
        flag = '--size' if pending.get('kind') == 'size' else '--paths'
        return f"plovi approve {task} {flag} --approve {pending.get('fingerprint', 'FINGERPRINT')}"
    if status == 'escalated':
        return f'plovi retry {task} --note DECISION'
    if status in {'failed', 'interrupted', 'cancelled', 'paused'}:
        return f'plovi resume {task}'
    return None


def summary(state):
    keys=('task','run_id','status','stage','completed','pending_input','escalation','pending_approvals','error','activity','activity_at','heartbeat_at','started_at','provider','model','repair_round','tool_active','tool_started_at','check','passed','updated_at')
    value={'type':'summary','schema_version':1,**{k:state[k] for k in keys if state.get(k) is not None}}
    task=state.get('task','TASK'); status=state.get('status')
    if status=='needs_input':value['next_action']='plovi answer '+task+' --file ANSWER'
    elif status=='needs_approval':value['next_action']='Inspect pending_approvals and approve each current diff gate'
    elif status=='escalated':value['next_action']='Inspect retained evidence, then plovi retry '+task+' --note DECISION'
    elif status in {'failed','interrupted','cancelled'}:value['next_action']='Inspect retained evidence, then plovi resume '+task
    elif status=='paused' and state.get('pause_reason')=='usage_limit':
        value['pause_reason']='usage_limit'
        if state.get('resets_at') is not None:value['resets_at']=state['resets_at']
        value['next_action']='Wait for the provider usage limit to reset, then plovi resume '+task
    elif status=='paused':value['next_action']='plovi resume '+task
    command=next_command(state)
    if command:value['next']=command
    return value


def human(value):
    status=value.get('status','unknown'); stage=value.get('stage') or 'preparing'
    now=time.time(); elapsed=max(0,int(now-value.get('started_at',now)))
    text=f"{value.get('task','task')}: {status} | {stage} | {elapsed}s elapsed"
    if value.get('provider'):text+=f" | {value['provider']} {value.get('model','')}"
    if value.get('activity_at') is not None:
        text+=f" | {value.get('activity','activity')} {max(0,int(now-value['activity_at']))}s ago"
    if value.get('tool_active'):text+=f" | tool running {max(0,int(now-value.get('tool_started_at',now)))}s"
    if value.get('check'):text+=' | check '+str(value['check'])+(' passed' if value.get('passed') is True else '')
    reason=(value.get('escalation') or {}).get('reason') or value.get('error')
    if reason:text+='\n'+clean(str(reason))
    if value.get('pending_input'):text+='\n'+clean(str(value['pending_input'].get('question','')))
    if value.get('next_action'):text+='\nNext: '+value['next_action']
    return text


def event_text(value):
    text=f"{value.get('task', 'task')}: {str(value.get('event', 'event')).replace('_', ' ')}"
    if value.get('stage'):text+=' | '+str(value['stage'])
    if value.get('check'):text+=' | '+str(value['check'])
    if value.get('passed') is not None:text+=' | '+('passed' if value['passed'] else 'needs correction')
    if value.get('reason'):text+=' | '+clean(str(value['reason']))
    return text
