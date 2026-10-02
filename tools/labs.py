"""Four independent teaching models, not upstream runtime or sandbox tests.

Run: python3 tools/labs.py --output verification/labs.json
No imports of analyzed frameworks, network, credentials, or external mutations.
"""
from pathlib import Path
import argparse, json

def tool_ledger(events, scoped=True, preserve_terminal=True):
    ledger={}
    for run,call,status in events:
        key=(run,call) if scoped else call
        if preserve_terminal and ledger.get(key) in {'completed','failed'}:continue
        ledger[key]=status
    return {str(k):v for k,v in ledger.items()}

def action_sequence(observations, stop_on_change=True):
    executed=[]
    for action,before,after in observations:
        executed.append(action)
        if stop_on_change and before!=after:break
    return executed

def projected_path(path,indexes):
    parts=path.replace('\\','/').split('/')
    if parts[0]=='skills':return False
    return all('/'.join(parts[:i])+'/MEMORY.md' in indexes for i in range(1,len(parts)))

def evaluation_counts(samples):
    return dict(planned=len(samples),run=sum(s['run'] for s in samples),
                scored=sum(s['score'] is not None for s in samples),
                correct=sum(s['score'] is True for s in samples))

def run():
    events=[('r1','x','started'),('r2','x','started'),('r1','x','completed'),('r1','x','started')]
    good=tool_ledger(events);bad=tool_ledger(events,False,False)
    assert len(good)==2 and good[str(('r1','x'))]=='completed' and bad=={'x':'started'}
    actions=[('navigate',('url1','focus1'),('url1','focus2')),('click_old_index',('url1','focus2'),('url1','focus2'))]
    safe=action_sequence(actions);stale=action_sequence(actions,False)
    assert safe==['navigate'] and stale==['navigate','click_old_index']
    indexes={'notes/MEMORY.md','notes/a/MEMORY.md'}
    assert projected_path('notes/a/b.md',indexes)
    assert not projected_path('notes/a/b.md',{'notes/MEMORY.md'})
    assert not projected_path('skills/x.md',{'skills/MEMORY.md'})
    samples=[dict(run=True,score=True),dict(run=True,score=False),dict(run=True,score=None),dict(run=True,score=None),dict(run=False,score=None)]
    counts=evaluation_counts(samples)
    assert counts==dict(planned=5,run=4,scored=2,correct=1)
    rows=[dict(id='tool-ledger',input=events,correct=good,wrong=bad,pass_=True),
          dict(id='stale-actions',input=actions,correct=safe,wrong=stale,pass_=True),
          dict(id='memory-projection',input=dict(path='notes/a/b.md',indexes=sorted(indexes)),correct=True,missing_parent_index=False,skills=False,pass_=True),
          dict(id='evaluation-denominator',input=samples,correct=counts,scored_accuracy=.5,wrong_planned_accuracy=.2,pass_=True)]
    return dict(kind='independent-teaching-model',upstreamRuntimeExecuted=False,apiCalls=0,
                status='PASS',groups=4,results=rows)

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path);args=parser.parse_args()
    result=run();text=json.dumps(result,ensure_ascii=False,indent=2)+'\n'
    if args.output:args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(text)
    print(json.dumps({k:v for k,v in result.items() if k!='results'}))
