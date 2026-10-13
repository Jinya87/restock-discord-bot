import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from monitor import URLS, WATCHED, PENDING_VERIFICATION, main, newly_available

class ReplacementSafetyTests(unittest.TestCase):
    def test_six_exact_requested_targets(self):
        self.assertEqual({u.split('/')[-1] for u in URLS.values()}, {
            '13698274396', '13697333976', '13733754793',
            '13698276158', '13734519413', '13699099702'})
        self.assertEqual(len(URLS), 6)

    def test_retired_targets_removed(self):
        self.assertFalse(any('kurly' in u or 'hmall' in u for u in URLS.values()))
        self.assertEqual(newly_available({}, {'kurly:key': True, 'hmall': True}), [])

    def test_unverified_targets_cannot_notify(self):
        self.assertEqual(PENDING_VERIFICATION, WATCHED)
        self.assertEqual(newly_available({}, {key: True for key in WATCHED}), [])

    def test_replace_state_keeps_unknown_without_network_or_alerts(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / 'state.json'
            path.write_text(json.dumps({'stock': {'kurly:key': True, 'hmall': True}}))
            with patch('monitor.STATE_FILE', path), patch('sys.argv', ['monitor.py']), patch('monitor.send_discord') as send, patch.dict(os.environ, {'GITHUB_STEP_SUMMARY': ''}):
                self.assertEqual(main(), 0)
                send.assert_not_called()
            state = json.loads(path.read_text())
            self.assertEqual(set(state['stock']), WATCHED)
            self.assertTrue(all(v is None for v in state['stock'].values()))
            self.assertEqual(set(state['pending_verification']), WATCHED)

    def test_dry_run_leaves_state_unchanged(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / 'state.json'
            path.write_text('{"stock": {}}')
            before = path.read_text()
            with patch('monitor.STATE_FILE', path), patch('sys.argv', ['monitor.py', '--dry-run']), patch.dict(os.environ, {'GITHUB_STEP_SUMMARY': ''}):
                self.assertEqual(main(), 0)
            self.assertEqual(path.read_text(), before)

    def test_summary_explicitly_says_alerts_paused(self):
        with tempfile.TemporaryDirectory() as d:
            summary = Path(d) / 'summary.md'
            with patch('monitor.STATE_FILE', Path(d) / 'state.json'), patch('sys.argv', ['monitor.py', '--dry-run']), patch.dict(os.environ, {'GITHUB_STEP_SUMMARY': str(summary)}):
                main()
            text = summary.read_text()
            self.assertEqual(text.count('등록됨 · 재고 미확인 · 알림 중지'), 6)
            self.assertNotIn('구매 가능', text)

if __name__ == '__main__':
    unittest.main()
