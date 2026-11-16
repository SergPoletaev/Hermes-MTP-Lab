"""Deterministic, conservative quality and parity checks for fixed benchmark prompts.

Never calls a cloud LLM. Never executes untrusted model code on the host.  Code
unit tests run only when an *already installed* local Docker Linux image exists;
otherwise their result is explicitly unverified. Heuristics are not grades.
"""
from __future__ import annotations
import ast
import difflib
import hashlib
import json
import re
import shutil
import subprocess

CODE_IMAGE = 'python:3.13-alpine'
MAX_ANSWER = 120_000


def sha(text):
    return hashlib.sha256(text.encode('utf-8')).hexdigest()


def normalize_response(value):
    if isinstance(value,str):return value
    if isinstance(value,list):
        return '\n'.join(str(part.get('text','')) for part in value if isinstance(part,dict) and part.get('type')=='text')
    return ''


def extract_code(answer):
    fenced=re.findall(r'```(?:python|py)?\s*\n(.*?)```',answer,re.I|re.S)
    return (fenced[0] if fenced else answer).strip()


def structured_data(text):
    """Take the *last* matching JSON object, not illustrative intermediate objects."""
    decoder=json.JSONDecoder()
    choices=[]
    for m in re.finditer(r'\{',text[:MAX_ANSWER]):
        try:
            data,_=decoder.raw_decode(text[m.start():])
            if isinstance(data,dict) and all(k in data for k in ('red','blue','green','total')):
                choices.append(data)
        except (ValueError,TypeError):pass
    return choices[-1] if choices else None


# Only the isolated container sees generated source code. Host controls image,
# executable, test suite and resource flags; model output is sent via stdin.
CODE_HARNESS = r'''
import sys,json,datetime,traceback
try:
    payload=sys.stdin.read()
    if len(payload)>100000:
        print(json.dumps({'error':'payload_too_large'}));sys.exit(0)
    obj=json.loads(payload)
    namespace={}
    exec(compile(obj['code'],'<generated-merge>','exec'),namespace)
    fn=namespace['merge_intervals']
    dt=datetime.datetime;utc=datetime.timezone.utc
    def d(day,hour=0,tz=utc):return dt(2026,1,day,hour,tzinfo=tz)
    checks=[
      ('disjoint',[(d(1),d(2)),(d(4),d(5))],[(d(1),d(2)),(d(4),d(5))]),
      ('overlap',[(d(1),d(3)),(d(2),d(4))],[(d(1),d(4))]),
      ('touching',[(d(1),d(2)),(d(2),d(3))],[(d(1),d(3))]),
      ('empty_list',[],[]),
      ('timezone',[(d(1),d(2)),(d(2,1,datetime.timezone(datetime.timedelta(hours=2))),d(3))],[(d(1),d(3))]),
    ]
    results={}
    def canonical(x):
        return [(a.astimezone(utc),b.astimezone(utc)) for a,b in x]
    for name,inp,expected in checks:
        try:results[name]=canonical(fn(inp))==expected
        except Exception:results[name]=False
    for name,inp in [('inverted',[(d(3),d(1))]),('naive',[(dt(2026,1,1),dt(2026,1,2))])]:
        try:fn(inp);results[name]=False
        except (ValueError,TypeError):results[name]=True
        except Exception:results[name]=False
    print(json.dumps({'tests':results}))
except Exception as exc:
    print(json.dumps({'error':str(exc)[:500]}))
'''


def docker_ready():
    binary=shutil.which('docker')
    if not binary:return False,'docker_unavailable'
    try:
        p=subprocess.run([binary,'image','inspect',CODE_IMAGE],capture_output=True,timeout=5)
    except (OSError,subprocess.TimeoutExpired):return False,'docker_unavailable'
    if p.returncode:return False,'sandbox_image_not_cached'
    return True,'ready'


def check_code(text,*,sandbox=None):
    source=extract_code(text)
    if len(source)>20000:return {'status':'unverified','method':'sandbox','reason':'code_too_large'}
    try:
        tree=ast.parse(source)
    except SyntaxError as e:
        return {'status':'fail','method':'static_syntax','reason':f'syntax_error_line_{e.lineno}'}
    if 'merge_intervals' not in {n.name for n in tree.body if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef))}:
        return {'status':'fail','method':'static_syntax','reason':'required_function_missing'}
    ready,reason=(sandbox if sandbox is not None else docker_ready())
    if not ready:return {'status':'unverified','method':'sandbox','reason':reason,'syntax':'pass'}
    cmd=[shutil.which('docker') or 'docker','run','--rm','-i','--network','none',
         '--read-only','--cap-drop','ALL','--security-opt','no-new-privileges',
         '--pids-limit','32','--memory','256m','--cpus','1','--user','65534:65534',
         '--tmpfs','/tmp:rw,noexec,nosuid,size=16m',CODE_IMAGE,
         'python','-I','-S','-c',CODE_HARNESS]
    try:
        p=subprocess.run(cmd,input=json.dumps({'code':source}),text=True,
                         capture_output=True,timeout=15)
        if p.returncode:return {'status':'unverified','method':'sandbox','reason':'sandbox_launch_failed','exit_code':p.returncode}
        value=json.loads(p.stdout.strip()[-10000:])
    except subprocess.TimeoutExpired:
        return {'status':'fail','method':'sandbox','reason':'test_timeout'}
    except (OSError,ValueError,json.JSONDecodeError):
        return {'status':'unverified','method':'sandbox','reason':'sandbox_protocol_error'}
    if 'error' in value:return {'status':'fail','method':'sandbox','reason':'runtime_error','detail':value['error']}
    results=value.get('tests',{})
    return {'status':'pass' if len(results)==7 and all(results.values()) else 'fail',
            'method':'sandbox','tests':results}


