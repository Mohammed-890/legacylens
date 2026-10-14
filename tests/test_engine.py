import unittest
from legacylens.engine import analyze, impact, investigate, search, validate_files
from legacylens.repair import fixture_files, execute_approved, proposal


class AnalysisTests(unittest.TestCase):
    def setUp(self):
        self.p = analyze(fixture_files())

    def test_import_chain(self):
        self.assertEqual(set(impact(self.p,'customers.py')['affected']), {'invoices.py','api.py','test_invoices.py'})

    def test_disconnected_file(self):
        self.assertEqual(impact(self.p,'notifications.py')['affected'],[])

    def test_unknown_target(self):
        with self.assertRaises(ValueError):
            impact(self.p,'not-real.py')

    def test_cycle_terminates(self):
        p=analyze({'a.py':'import b','b.py':'import a'})
        self.assertEqual(impact(p,'a.py')['affected'],['b.py'])

    def test_relative_import(self):
        p=analyze({'app/a.py':'from . import b','app/b.py':'x=1'})
        self.assertEqual(p['edges'][0]['target'],'app/b.py')

    def test_nested_relative(self):
        p=analyze({'app/sub/a.py':'from .. import b','app/b.py':'x=1'})
        self.assertEqual(p['edges'][0]['target'],'app/b.py')

    def test_sql_risk(self):
        self.assertTrue(any(f['rule']=='sql-interpolation' and f['path']=='reporting.py' for f in self.p['findings']))

    def test_parameterized_sql_not_flagged(self):
        p=analyze({'db.py':'db.execute("SELECT * FROM x WHERE id=?", (id,))'})
        self.assertFalse(p['findings'])

    def test_mutable_default(self):
        self.assertTrue(any(f['rule']=='mutable-default' for f in self.p['findings']))

    def test_bare_except(self):
        self.assertTrue(any(f['rule']=='bare-except' for f in self.p['findings']))

    def test_dynamic_code(self):
        p=analyze({'a.py':'eval(user_input)'})
        self.assertEqual(p['findings'][0]['rule'],'dynamic-exec')

    def test_timeout_rule(self):
        p=analyze({'a.py':'requests.get(url)\nrequests.get(url, timeout=5)'})
        self.assertEqual(len(p['findings']),1)

    def test_syntax_warning(self):
        p=analyze({'broken.py':'def broken('})
        self.assertEqual(len(p['warnings']),1)
        self.assertTrue(p['chunks'])

    def test_retrieval(self):
        self.assertEqual(search(self.p,'display_name full_name migration')[0]['path'],'RUNBOOK.md')

    def test_no_match_abstains(self):
        result=investigate(self.p,'zzqxyzz nonexistentxyz')
        self.assertEqual(result['evidence'],[])
        self.assertIn('does not contain',result['answer'])

    def test_citations_exact(self):
        for c in self.p['chunks']:
            self.assertEqual(c['text'],'\n'.join(self.p['files'][c['path']].splitlines()[c['start']-1:c['end']]))

    def test_path_traversal(self):
        for path in ['../secret.py','/etc/config.py','a/../../b.py','x\\a.py']:
            with self.subTest(path=path), self.assertRaises(ValueError):
                validate_files({path:'x=1'})

    def test_secrets_skipped(self):
        self.assertEqual(validate_files({'.env':'KEY=secret','credentials.json':'{}','a.py':'x=1'}),{'a.py':'x=1'})

    def test_size_limit(self):
        with self.assertRaises(ValueError):
            validate_files({'a.py':'x'*2_000_001})

    def test_fingerprint_stable(self):
        self.assertEqual(analyze({'a.py':'x=1','b.py':'x=2'})['fingerprint'],analyze({'b.py':'x=2','a.py':'x=1'})['fingerprint'])

    def test_source_is_not_executed(self):
        p=analyze({'evil.py':'raise RuntimeError("NEVER RUN")'})
        self.assertEqual(p['stats']['files'],1)

    def test_repair_proposal_integrity(self):
        with self.assertRaises(ValueError):
            execute_approved('wrong-id')

    def test_repair_and_source_unchanged(self):
        before=fixture_files()
        result=execute_approved(proposal()['id'])
        self.assertTrue(result['verified'])
        self.assertIn('Ran 5 tests',result['after']['output'])
        self.assertEqual(before,fixture_files())


if __name__=='__main__':
    unittest.main()
