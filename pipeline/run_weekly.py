#!/usr/bin/env python3
"""Demonstrable, stateful NPPES prospecting prototype. No production CRM writes.

Run against one or more ZIP weekly incrementals and/or a clearly flagged reconstructed cohort.
State is SQLite so repeated runs do not create new lead events for previously seen NPIs.
"""
import argparse, hashlib, json, re, sqlite3, zipfile
from datetime import datetime, timezone
from pathlib import Path
import pandas as pd

ABA={'103K00000X':'Behavior Analyst','106E00000X':'Assistant Behavior Analyst','106S00000X':'Behavior Technician'}
SLOTS=[f'Healthcare Provider Taxonomy Code_{i}' for i in range(1,16)]
COL={'line':'Provider First Line Business Practice Location Address','city':'Provider Business Practice Location Address City Name','state':'Provider Business Practice Location Address State Name','zip':'Provider Business Practice Location Address Postal Code','phone':'Provider Business Practice Location Address Telephone Number','org':'Provider Organization Name (Legal Business Name)','first':'Provider First Name','last':'Provider Last Name (Legal Name)'}
FIELDS=['NPI','Entity Type Code','Provider Enumeration Date','Last Update Date','NPI Deactivation Date',*COL.values(),'Matched ABA Taxonomy Codes']

