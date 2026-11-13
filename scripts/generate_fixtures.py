#!/usr/bin/env python3
"""Generate tiny, EXPLICITLY SYNTHETIC NPPES-shaped and CRM fixtures.

All names are invented, phones are 555 examples, NPIs are deliberately
invalid placeholders. No Passage Health CRM/provider data are used.
"""
import csv
from io import StringIO
from pathlib import Path
from zipfile import ZipFile,ZIP_DEFLATED

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'outputs'/'synthetic_inputs'
TAX=['Healthcare Provider Taxonomy Code_'+str(i) for i in range(1,16)]
FIELDS=['NPI','Entity Type Code','Provider Enumeration Date','Last Update Date','NPI Deactivation Date',
'Provider Organization Name (Legal Business Name)','Provider First Name','Provider Last Name (Legal Name)',
'Provider First Line Business Practice Location Address','Provider Business Practice Location Address City Name',
'Provider Business Practice Location Address State Name','Provider Business Practice Location Address Postal Code',
'Provider Business Practice Location Address Telephone Number',*TAX]

def provider(npi,entity,date,code,org='',first='',last='',address='11 Demo Street',phone='2025550100'):
    r=dict.fromkeys(FIELDS,'')
    r.update({'NPI':npi,'Entity Type Code':entity,'Provider Enumeration Date':date,'Last Update Date':date,
    'Provider Organization Name (Legal Business Name)':org,'Provider First Name':first,'Provider Last Name (Legal Name)':last,
    'Provider First Line Business Practice Location Address':address,
    'Provider Business Practice Location Address City Name':'Exampleville',
    'Provider Business Practice Location Address State Name':'VA',
    'Provider Business Practice Location Address Postal Code':'01234',
    'Provider Business Practice Location Address Telephone Number':phone,
    'Healthcare Provider Taxonomy Code_1':code})
    return r

def csv_text(rows,fields):
    f=StringIO();w=csv.DictWriter(f,fieldnames=fields,lineterminator='\n');w.writeheader();w.writerows(rows)
    return f.getvalue()

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    week1=[
       provider('0000000001','2','11/02/2026','103K00000X',org='Example ABA Studio',address='11 Demo Street'),
       provider('0000000002','1','11/03/2026','103K00000X',first='Taylor',last='Sample',address='55 Fiction Road',phone='2025550101'),
       provider('0000000003','1','11/04/2026','106S00000X',first='Casey',last='Example',address='77 Practice Lane',phone='2025550102'),
       provider('0000000004','1','11/05/2026','106E00000X',first='Jordan',last='Illustration',address='90 Test Avenue',phone='2025550103'),
       provider('0000000005','1','11/06/2026','207Q00000X',first='Non',last='ABA',address='90 Test Avenue'),
       provider('0000000006','1','10/15/2026','103K00000X',first='Earlier',last='Update',address='90 Test Avenue'),
    ]
    week2=[
       provider('0000000007','2','11/09/2026','103K00000X',org='Example Expansion Clinic',address='25 Fiction Parkway'),
       provider('0000000008','1','11/10/2026','103K00000X',first='Alex',last='Pretend',address='11 Demo Street',phone='2025550100'),
       provider('0000000009','1','11/11/2026','106S00000X',first='Sam',last='Madeup',address='25 Fiction Parkway',phone='2025550109'),
       provider('0000000001','2','11/02/2026','103K00000X',org='Example ABA Studio',address='11 Demo Street'),
    ]
    for date1,date2,rows in [('20261102','20261108',week1),('20261109','20261115',week2)]:
        path=OUT/f'NPPES_SYNTHETIC_{date1}_{date2}_Weekly_V2.zip'
        with ZipFile(path,'w',ZIP_DEFLATED) as z:
            z.writestr(f'npidata_pfile_{date1}-{date2}.csv',csv_text(rows,FIELDS))
    companies=[
      {'Record ID':'SYNTH-COMP-001','Company name':'Example ABA Studio','Company Domain Name':'example.org','NPI number':'0000000001',
      'HQ Address - Line 1':'11 Demo Street','HQ Address - City':'Exampleville','HQ Address - State/Province Code':'VA','HQ Address - Zip Code':'01234'},
      {'Record ID':'SYNTH-COMP-002','Company name':'Fictional Clinic','Company Domain Name':'fiction.example','NPI number':'',
      'HQ Address - Line 1':'77 Practice Lane','HQ Address - City':'Exampleville','HQ Address - State/Province Code':'VA','HQ Address - Zip Code':'01234'},
    ]
    contacts=[{'Record ID':'SYNTH-CONTACT-001','First Name':'Morgan','Last Name':'Imaginary','Email':'morgan@example.org','LinkedIn Profile URL':'','Job Title':'Demo Contact','Phone Number':'2025550199'}]
    (OUT/'sample_crm_export_companies.csv').write_text(csv_text(companies,list(companies[0])))
    (OUT/'sample_crm_export_contacts.csv').write_text(csv_text(contacts,list(contacts[0])))
    print('Synthetic demo fixtures written to',OUT)

if __name__=='__main__':main()
