import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
sys.path.insert(0,str(Path(__file__).parents[1]/'scripts'))
import research_coverage as m

class CoverageTests(unittest.TestCase):
    def plan(self): return m.make_plan('Transformers',['How does attention replace recurrence?'],'2026-11-04')
    def test_dual_track_contract(self):
        plan=self.plan(); self.assertEqual(plan['questions'][0]['tracks'],['classic','recent'])
        plan['questions'][0]['tracks']=['recent']
        with self.assertRaises(ValueError): m.validate_plan(plan)
    def test_versions_deduplicated(self):
        self.assertEqual(m.normalized_id({'url':'https://arxiv.org/pdf/1706.03762v2'}),m.normalized_id({'url':'https://arxiv.org/abs/1706.03762v1'}))
    def test_no_run_is_unsearched(self):
        result=m.audit(self.plan(),[])
        self.assertFalse(result['complete_topic']); self.assertEqual(len(result['coverage']),2)
        self.assertEqual(result['coverage'][0]['run_statuses'],['not_searched'])
    def test_provenance_and_tamper(self):
        with tempfile.TemporaryDirectory() as temp:
            folder=Path(temp); response=folder/'response.json'
            response.write_text(json.dumps({'provider':'offline-fixture','results':[{'href':'https://arxiv.org/abs/1706.03762v1'}]}))
            run={'status':'replayed_unverified','question_id':'q1','track':'classic','cutoff':'2026-11-04',
                 'events':[{'kind':'web-search','response':str(response),'response_sha256':hashlib.sha256(response.read_bytes()).hexdigest()}]}
            (folder/'gptr-run.json').write_text(json.dumps(run))
            result=m.audit(self.plan(),[folder]); self.assertEqual(len(result['candidates']),1)
            self.assertEqual(result['candidates'][0]['verification'],'unverified')
            self.assertEqual(result['coverage'][0]['run_statuses'],['replayed_unverified'])
            response.write_text('{}')
            with self.assertRaises(ValueError): m.audit(self.plan(),[folder])

if __name__=='__main__': unittest.main()