def s(v): return '' if pd.isna(v) else str(v).strip()
def norm(v): return re.sub(r'[^A-Z0-9]','',s(v).upper())
def zip5(v): return re.sub(r'\D','',s(v))[:5]
def sha(path):
 h=hashlib.sha256()
 with open(path,'rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''): h.update(b)
 return h.hexdigest()
def db_open(path):
 path.parent.mkdir(parents=True,exist_ok=True)
 db=sqlite3.connect(path)
 db.execute('PRAGMA journal_mode=WAL')
 db.executescript('''CREATE TABLE IF NOT EXISTS seen_providers(npi TEXT PRIMARY KEY, first_seen_run TEXT NOT NULL, last_seen_run TEXT NOT NULL, first_source TEXT NOT NULL, initial_class TEXT, last_status TEXT, last_fingerprint TEXT); CREATE TABLE IF NOT EXISTS processed_releases(source_hash TEXT PRIMARY KEY, source_name TEXT, provenance TEXT, first_run TEXT); CREATE TABLE IF NOT EXISTS lead_events(npi TEXT PRIMARY KEY, first_run TEXT, classification TEXT, status TEXT, tier TEXT); CREATE TABLE IF NOT EXISTS runs(run_id TEXT PRIMARY KEY, started_utc TEXT, records_read INTEGER, in_window INTEGER, eligible INTEGER, novel INTEGER, resurfaced INTEGER, crm_candidates INTEGER, source_notes TEXT);''')
 return db

def load_sources(paths,prior,prior_window,weekly_window):
 records=[]; totals=[]
 for path in paths:
  path=Path(path)
  with zipfile.ZipFile(path) as z:
   names=[n for n in z.namelist() if Path(n).name.startswith('npidata_pfile_') and n.lower().endswith('.csv') and 'fileheader' not in n.lower()]
   if len(names)!=1: raise ValueError(f'Expected one main npidata_pfile CSV in {path}, found {names}')
   scanned=window=matched=0
   with z.open(names[0]) as f:
    for df in pd.read_csv(f,dtype=str,keep_default_na=False,chunksize=10000,low_memory=False):
     scanned+=len(df); ts=pd.to_datetime(df['Provider Enumeration Date'],format='%m/%d/%Y',errors='coerce')
     w=ts.between(pd.Timestamp(weekly_window[0]),pd.Timestamp(weekly_window[1]))
     window+=int(w.sum());tax=[c for c in SLOTS if c in df.columns]
     m=df[tax].isin(ABA.keys()).any(axis=1) & w
     sub=df.loc[m].copy();matched+=len(sub)
     sub['Matched ABA Taxonomy Codes']=sub[tax].apply(lambda row:';'.join(c for c in row if c in ABA),axis=1)
     records.extend(sub.reindex(columns=FIELDS,fill_value='').to_dict('records'))
   totals.append({'source':path.name,'provenance':'original_weekly_incremental','rows_scanned':scanned,'window_rows':window,'eligible_rows':matched,'source_hash':sha(path)})
 if prior:
  df=pd.read_csv(prior,dtype=str,keep_default_na=False)
  ts=pd.to_datetime(df['Provider Enumeration Date'],format='%m/%d/%Y',errors='coerce')
  w=ts.between(pd.Timestamp(prior_window[0]),pd.Timestamp(prior_window[1]))
  sub=df.loc[w].copy()
  if 'Matched ABA Taxonomy Codes' not in sub: raise ValueError('Prior cohort must include taxonomy evidence')
  sub=sub[sub['Matched ABA Taxonomy Codes'].apply(lambda x:any(t in ABA for t in s(x).split(';')))]
  records.extend(sub.reindex(columns=FIELDS,fill_value='').to_dict('records'))
  totals.append({'source':Path(prior).name,'provenance':'RECONSTRUCTED_LATER_MONTHLY_SNAPSHOT_NOT_WEEKLY','rows_scanned':len(df),'window_rows':int(w.sum()),'eligible_rows':len(sub),'source_hash':sha(prior)})
 return pd.DataFrame(records).drop_duplicates('NPI'),totals

def cmaps(book,crm_dir=None):
 if crm_dir:
  company=pd.read_csv(Path(crm_dir)/'sample_crm_export_companies.csv',dtype=str,keep_default_na=False)
  contact=pd.read_csv(Path(crm_dir)/'sample_crm_export_contacts.csv',dtype=str,keep_default_na=False)
 else:
  company=pd.read_excel(book,sheet_name='sample_crm_export_companies',dtype=str).fillna('')
  contact=pd.read_excel(book,sheet_name='sample_crm_export_contacts',dtype=str).fillna('')
 by_npi={};by_org={};by_address={}
 for r in company.to_dict('records'):
  n=norm(r.get('NPI number'));org=norm(r.get('Company name'))
  addr='|'.join([norm(r.get('HQ Address - Line 1')),norm(r.get('HQ Address - City')),norm(r.get('HQ Address - State/Province Code')),zip5(r.get('HQ Address - Zip Code'))])
  if n: by_npi.setdefault(n,[]).append(r)
  if org: by_org.setdefault(org,[]).append(r)
  if addr.split('|')[0] and addr.split('|')[-1]: by_address.setdefault(addr,[]).append(r)
 return company,contact,by_npi,by_org,by_address

def classify(r):
 entity=s(r.get('Entity Type Code'))
 tax=s(r.get('Matched ABA Taxonomy Codes'))
 if entity=='2':return 'ABA organization','Type 2 organizational NPI; verify active ABA business'
 if entity=='1':return 'Individual — affiliation unverified','Type 1 individual NPI does not establish solo practice or employer'
 return 'Provider type unknown','Entity Type Code missing or unexpected'

def score(r):
 codes=s(r.get('Matched ABA Taxonomy Codes')).split(';')
 components=[]
 if s(r.get('Entity Type Code'))=='2':components.append(('Organization NPI',20))
 if '103K00000X' in codes:components.append(('Behavior Analyst',15))
 if '106E00000X' in codes:components.append(('Assistant Behavior Analyst',8))
 if s(r.get(COL['org'])):components.append(('Organization name present',10))
 if s(r.get(COL['line'])):components.append(('Practice address present',5))
 if s(r.get(COL['phone'])):components.append(('Practice phone present',5))
 if not s(r.get('NPI Deactivation Date')):components.append(('No deactivation date listed',5))
 n=sum(x[1] for x in components)
 return n,('Tier 1' if n>=35 else 'Tier 2' if n>=20 else 'Research'),'; '.join(f'{a} +{b}' for a,b in components)

def process(args):
 result=Path(args.output);result.mkdir(parents=True,exist_ok=True)
 db=db_open(Path(args.database))
 providers,sources=load_sources(args.weekly_zip,args.prior_cohort,args.prior_window,args.weekly_window)
 _,contacts,by_npi,by_org,by_addr=cmaps(args.crm_workbook,args.crm_dir)
 run_id=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
 records=[];matches=[];new=[];resurfaced=0;ambig=0
 # Keep state changes and exports inside a single transaction. Roll back on exceptions.
 with db:
  for _,r in providers.iterrows():
   p=r.to_dict();npi=s(p['NPI']); typ,reason=classify(p)
   org=norm(p.get(COL['org'])) if s(p.get('Entity Type Code'))=='2' else ''
   adr='|'.join([norm(p.get(COL['line'])),norm(p.get(COL['city'])),norm(p.get(COL['state'])),zip5(p.get(COL['zip']))])
   candidates={}
   def register(rows,evidence):
    for comp in rows:
     ident=s(comp.get('Record ID'))
     if ident:
      cur=candidates.setdefault(ident,{'name':s(comp.get('Company name')),'signals':set()})
      cur['signals'].add(evidence)
   register(by_npi.get(norm(npi),[]),'Exact company NPI')
   if org:register(by_org.get(org,[]),'Exact organization name')
   if adr.split('|')[0] and adr.split('|')[-1]:register(by_addr.get(adr,[]),'Exact full practice address')
   primary=[id for id,c in candidates.items() if 'Exact company NPI' in c['signals'] or 'Exact organization name' in c['signals']]
   if primary:status='Already in CRM';rationale='Same NPI or normalized organization name; confirm legal identity before merge'
   elif s(p.get('Entity Type Code'))=='1' and candidates:status='New Contact at Existing Account';rationale='Practice-address candidates only; affiliation NOT verified'
   else:status='Net New Account';rationale='No strong company match; individual independence NOT established'
   if len(candidates)>1:ambig+=1
   # Adjust persona only when a likely known company has address evidence; do NOT assert employer.
   if s(p.get('Entity Type Code'))=='1' and candidates:
    typ='Individual — possible existing-company affiliation';reason='Shared practice address; cannot establish employment'
   points,tier,parts=score(p)
   was=db.execute('SELECT npi FROM seen_providers WHERE npi=?',(npi,)).fetchone() is not None
   fingerprint=hashlib.sha256(json.dumps({'name':s(p.get(COL['org'])),'address':adr,'tax':s(p.get('Matched ABA Taxonomy Codes'))},sort_keys=True).encode()).hexdigest()
   if not was:
    new.append(npi)
    db.execute('INSERT INTO seen_providers VALUES(?,?,?,?,?,?,?)',(npi,run_id,run_id,sources[0]['source'] if sources else '',typ,status,fingerprint))
    db.execute('INSERT INTO lead_events VALUES(?,?,?,?,?)',(npi,run_id,typ,status,tier))
   else:
    resurfaced+=1
    db.execute('UPDATE seen_providers SET last_seen_run=?,last_status=?,last_fingerprint=? WHERE npi=?',(run_id,status,fingerprint,npi))
   for cid,c in candidates.items():matches.append({'NPI':npi,'CRM Company Record ID':cid,'CRM Company Name':c['name'],'Evidence':'; '.join(sorted(c['signals'])),'Review Required':'YES','Provider Type':typ})
   records.append({'NPI':npi,'Provider Name':s(p.get(COL['org'])) or (s(p.get(COL['first']))+' '+s(p.get(COL['last']))).strip(),'Enumeration Date':s(p.get('Provider Enumeration Date')),'Source Cohort': f'{args.weekly_window[0]} to {args.weekly_window[1]}' if pd.to_datetime(p.get('Provider Enumeration Date'),format='%m/%d/%Y')>=pd.Timestamp(args.weekly_window[0]) else 'Earlier reconstructed cohort','Entity Type':s(p.get('Entity Type Code')),'ABA Taxonomies':s(p.get('Matched ABA Taxonomy Codes')),'Provider Persona':typ,'Persona Rationale':reason,'Practice Address':s(p.get(COL['line'])),'City':s(p.get(COL['city'])),'State':s(p.get(COL['state'])),'ZIP5':zip5(p.get(COL['zip'])),'Phone':s(p.get(COL['phone'])),'CRM Match Status':status,'Match Rationale':rationale,'CRM Candidate IDs':'; '.join(candidates),'CRM Candidate Count':len(candidates),'Qualification Score':points,'Tier':tier,'Tier Rationale':parts,'Review Required':'YES' if candidates or typ.startswith('Individual') else 'CHECK BUSINESS FIT','CRM Object':'Company' if s(p.get('Entity Type Code'))=='2' else 'Contact (research only)','Lifecycle Stage':'Lead (proposed; hold)','Lead Source':'NPPES Weekly Registry','Routing':'Existing account owner AFTER verification' if candidates else ('Territory SDR AFTER verification' if s(p.get('Entity Type Code'))=='2' else 'RevOps verification queue'),'New This Run':'YES' if not was else 'NO','CRM Import Allowed':'NO — REVIEW HOLD'})
  for source in sources:db.execute('INSERT OR IGNORE INTO processed_releases VALUES(?,?,?,?)',(source['source_hash'],source['source'],source['provenance'],run_id))
  db.execute('INSERT INTO runs VALUES(?,?,?,?,?,?,?,?,?)',(run_id,datetime.now(timezone.utc).isoformat(),sum(x['rows_scanned'] for x in sources),sum(x['window_rows'] for x in sources),len(providers),len(new),resurfaced,len(matches),json.dumps(sources)))
 pd.DataFrame(records).to_csv(result/'prospect_queue.csv',index=False)
 pd.DataFrame(matches,columns=['NPI','CRM Company Record ID','CRM Company Name','Evidence','Review Required','Provider Type']).to_csv(result/'crm_candidate_matches.csv',index=False)
 pd.DataFrame([x for x in records if x['New This Run']=='YES']).to_csv(result/'new_this_run.csv',index=False)
 pd.DataFrame([x for x in records if x['CRM Object']=='Company']).to_csv(result/'hubspot_company_staging_HOLD.csv',index=False)
 pd.DataFrame([x for x in records if x['CRM Object'].startswith('Contact')]).to_csv(result/'hubspot_contact_staging_HOLD.csv',index=False)
 statuses=pd.Series([x['CRM Match Status'] for x in records]).value_counts().to_dict()
 tiers=pd.Series([x['Tier'] for x in records]).value_counts().to_dict()
 summary={'run_id':run_id,'input_sources':sources,'source_count':len(sources),'records_after_filtering_dedupe':len(records),'duplicate_npis_removed_within_this_batch':sum(x['eligible_rows'] for x in sources)-len(records),'crm_candidate_rows':len(matches),'candidate_provider_count':len(set(x['NPI'] for x in matches)),'ambiguous_multi_company_npis':ambig,'new_prospect_events':len(new),'previously_seen_suppressed':resurfaced,'status_counts':statuses,'tier_counts':tiers,'crm_contacts_in_sample':len(contacts),'database_path':str(Path(args.database).resolve()),'operational_metrics':{'new_npi_events':len(new),'repeated_seen_npis_suppressed':resurfaced,'candidate_coverage':round(len(set(x['NPI'] for x in matches))/max(1,len(records)),4)},'business_funnel_metrics_pending_hubspot': ['reviewer-qualified lead rate','sales acceptance rate','lead-to-opportunity rate','NPPES-attributed pipeline value','duplicate CRM creation rate']}
 (result/'run_summary.json').write_text(json.dumps(summary,indent=2))
 checks={'unique_npi':len(set(x['NPI'] for x in records))==len(records),'no_duplicate_new_events':len(db.execute('SELECT npi FROM lead_events').fetchall())==len(set(x[0] for x in db.execute('SELECT npi FROM lead_events'))),'zip_text_5_characters':all(len(x['ZIP5'])==5 and x['ZIP5'].isdigit() for x in records),'valid_status':set(statuses).issubset({'Already in CRM','New Contact at Existing Account','Net New Account'}),'all_no_import':all(x['CRM Import Allowed'].startswith('NO') for x in records),'eligible_window_reconciles':all(x['eligible_rows']<=x['window_rows'] for x in sources)}
 (result/'qa_checks.json').write_text(json.dumps({'all_pass':all(checks.values()),'checks':checks},indent=2))
 if not all(checks.values()):raise RuntimeError(f'QA failed: {checks}')
 print(json.dumps({'run':run_id,'unique':len(records),'new':len(new),'suppressed':resurfaced,'matches':len(matches),'statuses':statuses,'tiers':tiers,'QA':'PASS'},indent=2))
 return summary

def cli():
 p=argparse.ArgumentParser(description=__doc__)
 p.add_argument('--weekly-zip',nargs='*',default=[],help='Official CMS weekly V2 ZIP(s)')
 p.add_argument('--prior-cohort',help='Reconstructed cohort CSV, explicitly NOT original weekly incremental')
 p.add_argument('--crm-workbook')
 p.add_argument('--crm-dir',help='Directory containing the two supplied CRM CSV exports')
 p.add_argument('--database',default='03_results/state.sqlite3')
 p.add_argument('--output',default='03_results/latest')
 p.add_argument('--weekly-window',nargs=2,default=['2026-11-02','2026-11-08'])
 p.add_argument('--prior-window',nargs=2,default=['2026-10-26','2026-11-01'])
 args=p.parse_args()
 if not args.weekly_zip and not args.prior_cohort: p.error('Provide at least one weekly ZIP or the reconstructed prior cohort')
 if not args.crm_workbook and not args.crm_dir: p.error('Provide either --crm-workbook or --crm-dir')
 return args
if __name__=='__main__':process(cli())
