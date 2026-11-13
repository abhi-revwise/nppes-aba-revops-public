"""Offline unit tests: CMS discovery + safe error path, no credentials required."""
import io, sys, unittest, tempfile
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'pipeline'))
from cms_discovery import discover_latest,download

class FakeResponse:
    def __init__(self,html,url='https://download.cms.gov/nppes/NPI_Files.html'):
        self.text=html;self.url=url
    def raise_for_status(self): pass
class FakeSession:
    def __init__(self,html):self.html=html
    def get(self,url,timeout=None,stream=False):return FakeResponse(self.html)

class TestCMS(unittest.TestCase):
    def test_latest_weekly_is_selected(self):
        html='''<a href="NPPES_Data_Dissemination_102626_110126_Weekly_V2.zip">NPPES V.2 Weekly Update 102626_110126</a><a href="NPPES_Data_Dissemination_110226_110826_Weekly_V2.zip">NPPES V.2 Weekly Update 110226_110826</a><a href="NPPES_monthly.zip">Monthly</a>'''
        x=discover_latest(session=FakeSession(html))
        self.assertEqual((x['start'],x['end']),('2026-11-02','2026-11-08'))
        self.assertEqual(x['url'],'https://download.cms.gov/nppes/NPPES_Data_Dissemination_110226_110826_Weekly_V2.zip')
    def test_missing_weekly_is_not_guessed(self):
        with self.assertRaises(RuntimeError):discover_latest(session=FakeSession('<a href="monthly.zip">Monthly</a>'))
    def test_no_redirect_to_unrelated_host(self):
        # Download must never silently accept files from off-domain hosts.
        class Response:
            url='https://evil.example/file.zip'
            def raise_for_status(self):pass
            def __enter__(self):return self
            def __exit__(self,*a):return False
        class Session:
            def get(self,*a,**kw):return Response()
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(ValueError):download('https://download.cms.gov/nppes/something.zip',Path(d)/'file.zip',session=Session())

if __name__=='__main__':unittest.main()
