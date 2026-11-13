"""Discover official current weekly V2 NPPES files without guessing URLs."""
from __future__ import annotations
import argparse
from datetime import datetime
from pathlib import Path
import re
from urllib.parse import urljoin, urlparse
import requests
from bs4 import BeautifulSoup

CMS_PAGE = 'https://download.cms.gov/nppes/NPI_Files.html'
# filename dates mmddyy_mmddyy; archive may also be named NPPES_Data_Dissemination_110226_110826_Weekly_V2.zip
PATTERN = re.compile(r'(\d{6})_(\d{6})', re.IGNORECASE)


def discover_latest(page=CMS_PAGE, session=None):
    session = session or requests.Session()
    r = session.get(page, timeout=45)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, 'html.parser')
    hits=[]
    for a in soup.select('a[href]'):
        label=' '.join(a.stripped_strings).lower()
        href=urljoin(r.url,a.get('href'))
        candidate=label+' '+href.lower()
        if not ('weekly' in candidate and ('v.2' in candidate or 'v2' in candidate or 'version 2' in candidate)):
            continue
        m=PATTERN.search(candidate)
        if not m: continue
        try:
            start=datetime.strptime(m.group(1),'%m%d%y').date()
            end=datetime.strptime(m.group(2),'%m%d%y').date()
        except ValueError: continue
        if end < start: continue
        if urlparse(href).scheme!='https' or urlparse(href).hostname != 'download.cms.gov': continue
        hits.append({'url':href,'start':start.isoformat(),'end':end.isoformat()})
    if not hits:
        raise RuntimeError('No Version 2 weekly archive link discovered. CMS listing may have changed; verify manually, do not guess a URL.')
    return max(hits,key=lambda x:x['end'])


def download(url,destination,session=None,max_bytes=100*1024*1024):
    """Bounded streaming + ZIP integrity; HTTP failure fails the weekly run."""
    from zipfile import ZipFile
    session=session or requests.Session()
    dest=Path(destination)
    dest.parent.mkdir(parents=True,exist_ok=True)
    part=dest.with_name(dest.name+'.part')
    try:
        with session.get(url,timeout=(20,120),stream=True) as r:
            r.raise_for_status()
            if (urlparse(r.url).hostname or '').lower() != 'download.cms.gov':
                raise ValueError('Redirected away from expected CMS download domain')
            count=0
            with open(part,'wb') as f:
                for block in r.iter_content(1024*1024):
                    count+=len(block)
                    if count>max_bytes:raise ValueError('Unusually large weekly file; aborting download')
                    f.write(block)
        with ZipFile(part) as z:
            primary=[n for n in z.namelist() if Path(n).name.startswith('npidata_pfile_') and n.lower().endswith('.csv')]
            if len(primary)!=1:raise ValueError('Not a recognized weekly provider ZIP')
            if z.testzip() is not None:raise ValueError('Corrupt archive')
        part.replace(dest)
        return dest
    finally:
        part.unlink(missing_ok=True)

if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('--output-dir',default='.cache/cms')
    p.add_argument('--url',help='Official CMS weekly archive override, not a fabricated URL')
    p.add_argument('--start',help='YYYY-MM-DD; required with --url')
    p.add_argument('--end',help='YYYY-MM-DD; required with --url')
    a=p.parse_args()
    d=({'url':a.url,'start':a.start,'end':a.end} if a.url else discover_latest())
    if not all(d.values()):p.error('Override requires --url, --start and --end')
    file=download(d['url'],Path(a.output_dir)/f"weekly_{d['start']}_{d['end']}.zip")
    print(f"{file}|{d['start']}|{d['end']}")