def _grounding(text):
    norm=text.casefold()
    # The built-in still image contains TEST 47 on the white tent card and red,
    # green, yellow notebooks from top to bottom. These are fixed, human-audited.
    label=bool(re.search(r'\btest\s*[-:#]?\s*47\b',norm))
    color_order=bool(re.search(r'\bred\b[\s\S]{0,160}\bgreen\b[\s\S]{0,160}\byellow\b',norm))
    return {'status':'pass' if label and color_order else 'fail', 'method':'reference_heuristic',
            'checks':{'printed_label_TEST_47':label,'notebook_order_red_green_yellow':color_order},
            'warning':'Keyword-based reference checks are not a complete visual-quality assessment'}


def grade(task_id,text,reasoning='',finish_reason=None,*,sandbox=None):
    if finish_reason in ('length','max_tokens'):
        return {'status':'incomplete','method':'completion','reason':'token_limit_reached'}
    if not text.strip():
        return {'status':'unverified','method':'completion','reason':'no_visible_response'}
    if task_id=='structured':
        data=structured_data(text)
        if data is None:return {'status':'fail','method':'exact_json','reason':'required_json_not_found'}
        expected={'red':380,'blue':203,'green':206,'total':789}
        checks={k:type(data[k]) is int and data[k]==v for k,v in expected.items()}
        return {'status':'pass' if all(checks.values()) else 'fail','method':'exact_json','checks':checks}
    if task_id=='grounding':return _grounding(text)
    if task_id=='code':return check_code(text,sandbox=sandbox)
    # Natural language/scene generation have no automatically verified ground truth.
    return {'status':'manual_review','method':'human_review','reason':'open_ended_task'}


def pair(a,b,kind):
    """Compare *separately* visible and hidden reasoning; do not imply mismatch is a failure."""
    if a is None or b is None:return None
    x=a.get('visible','');y=b.get('visible','')
    rx=a.get('reasoning','');ry=b.get('reasoning','')
    return {'type':kind,'model_id':a['model_id'],'trial':a['trial'],'task':a['task'],
            'left':a['phase']+'#'+str(a['replica']),'right':b['phase']+'#'+str(b['replica']),
            'visible_equal':x==y,'reasoning_equal':rx==ry,
            'visible_similarity':round(difflib.SequenceMatcher(None,x[:6000],y[:6000],autojunk=True).ratio(),4),
            'visible_left_sha256':sha(x),'visible_right_sha256':sha(y),
            'reasoning_left_sha256':sha(rx),'reasoning_right_sha256':sha(ry),
            'quality_left':a.get('quality',{}).get('status'),'quality_right':b.get('quality',{}).get('status'),
            'quality_regression':kind=='OFF/ON' and a.get('quality',{}).get('status')=='pass' and b.get('quality',{}).get('status')=='fail'}


def comparisons(answers):
    groups={}
    for row in answers:
        groups.setdefault((row['trial'],row['task']),{})[(row['phase'],row['replica'])]=row
    result=[]
    for key,slots in sorted(groups.items()):
        for a,b,kind in [(('OFF',1),('OFF',2),'OFF/OFF'),(('ON',1),('ON',2),'ON/ON'),
                         (('OFF',1),('ON',1),'OFF/ON'),(('OFF',2),('ON',2),'OFF/ON')]:
            value=pair(slots.get(a),slots.get(b),kind)
            if value is not None:result.append(value)
    return result


def comparison_summary(items):
    result={}
    for typ in ('OFF/OFF','ON/ON','OFF/ON'):
        subset=[x for x in items if x['type']==typ]
        result[typ]={'pairs':len(subset),'same_visible':sum(x['visible_equal'] for x in subset),
                     'same_reasoning':sum(x['reasoning_equal'] for x in subset),
                     'quality_regressions':sum(x['quality_regression'] for x in subset),
                     'median_visible_similarity':round(__import__('statistics').median(x['visible_similarity'] for x in subset),3) if subset else None}
    return result
