"""Current profile contract and executable reference; no legacy core judge."""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]


def read(name):
    return json.loads((ROOT / name).read_text())


class TacticalContract(unittest.TestCase):
    def test_current_profile_is_the_root_contract(self):
        contract = read('CONTRACT.json')
        profile = read('content/clash_balance.json')
        self.assertEqual(contract['ruleset_id'], 'pcg.clash.v0')
        self.assertEqual(contract['balance_version'], profile['balance_version'])
        self.assertEqual(contract['rules'], profile['rules'])
        self.assertEqual(contract['random_deck'], profile['deck'])
        for name in contract['content_load_order']:
            self.assertTrue((ROOT / name).is_file(), name)
        ref = contract['reference']
        self.assertEqual(hashlib.sha256((ROOT / ref['path']).read_bytes()).hexdigest(), ref['sha256'])

    def test_reference_behaviors(self):
        self.assertIsNotNone(shutil.which('node'), 'Node.js is required for the current reference judge')
        for file in sorted((ROOT / 'tests').glob('*.test.cjs')):
            with self.subTest(suite=file.name):
                run = subprocess.run(['node', str(file)], cwd=ROOT, capture_output=True, text=True)
                self.assertEqual(run.returncode, 0, run.stdout + run.stderr)

    def test_web_sync_when_sibling_is_available(self):
        web = ROOT.parent / 'pulse_card_game_web'
        if not web.is_dir():
            self.skipTest('Sibling web repository is not checked out')
        pairs = [('reference/clash.js', 'src/clash/engine.js')]
        pairs += [('content/' + name, 'content/clash/' + name) for name in
                  ['clash_balance.json', 'clash_tactics.json', 'clash_roster_96.json', 'capabilities.json']]
        for local, sibling in pairs:
            with self.subTest(file=local):
                self.assertEqual((ROOT / local).read_bytes(), (web / sibling).read_bytes())


if __name__ == '__main__':
    unittest.main()
