"""Regenerate all public demo artifacts from real engine and fixture execution."""
import json
from datetime import datetime, timezone
from pathlib import Path
import platform
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from legacylens.engine import analyze, search, impact, investigate
from legacylens.repair import fixture_files, proposal, execute_approved

root=Path(__file__).resolve().parents[1]
project=analyze(fixture_files(),'Northstar · Billing Service')
cases=[]
def check(name,fn):
    try:
        passed=bool(fn())
    except Exception:
        passed=False
    cases.append({'id':f'LL-{len(cases)+1:03}','name':name,'passed':passed})

check('Schema incident retrieves migration runbook first',lambda:search(project,'display_name full_name migration')[0]['path']=='RUNBOOK.md')
check('Invoice query retrieves consumer source in top 3',lambda:'invoices.py' in [c['path'] for c in search(project,'create_invoice customer subtotal',3)])
check('Unknown terminology returns no evidence',lambda:not search(project,'zxqvnonexistent'))
check('Unsupported diagnosis abstains',lambda:not investigate(project,'zxqvnonexistent')['citations'])
check('Customer change reaches invoice and API',lambda:{'invoices.py','api.py'}<=set(impact(project,'customers.py')['affected']))
check('Disconnected module has no importers',lambda:not impact(project,'notifications.py')['affected'])
check('Every citation reproduces the exact source window',lambda:all(c['text']=='\n'.join(project['files'][c['path']].splitlines()[c['start']-1:c['end']]) for c in project['chunks']))
for rule,source in [('sql-interpolation','db.execute(f"SELECT {name}")'),('bare-except','try:\n pass\nexcept:\n pass'),('mutable-default','def f(x=[]):\n return x'),('dynamic-exec','eval(x)'),('missing-timeout','requests.get(url)')]:
    check(f'Detects {rule}',lambda rule=rule,source=source:any(f['rule']==rule for f in analyze({'test.py':source})['findings']))
check('Bound SQL parameters avoid SQL interpolation finding',lambda:not analyze({'a.py':'db.execute("SELECT ?", (name,))'})['findings'])
check('Explicit HTTP timeout avoids timeout finding',lambda:not analyze({'a.py':'requests.get(url,timeout=5)'})['findings'])
check('Broken Python reports a parse warning',lambda:len(analyze({'a.py':'def ('})['warnings'])==1)
check('Cyclic dependencies terminate',lambda:impact(analyze({'a.py':'import b','b.py':'import a'}),'a.py')['affected']==['b.py'])
repair=execute_approved(proposal()['id'])
check('Original invoice tests fail',lambda:not repair['before']['passed'])
check('All five patched invoice tests pass',lambda:repair['after']['passed'] and 'Ran 5 tests' in repair['after']['output'])
check('Bundled source remains unchanged after repair',lambda:'customer["full_name"]' in fixture_files()['invoices.py'])
now=datetime.now(timezone.utc).isoformat()
repair['recorded_at']=now
report={'generated_at':now,'python':platform.python_version(),'rule_count':5,'cases':cases,
        'scope':'Deterministic engine regression checks and trusted-fixture repair. Not an LLM accuracy benchmark.',
        'source_fingerprint':project['fingerprint']}
for filename,value in [('demo.json',project),('proposal.json',proposal()),('repair.json',repair),('evaluations.json',report)]:
    (root/'web'/filename).write_text(json.dumps(value,indent=2)+'\n')
print(f"{sum(c['passed'] for c in cases)}/{len(cases)} evaluation checks passed. Assets generated in web/.")
if not all(c['passed'] for c in cases):
    sys.exit(1)
