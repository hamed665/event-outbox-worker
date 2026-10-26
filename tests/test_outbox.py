import unittest
import tempfile
from concurrent.futures import ThreadPoolExecutor
from relaybox.core import Outbox, StaleLease

class OutboxTests(unittest.TestCase):
    def setUp(self): self.q=Outbox(max_attempts=2)
    def tearDown(self): self.q.close()
    def write(self): return self.q.write('t','e','order',{'v':1},now=0)
    def test_nonfinite_clock_rejected(self):
        for invalid in (float("nan"),float("inf"),True):
            with self.assertRaises(ValueError): self.q.claim(invalid)
        with self.assertRaises(ValueError): self.q.claim(0,float("nan"))
    def test_atomic_write_and_dedupe(self):
        self.assertTrue(self.write()); self.assertFalse(self.write())
        with self.assertRaises(ValueError): self.q.write('t','e','order',{'v':2},now=0)
        self.assertEqual(self.q.db.execute('SELECT body FROM entities').fetchone()[0],'{"v":1}')
    def test_retry_schedule(self):
        self.write(); j=self.q.claim(0); self.q.finish(j,1,error='timeout')
        self.assertIsNone(self.q.claim(2)); self.assertIsNotNone(self.q.claim(3))
    def test_expired_worker_fenced(self):
        self.write(); old=self.q.claim(0,lease_seconds=2); new=self.q.claim(2)
        with self.assertRaises(StaleLease): self.q.finish(old,3)
        self.q.finish(new,3); self.assertEqual(self.q.stats(),{'delivered':1})
    def test_dead_letter_and_manual_requeue(self):
        self.write(); self.q.finish(self.q.claim(0),1,error='fail')
        self.q.finish(self.q.claim(3),4,error='fail')
        self.assertEqual(self.q.stats(),{'dead':1}); self.assertTrue(self.q.requeue('t','e',5))
        self.assertEqual(self.q.claim(5)['attempts'],1)
    def test_crash_budget(self):
        self.write(); self.q.claim(0,1); self.q.claim(1,1)
        self.assertIsNone(self.q.claim(2)); self.assertEqual(self.q.stats(),{'dead':1})
    def test_tenant_scoped_keys(self):
        self.write(); self.q.write('other','e','order',{'v':2},0)
        self.assertEqual(self.q.stats(),{'pending':2})
    def test_single_winner(self):
        with tempfile.TemporaryDirectory() as d:
            path=d+'/queue.db'; q=Outbox(path); q.write('t','e','o',{},0); q.close()
            def claim(_):
                worker=Outbox(path)
                try: return worker.claim(0) is not None
                finally: worker.close()
            with ThreadPoolExecutor(2) as pool:
                self.assertEqual(sum(pool.map(claim,range(2))),1)
