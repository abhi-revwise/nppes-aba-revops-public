import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'pipeline'))
from decision_layer import classify
class TestDomainRules(unittest.TestCase):
 def test_supervised_unknown_company_not_new_account(self):
  for tx in ('106S00000X','106E00000X'):
   x=classify('1',tx,'','','2025550101','Fake Street')
   self.assertEqual(x['provider_type'],'Individual at Existing Company')
   self.assertEqual(x['crm_action'],'Do not import; market signal')
   self.assertEqual(x['crm_import_allowed'],'NO')
 def test_unassociated_bcba_possible_solo(self):
  x=classify('1','103K00000X','','','2025550101','Fake Street')
  self.assertEqual(x['provider_type'],'Solo Practitioner (possible new practice)')
  self.assertEqual(x['crm_match_status'],'Net New Account')
 def test_org_account_review_staging(self):
  x=classify('2','103K00000X','','','2025550101','Fake Street')
  self.assertEqual(x['crm_action'],'Create Company + Contact')
  self.assertEqual(x['crm_import_allowed'],'YES')
 def test_address_contact_match_held(self):
  x=classify('1','106S00000X','SYNTH-COMP-002','exact full practice address','2025550101','Fake Street')
  self.assertEqual(x['review_required'],'YES')
if __name__=='__main__':unittest.main()
