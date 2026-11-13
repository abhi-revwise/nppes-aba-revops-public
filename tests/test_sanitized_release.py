import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
class TestSanitizedRelease(unittest.TestCase):
 def test_no_private_input_directories(self):
  for directory in ('demo_inputs','analysis_inputs','submission'):self.assertFalse((ROOT/directory).exists(),directory)
 def test_public_workflow_readonly(self):
  w=(ROOT/'.github/workflows/public_demo.yml').read_text()
  self.assertIn('contents: read',w);self.assertNotIn('contents: write',w);self.assertNotIn('schedule:',w)
 def test_synthetic_generator_marked(self):
  s=(ROOT/'scripts/generate_fixtures.py').read_text()
  self.assertIn('EXPLICITLY SYNTHETIC',s);self.assertIn('0000000001',s)
if __name__=='__main__':unittest.main()
