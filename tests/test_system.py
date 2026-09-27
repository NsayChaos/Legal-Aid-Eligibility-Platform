import tempfile, unittest, sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import server

class SystemTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.db=Path(self.temp.name)/'test.db';server.init_db(self.db)
 def tearDown(self):self.temp.cleanup()
 def test_metric_scope_and_validation(self):
  before=server.metrics(self.db,'partner')
  server.import_metrics(self.db,'pilot',[{'branch_id':'north','period':'2026-09','intakes':100,'completed':70,'staff_minutes':2400,'recontacts':25,'referrals':12,'accepted_referrals':9}])
  self.assertEqual(before,server.metrics(self.db,'partner'))
  with self.assertRaises(ValueError):server.import_metrics(self.db,'partner',[{'branch_id':'north','period':'2026-09','intakes':100,'completed':70,'staff_minutes':2400,'recontacts':25,'referrals':12,'accepted_referrals':9}])
 def test_reject_impossible_metrics_without_partial_writes(self):
  before=server.metrics(self.db,'pilot')
  r={'branch_id':'north','period':'2026-09','intakes':2,'completed':3,'staff_minutes':2400,'recontacts':0,'referrals':0,'accepted_referrals':0}
  with self.assertRaises(ValueError):server.import_metrics(self.db,'pilot',[r])
  self.assertEqual(before,server.metrics(self.db,'pilot'))
 def test_source_scope_blocks_arbitrary_hosts(self):
  for url in ['http://127.0.0.1/admin','https://evil.example','https://www.lsc.gov.evil.example/','https://www.lsc.gov:8443/']:
   with self.assertRaises(ValueError):server.validate_source_url(url)
 def test_changed_source_creates_review_and_unchanged_does_not(self):
  server.record_snapshot(self.db,'lsc-intake','One reviewed source '*30)
  server.record_snapshot(self.db,'lsc-intake','One reviewed source '*30)
  with server.connection(self.db) as c:self.assertEqual(c.execute('select count(*) from source_reviews').fetchone()[0],1)
  server.record_snapshot(self.db,'lsc-intake','Changed source '*30)
  with server.connection(self.db) as c:self.assertEqual(c.execute('select count(*) from source_reviews').fetchone()[0],2)
 def test_unknown_society_rejected(self):
  with self.assertRaises(ValueError):server.metrics(self.db,'unknown')
if __name__=='__main__':unittest.main()
