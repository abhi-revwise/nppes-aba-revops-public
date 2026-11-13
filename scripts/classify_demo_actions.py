#!/usr/bin/env python3
"""Public-safe action classification over fictional research output."""
import csv,json,sys
from collections import Counter
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'pipeline'))
from decision_layer import classify
def main():
    root=ROOT/'outputs/public_demo';reported={}
    for phase in ('week1','week2','week2_repeat'):
        with (root/phase/'prospect_queue.csv').open(newline='') as f: rows=list(csv.DictReader(f))
        out=[]
        for row in rows:
            d=classify(row['Entity Type'],row['ABA Taxonomies'],row['CRM Candidate IDs'],
                       row['Match Rationale'],row['Phone'],row['Practice Address'],new_this_run=row['New This Run']=='YES')
            out.append({'synthetic_npi':row['NPI'],**d})
        with (root/phase/'sanitized_crm_actions.csv').open('w',newline='') as f:
            w=csv.DictWriter(f,fieldnames=['synthetic_npi',*list(d)]);w.writeheader();w.writerows(out)
        counts=Counter(r['crm_action'] for r in out)
        assert sum(counts.values())==len(rows)
        assert all(not (r['provider_type'].startswith('Solo') and r['synthetic_npi'] in ('0000000003','0000000004','0000000009')) for r in out)
        reported[phase]=dict(counts)
    (root/'synthetic_action_summary.json').write_text(json.dumps({'data_label':'SYNTHETIC ONLY','crm_actions_by_phase':reported},indent=2))
    print(json.dumps(reported,indent=2))
if __name__=='__main__':main()
