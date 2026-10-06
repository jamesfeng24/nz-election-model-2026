"""Bounded CI selection is conservative; behavioural discovery stays unchanged."""
import ast
from contextlib import redirect_stdout
from copy import deepcopy
import hashlib
from io import StringIO
import json
from pathlib import Path
import subprocess
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from scripts.validate import ci_selection as selection
from scripts.validate.ci_stage39 import simplex, verify as verify_stage39

ROOT = Path(__file__).resolve().parents[2]


def synthetic_registry():
    return {'version': 1, 'pipeline': 'stage39',
            'dependencies': {'scripts/shared.py': 'synthetic', 'requirements-boundaries.txt': 'synthetic',
                             'data/raw/required.csv': 'synthetic',
                             'data/processed/polling/candidate-integration/construction.json': 'synthetic'},
            'reviewedEditorialFiles': ['PROJECT_STATE.md'],
            'reviewedUnaffectedPrefixes': ['scripts/uncertainty_revision/',
                                          'data/processed/uncertainty-revision/', 'src/']}


class ConservativeSelectionTests(unittest.TestCase):
    def test_only_reviewed_unaffected_scopes_can_reuse_stage39(self):
        registry = synthetic_registry()
        for changed in (['docs/a.md'], ['PROJECT_STATE.md'], ['changelog.d/2026-10-06-x.md', 'state.d/2026-10-06-x.md'], ['src/App.tsx'],
                        ['scripts/uncertainty_revision/evaluation.py'],
                        ['data/processed/uncertainty-revision/evaluation.json'], []):
            with self.subTest(changed=changed):
                result = selection.select(changed, 'pull_request', registry)
                self.assertEqual(result['mode'], 'integrity')
                self.assertIn('behavioural tests remain full', result['reason'])

    def test_shared_raw_required_output_environment_and_unknown_paths_fail_full(self):
        for changed in ('scripts/shared.py', 'requirements-boundaries.txt',
                        'data/raw/required.csv',
                        'data/processed/polling/candidate-integration/construction.json',
                        'data/raw/unreviewed.csv', 'scripts/new_pipeline/run.py',
                        'data/processed/new-stage/result.json', 'package-lock.json',
                        'unknown.txt', 'docs/new-data.json', 'changelog.d/data.json', 'state.d/notes.txt'):
            with self.subTest(changed=changed):
                self.assertEqual(selection.select([changed], 'pull_request', synthetic_registry())['mode'], 'full')

    def test_ci_registry_checkpoint_policy_and_every_new_or_changed_test_fail_full(self):
        for changed in ('.github/workflows/ci.yml', '.github/validation/stage39.json',
                        'scripts/validate/ci_selection.py', 'AGENTS.md',
                        'scripts/tests/test_new_feature.py', 'scripts/tests/test_stage39_candidate_integration.py'):
            with self.subTest(changed=changed):
                self.assertEqual(selection.select([changed], 'pull_request', synthetic_registry())['mode'], 'full')

    def test_missing_history_invalid_fingerprint_and_non_pr_events_fail_full(self):
        for event in ('push', 'workflow_dispatch', 'schedule', 'unknown'):
            self.assertEqual(selection.select([], event, synthetic_registry())['mode'], 'full')
        self.assertEqual(selection.select([], 'pull_request', synthetic_registry(), history_available=False)['mode'], 'full')
        self.assertEqual(selection.select([], 'pull_request', synthetic_registry(), errors=['missing file'])['mode'], 'full')

    def test_explicit_full_mode(self):
        with patch('sys.argv', ['ci_selection', '--full']), redirect_stdout(StringIO()) as stdout:
            selection.main()
        self.assertEqual(json.loads(stdout.getvalue())['mode'], 'full')

    def test_mixed_changes_cannot_hide_a_protected_dependency(self):
        result = selection.select(['docs/explanation.md', 'scripts/shared.py'], 'pull_request', synthetic_registry())
        self.assertEqual(result['mode'], 'full')
        self.assertIn('scripts/shared.py', result['reason'])

    def test_invalid_registry_falls_back_to_full_github_output(self):
        with TemporaryDirectory(prefix='synthetic-ci-output-') as directory:
            output = Path(directory)/'github-output'
            with patch('sys.argv', ['ci_selection', '--event', 'pull_request', '--github-output', str(output)]), \
                    patch.object(selection, 'load_registry', side_effect=ValueError('synthetic corrupt JSON')), \
                    redirect_stdout(StringIO()) as stdout:
                selection.main()
            self.assertEqual(json.loads(stdout.getvalue())['mode'], 'full')
            self.assertEqual(output.read_text(), 'mode=full\n')

    def test_real_git_diff_and_missing_base_are_bounded_and_outcome_free(self):
        with TemporaryDirectory(prefix='synthetic-ci-git-') as directory:
            root = Path(directory)
            subprocess.run(['git', 'init', '-q'], cwd=root, check=True)
            (root/'a.md').write_text('first\n')
            def commit(message):
                subprocess.run(['git', 'add', '.'], cwd=root, check=True)
                subprocess.run(['git', '-c', 'user.name=Synthetic Fixture',
                                '-c', 'user.email=fixture@example.invalid', 'commit', '-qm', message], cwd=root, check=True)
            commit('synthetic baseline')
            base = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=root, text=True).strip()
            (root/'a.md').write_text('second\n')
            commit('synthetic change')
            self.assertEqual(selection.changed_paths(base, root), (['a.md'], True))
            self.assertEqual(selection.changed_paths('missing-ref', root), ([], False))
            self.assertEqual(selection.changed_paths('', root), ([], False))
            subprocess.run(['git', 'checkout', '--orphan', 'unrelated'], cwd=root, check=True,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            commit('synthetic disconnected history')
            self.assertEqual(selection.changed_paths(base, root), ([], False))


class EvidenceFingerprintTests(unittest.TestCase):
    def test_actual_attestation_is_prior_full_linux_evidence_not_new_output_assertion(self):
        registry = selection.load_registry()
        evidence = registry['attestation']
        self.assertEqual(evidence['head'], '5283e7c85bab23d31176c2160964672b5e0cca3f')
        log = (ROOT/evidence['evidencePath']).read_bytes()
        self.assertEqual(hashlib.sha256(log).hexdigest(), evidence['evidenceSha256'])
        for marker in evidence['requiredLogMarkers']:
            self.assertIn(marker, log.decode())
        self.assertIn('Ubuntu', log.decode())
        self.assertIn('3.12.2', log.decode())
        self.assertIn('requirements-boundaries.txt', registry['dependencies'])
        self.assertIn('scripts/polling/candidate_integration/propagation.py', registry['dependencies'])
        self.assertIn('data/processed/polling/candidate-integration/construction.json', registry['dependencies'])

    def test_missing_changed_dependency_and_evidence_fail_closed(self):
        with TemporaryDirectory(prefix='synthetic-ci-evidence-') as directory:
            root = Path(directory)
            (root/'evidence.log').write_text('validated head and completed Stage39\n')
            (root/'source.py').write_text('synthetic source\n')
            registry = {'version':1, 'pipeline':'stage39',
                        'attestation':{'evidencePath':'evidence.log',
                                       'evidenceSha256':hashlib.sha256((root/'evidence.log').read_bytes()).hexdigest(),
                                       'requiredLogMarkers':['validated head', 'completed Stage39']},
                        'dependencies':{'source.py':hashlib.sha256((root/'source.py').read_bytes()).hexdigest()}}
            self.assertEqual(selection.fingerprint_errors(registry, root), [])
            (root/'source.py').write_text('changed\n')
            self.assertIn('changed dependency: source.py', selection.fingerprint_errors(registry, root))
            (root/'source.py').unlink()
            self.assertIn('changed dependency: source.py', selection.fingerprint_errors(registry, root))
            (root/'evidence.log').write_text('new manifest says passed\n')
            self.assertIn('missing or changed prior Linux evidence', selection.fingerprint_errors(registry, root))

    def test_runtime_must_match_previously_validated_linux_environment(self):
        registry = selection.load_registry()
        with patch.dict(selection.os.environ, {'ImageVersion': '20260927.320.1'}), \
                patch.object(selection.sys, 'version', '3.12.2 synthetic'), \
                patch.object(selection.platform, 'system', return_value='Linux'), \
                patch.object(selection.platform, 'machine', return_value='x86_64'), \
                patch.object(selection.platform, 'freedesktop_os_release', return_value={'ID':'ubuntu', 'VERSION_ID':'24.04'}):
            self.assertEqual(selection.runtime_errors(registry), [])
            with patch.dict(selection.os.environ, {'ImageVersion': 'changed-image'}):
                self.assertIn('unattested runtime: imageVersion', selection.runtime_errors(registry))
            with patch.object(selection, 'version', return_value='unknown-version'):
                self.assertIn('unattested runtime: packages', selection.runtime_errors(registry))
            with patch.object(selection.sys, 'version', '3.13.0 synthetic'):
                self.assertIn('unattested runtime: python', selection.runtime_errors(registry))
            with patch.object(selection.platform, 'machine', return_value='aarch64'):
                self.assertIn('unattested runtime: machine', selection.runtime_errors(registry))
            with patch.object(selection.platform, 'freedesktop_os_release', return_value={'ID':'ubuntu', 'VERSION_ID':'26.04'}):
                self.assertIn('unattested runtime: osVersionId', selection.runtime_errors(registry))

    def test_completion_markers_and_nonempty_dependency_closure_are_required(self):
        with TemporaryDirectory(prefix='synthetic-ci-markers-') as directory:
            root = Path(directory)
            (root/'evidence.log').write_text('unvalidated\n')
            registry = {'version':1, 'pipeline':'stage39', 'dependencies':{},
                        'attestation':{'evidencePath':'evidence.log',
                                       'evidenceSha256':hashlib.sha256((root/'evidence.log').read_bytes()).hexdigest(),
                                       'requiredLogMarkers':['missing completion']}}
            errors = selection.fingerprint_errors(registry, root)
            self.assertIn('prior Linux evidence lacks required completion markers', errors)
            self.assertIn('unsupported or incomplete reviewed registry', errors)

    def test_inspected_semantic_registry_never_skips_behavioural_or_archival_tests(self):
        registry = json.loads((ROOT/'.github/validation/test-semantics.json').read_text())
        self.assertEqual(registry['default'], 'behavioural')
        self.assertEqual(registry['skipPolicy'], 'none; standard discovery remains full')
        kinds = set()
        for item in registry['entries']:
            source = (ROOT/item['file']).read_text()
            node = next(f for c in ast.parse(source).body if isinstance(c, ast.ClassDef) and c.name == item['class']
                        for f in c.body if isinstance(f, ast.FunctionDef) and f.name == item['method'])
            self.assertEqual(hashlib.sha256(ast.get_source_segment(source, node).encode()).hexdigest(),
                             item['methodSourceSha256'])
            self.assertEqual(item['execution'], 'always')
            kinds.add(item['classification'])
        self.assertEqual(kinds, {'behavioural', 'archival_reproduction_kept_full'})

    def test_actual_lightweight_path_never_reconstructs_historical_predictions(self):
        # The selection/fingerprint gate is tested independently above. This structural
        # adapter test must not make a legitimate future full run require the old
        # attestation to remain current after its dependencies have changed.
        with patch('scripts.validate.ci_stage39.fingerprint_errors', return_value=[]), \
                patch('scripts.polling.candidate_integration.construction.build',
                      side_effect=AssertionError('full prediction reconstruction is forbidden here')):
            result = verify_stage39()
        self.assertEqual(result['preservedFiles'], 1671)
        self.assertEqual(result['nationalVectors'], 48000)
        self.assertEqual(result['candidateCoordinates'], 7056)
        self.assertFalse(result['predictionReconstruction'])
        self.assertFalse(result['inference'])

    def test_complete_simplexes_reject_partial_or_invalid_inputs(self):
        simplex([.4, .6])
        for invalid in ([.4, .5], [-.1, 1.1], [float('nan'), 1], [1]):
            with self.assertRaises(ValueError):
                simplex(invalid)


class WorkflowCoverageTests(unittest.TestCase):
    def test_full_commands_jobs_permissions_and_manual_full_path_are_retained(self):
        original = subprocess.check_output(['git', 'show', '5283e7c85bab23d31176c2160964672b5e0cca3f:.github/workflows/ci.yml'], cwd=ROOT, text=True)
        current = (ROOT/'.github/workflows/ci.yml').read_text()
        for line in original.splitlines():
            if line.strip().startswith('- run:'):
                self.assertIn(line, current)
        for expected in ('  check:\n', '  python:\n', '  contents: read\n', '  workflow_dispatch:\n',
                         'cancel-in-progress: true', 'fetch-depth: 0',
                         'python3 -m unittest discover -s scripts/tests -v'):
            self.assertIn(expected, current)
        self.assertNotIn('schedule:', current)
        self.assertNotIn('actions/cache', current)
        for suffix in ('inventory', 'construction', 'evaluation', 'verification', 'report'):
            line = f'      - run: python3 -m scripts.polling.candidate_integration.{suffix} --check\n'
            self.assertIn(line+"        if: steps.stage39.outputs.mode != 'integrity'", current)


if __name__ == '__main__':
    unittest.main()
