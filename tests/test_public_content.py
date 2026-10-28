from __future__ import annotations
import importlib.util
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch
from tests.helpers import PACKAGE, WorkspaceTest

spec = importlib.util.spec_from_file_location('public_content', PACKAGE / 'scripts/check_public_content.py')
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)
PUBLIC_ADDRESS = 'noreply' + '@anthropic.com'
PRIVATE_ADDRESS = 'person' + '@private.test'


class PublicContentTests(WorkspaceTest):
    def commit(self, repo, message='Change fixture'):
        self.git(repo, 'add', '-A')
        self.git(repo, 'commit', '--allow-empty', '-m', message)

    def test_reviewed_attribution_is_allowed_only_in_commit_trailers(self):
        repo = self.repo('attribution')
        self.commit(repo, 'Change fixture\n\nCo-Authored-By: Public Bot <' + PUBLIC_ADDRESS + '>')
        self.assertEqual(audit.scan(repo, [], history=True)[1], [])
        (repo / 'ordinary.txt').write_text(PUBLIC_ADDRESS)
        self.assertIn(('ordinary.txt', 'email'), audit.scan(repo, [])[1])
        self.commit(repo, 'Mention ' + PUBLIC_ADDRESS)
        self.assertTrue(any(name.endswith(':message') and reason == 'email'
                            for name, reason in audit.scan(repo, [], history=True)[1]))

    def test_unreviewed_and_malformed_trailers_are_rejected(self):
        repo = self.repo('negative')
        for message in [
            'Change\n\nCo-Authored-By: Person <' + PRIVATE_ADDRESS + '>',
            'Change\n\nCo-Authored-By: Public Bot <' + PUBLIC_ADDRESS + '> extra text',
            'Change\n\nCo-Authored-By: Public Bot <' + PUBLIC_ADDRESS + '>\n\nMore prose',
            'Co-Authored-By: Public Bot <' + PUBLIC_ADDRESS + '>',
        ]:
            self.commit(repo, message)
        findings = [f for f in audit.scan(repo, [], history=True)[1] if f[0].endswith(':message')]
        self.assertEqual(len(findings), 4)

    def test_denylist_overrides_public_attribution_without_exposing_term(self):
        repo = self.repo('deny')
        self.commit(repo, 'Change\n\nCo-Authored-By: Public Bot <' + PUBLIC_ADDRESS + '>')
        findings = audit.scan(repo, ['anthropic'])[1]
        self.assertEqual(findings, [])
        findings = audit.scan(repo, ['anthropic'], history=True)[1]
        self.assertTrue(findings)
        self.assertTrue(all(reason == 'private term' for _, reason in findings))

    def test_history_preserves_deleted_content_paths_symlinks_and_binary_text(self):
        repo = self.repo('history')
        credential = 'ghp_' + 'x' * 24
        secret_path = '/' + 'home/fixture/private'
        (repo / 'old.txt').write_text(credential)
        (repo / 'bytes.bin').write_bytes(b'\xff' + PRIVATE_ADDRESS.encode())
        # Git stores symlink targets as blobs, even on hosts that cannot create symlinks.
        target = self.root / 'target.txt'
        target.write_text(secret_path)
        oid = self.git(repo, 'hash-object', '-w', str(target))
        self.git(repo, 'update-index', '--add', '--cacheinfo', '120000,' + oid + ',link')
        self.git(repo, 'add', 'old.txt', 'bytes.bin')
        self.git(repo, 'commit', '-m', 'Add historical findings')
        first = self.git(repo, 'rev-parse', 'HEAD')[:8]
        self.git(repo, 'rm', '--cached', 'link')
        (repo / 'old.txt').unlink()
        (repo / 'bytes.bin').write_text('clean')
        self.commit(repo)
        findings = audit.scan(repo, [], history=True)[1]
        self.assertIn((first + ':old.txt', 'credential'), findings)
        self.assertIn((first + ':bytes.bin', 'email'), findings)
        self.assertIn((first + ':link', 'personal path'), findings)

    def test_same_blob_under_another_path_is_still_checked(self):
        repo = self.repo('paths')
        (repo / 'safe.txt').write_text('ordinary')
        self.commit(repo)
        (repo / PRIVATE_ADDRESS).write_text('ordinary')
        self.commit(repo)
        findings = audit.scan(repo, [], history=True)[1]
        self.assertTrue(any(name.endswith(':' + PRIVATE_ADDRESS) and reason == 'email'
                            for name, reason in findings))

    def test_repeated_history_uses_bounded_git_calls_and_scans_unchanged_entries_once(self):
        repo = self.repo('dedup')
        (repo / 'unchanged.txt').write_text('unchanged sentinel')
        for i in range(12):
            self.commit(repo, f'Change {i}')
        calls, scans = [], []
        original_run, original_check = audit.subprocess.run, audit.subprocess.check_output
        original_violations = audit.violations
        def run(*args, **kwargs):
            calls.append(args[0])
            return original_run(*args, **kwargs)
        def check(*args, **kwargs):
            calls.append(args[0])
            return original_check(*args, **kwargs)
        def violations(text, *args, **kwargs):
            if text == 'unchanged.txt\nunchanged sentinel':
                scans.append(text)
            return original_violations(text, *args, **kwargs)
        with patch.object(audit.subprocess, 'run', side_effect=run), \
             patch.object(audit.subprocess, 'check_output', side_effect=check), \
             patch.object(audit, 'violations', side_effect=violations):
            findings = audit.scan(repo, [], history=True)[1]
        self.assertEqual(findings, [])
        self.assertLessEqual(len(calls), 6, 'History must batch Git object reads')
        self.assertLessEqual(len(scans), 2, 'One working-tree and one historical scan')

    def test_history_findings_match_reference_traversal(self):
        repo = self.repo('reference')
        (repo / 'first.txt').write_text(PRIVATE_ADDRESS)
        self.commit(repo)
        (repo / 'first.txt').rename(repo / 'second.txt')
        self.commit(repo)
        expected = set()
        for commit in self.git(repo, 'rev-list', '--all').splitlines():
            for name in self.git(repo, 'ls-tree', '-r', '--name-only', commit).splitlines():
                data = self.git(repo, 'show', f'{commit}:{name}')
                expected.update((name, r) for r in audit.violations(name + '\n' + data, []))
        actual = {(name.split(':', 1)[1], reason) for name, reason in
                  audit.scan(repo, [], history=True)[1] if ':' in name and not name.endswith(':message')}
        self.assertEqual(actual, expected)

    def test_credentials_and_personal_paths_remain_blocking(self):
        text = 'github_pat_' + 'x' * 24 + '\n/' + 'Users/fixture/private'
        self.assertEqual(audit.violations(text, []), ['credential', 'personal path'])

    def test_cli_redacts_sensitive_names_and_private_terms(self):
        repo = self.repo('redaction')
        credential = 'ghp_' + 'z' * 24
        (repo / credential).write_text('ordinary')
        (repo / PRIVATE_ADDRESS).write_text('ordinary')
        deny = self.root / 'deny.txt'
        deny.write_text('hiddenword')
        (repo / 'hiddenword.txt').write_text('ordinary')
        result = subprocess.run([sys.executable, str(PACKAGE / 'scripts/check_public_content.py'),
                                 str(repo), '--deny-file', str(deny)], env=self.env,
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 1)
        self.assertNotIn(credential, result.stdout)
        self.assertNotIn(PRIVATE_ADDRESS, result.stdout)
        self.assertNotIn('hiddenword', result.stdout)
        self.assertIn('credential', result.stdout)
        self.assertIn('private term', result.stdout)
