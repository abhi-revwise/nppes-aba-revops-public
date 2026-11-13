"""Hosted workflow: authoritative Postgres state + existing deterministic Python engine.

A transaction-level advisory lock serializes runs. Postgres is persistent across
GitHub runners; an ephemeral SQLite snapshot adapts the tested processing core.
No production CRM writes are performed.
"""
from __future__ import annotations
import argparse, os, sqlite3, tempfile, json
from pathlib import Path
from types import SimpleNamespace
import psycopg
from psycopg.rows import dict_row
from cms_discovery import discover_latest, download
from run_weekly import process,db_open

SCHEMA='''
CREATE TABLE IF NOT EXISTS nppes_seen_providers (
 npi text PRIMARY KEY, first_seen_run text NOT NULL, last_seen_run text NOT NULL,
 first_source text NOT NULL, initial_class text, last_status text, last_fingerprint text
);
CREATE TABLE IF NOT EXISTS nppes_processed_releases (
 source_hash text PRIMARY KEY, source_name text, provenance text, first_run text
);
CREATE TABLE IF NOT EXISTS nppes_lead_events (
 npi text PRIMARY KEY, first_run text, classification text, status text, tier text
);
CREATE TABLE IF NOT EXISTS nppes_runs (
 run_id text PRIMARY KEY, started_utc text, records_read bigint, in_window bigint,
 eligible bigint, novel bigint, resurfaced bigint, crm_candidates bigint, source_notes text
);
'''
TABLES={
 'seen_providers':('nppes_seen_providers',['npi','first_seen_run','last_seen_run','first_source','initial_class','last_status','last_fingerprint']),
 'processed_releases':('nppes_processed_releases',['source_hash','source_name','provenance','first_run']),
 'lead_events':('nppes_lead_events',['npi','first_run','classification','status','tier']),
 'runs':('nppes_runs',['run_id','started_utc','records_read','in_window','eligible','novel','resurfaced','crm_candidates','source_notes'])
}

def stage_from_pg(pg,sqlite):
    for local,(remote,cols) in TABLES.items():
        names=','.join(cols)
        rows=pg.execute(f'SELECT {names} FROM {remote}').fetchall()
        if rows:
            sqlite.executemany(f'INSERT INTO {local}({names}) VALUES({",".join("?" for _ in cols)})',[tuple(row[col] for col in cols) for row in rows])
    sqlite.commit()

def save_to_pg(pg,sqlite):
    for local,(remote,cols) in TABLES.items():
        names=','.join(cols)
        key=cols[0]
        updates=','.join(f'{col}=excluded.{col}' for col in cols[1:])
        rows=sqlite.execute(f'SELECT {names} FROM {local}').fetchall()
        if rows:
            sql=f'INSERT INTO {remote}({names}) VALUES({",".join("%s" for _ in cols)}) ON CONFLICT ({key}) DO UPDATE SET {updates}'
            pg.executemany(sql,rows)

def main():
    p=argparse.ArgumentParser(description='Run latest CMS weekly V2 with persistent PostgreSQL NPI history')
    p.add_argument('--crm-dir',required=True)
    p.add_argument('--output',default='outputs/latest')
    p.add_argument('--local-zip',help='Optional verified historical weekly ZIP for testing')
    p.add_argument('--start',help='YYYY-MM-DD; required with local-zip')
    p.add_argument('--end',help='YYYY-MM-DD; required with local-zip')
    p.add_argument('--force',action='store_true',help='Audit rerun even if source release previously processed; zero new first-seen events')
    a=p.parse_args()
    dsn=os.getenv('DATABASE_URL')
    if not dsn:raise RuntimeError('DATABASE_URL environment secret is required; do not commit it')
    if a.local_zip:
        if not a.start or not a.end:p.error('--local-zip requires --start and --end')
        source=Path(a.local_zip);start=a.start;end=a.end
    else:
        info=discover_latest();start=info['start'];end=info['end']
        source=download(info['url'],Path('.cache/cms')/f'weekly_{start}_{end}.zip')
    if not source.is_file():raise FileNotFoundError(source)
    # Keep a single serialized transaction open until output checks and state commit finish.
    with psycopg.connect(dsn,row_factory=dict_row,connect_timeout=30,sslmode='require',prepare_threshold=None) as conn:
        with conn.transaction():
            pg=conn.cursor()
            pg.execute('SELECT pg_advisory_xact_lock(914220261)')
            pg.execute(SCHEMA)
            from run_weekly import sha
            source_hash=sha(source)
            exists=pg.execute('SELECT 1 FROM nppes_processed_releases WHERE source_hash=%s',(source_hash,)).fetchone()
            if exists and not a.force:
                print(json.dumps({'status':'already_processed','source':source.name,'new_prospect_events':0}))
                return
            with tempfile.TemporaryDirectory() as tmp:
                db_file=Path(tmp)/'snapshot.sqlite3'
                db=db_open(db_file)
                stage_from_pg(pg,db)
                db.close()
                args=SimpleNamespace(weekly_zip=[str(source)],prior_cohort=None,prior_window=[start,end],weekly_window=[start,end],crm_workbook=None,crm_dir=a.crm_dir,database=str(db_file),output=a.output)
                summary=process(args)
                if not json.loads((Path(a.output)/'qa_checks.json').read_text())['all_pass']:
                    raise RuntimeError('QA failure: refusing to commit remote state')
                snapshot=sqlite3.connect(db_file)
                save_to_pg(pg,snapshot)
                snapshot.close()
                print(json.dumps({'hosted_state_committed':True,'new_prospect_events':summary['new_prospect_events'],'source':source.name}))

if __name__=='__main__': main()
