#!/usr/bin/env python3
"""Demonstrate real filtering, CRM matching and SQLite dedupe with synthetic inputs."""
import json,shutil,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'outputs/public_demo'
if OUT.exists():shutil.rmtree(OUT)
OUT.mkdir(parents=True)
subprocess.run([sys.executable,str(ROOT/'scripts/generate_fixtures.py')],check=True,cwd=ROOT)
inputs=ROOT/'outputs/synthetic_inputs'
base=[sys.executable,str(ROOT/'pipeline/run_weekly.py'),'--crm-dir',str(inputs),'--database',str(OUT/'demo_state.sqlite3')]
steps=[('week1','2026-11-02','2026-11-08',inputs/'NPPES_SYNTHETIC_20261102_20261108_Weekly_V2.zip'),('week2','2026-11-09','2026-11-15',inputs/'NPPES_SYNTHETIC_20261109_20261115_Weekly_V2.zip'),('week2_repeat','2026-11-09','2026-11-15',inputs/'NPPES_SYNTHETIC_20261109_20261115_Weekly_V2.zip')]
summaries=[]
for name,start,end,archive in steps:
    print('=== SYNTHETIC',name,'===',flush=True)
    cmd=base+['--weekly-zip',str(archive),'--weekly-window',start,end,'--output',str(OUT/name)]
    subprocess.run(cmd,check=True,cwd=ROOT)
    summary=json.loads((OUT/name/'run_summary.json').read_text());qa=json.loads((OUT/name/'qa_checks.json').read_text())
    assert qa['all_pass'],name
    summaries.append(summary)
novel=[x['new_prospect_events'] for x in summaries]
assert novel==[4,3,0],f'unexpected synthetic counts: {novel}'
assert summaries[2]['previously_seen_suppressed']==3
result={'data_label':'SYNTHETIC - NOT PASSAGE HEALTH CRM OR ACTUAL NPPES','status':'PASS','new_prospect_events_per_run':novel,'repeat_suppressed':3,'note':'All NPIs, names and phones are fake; these are demo-only counts.'}
(OUT/'demo_validation.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))
subprocess.run([sys.executable,str(ROOT/'scripts/classify_demo_actions.py')],check=True,cwd=ROOT)
