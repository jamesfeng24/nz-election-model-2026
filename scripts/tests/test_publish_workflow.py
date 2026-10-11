"""Publish workflow: run mode, release ids, options, the independent archive and tree checks, the public-repository push (against a local bare
repository), and the shape of .github/workflows/publish.yml (stdlib only; no network)."""
import hashlib
import json
import re
import shutil
import subprocess
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from scripts.publish_workflow import plan, public, verify

ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = (ROOT / '.github/workflows/publish.yml').read_text(encoding='utf-8')
CODE = '\n'.join(line for line in WORKFLOW.splitlines() if not line.lstrip().startswith('#'))
EMPTY_INDEX = '{"schemaVersion": 1, "snapshots": []}'
CONFIG = json.loads((ROOT / 'config/nowcast-2026.json').read_text(encoding='utf-8'))


def steps():
    """The steps of the single job as (name, text) pairs."""
    body = CODE.split('    steps:\n', 1)[1]
    parts = re.split(r'\n      - (?=name:|uses:)', '\n' + body)
    return [(re.match(r'(?:name|uses): (.*)', p).group(1), p) for p in parts if p.strip()]


class ModeTests(unittest.TestCase):
    def test_nothing_publishes_without_an_explicit_go(self):
        self.assertEqual(plan.decide_mode('workflow_dispatch', 'false', '', 'refs/heads/main')[0], 'dry-run')
        self.assertEqual(plan.decide_mode('workflow_dispatch', '', 'true', 'refs/heads/main')[0], 'dry-run')   # the variable never applies to a manual run
        self.assertEqual(plan.decide_mode('push', '', '', 'refs/heads/main')[0], 'dry-run')
        self.assertEqual(plan.decide_mode('push', '', 'True ', 'refs/heads/main')[0], 'dry-run')               # exactly 'true'
        self.assertEqual(plan.decide_mode('push', 'true', 'yes', 'refs/heads/main')[0], 'dry-run')
        self.assertEqual(plan.decide_mode('schedule', 'true', 'true', 'refs/heads/main')[0], 'dry-run')
        self.assertEqual(plan.decide_mode('', '', '', '')[0], 'dry-run')

    def test_the_two_explicit_go_routes(self):
        self.assertEqual(plan.decide_mode('workflow_dispatch', 'true', '', 'refs/heads/main')[0], 'publish')
        self.assertEqual(plan.decide_mode('push', '', 'true', 'refs/heads/main')[0], 'publish')

    def test_publishing_from_another_ref_is_refused_not_downgraded(self):
        with self.assertRaises(plan.Refused):
            plan.decide_mode('workflow_dispatch', 'true', '', 'refs/heads/claude/x')
        self.assertEqual(plan.decide_mode('workflow_dispatch', 'false', '', 'refs/heads/claude/x')[0], 'dry-run')


class ReleaseTests(unittest.TestCase):
    def test_latest_refresh_on_the_repository(self):
        found = plan.latest_refresh()
        estimate = json.loads((ROOT / plan.WEEKLY / found['nationalDate'] / 'estimate.json').read_text())
        self.assertEqual(found['nationalCutoff'], estimate['nowcastInput']['dataCutoff'])
        self.assertEqual(found['releaseDate'], max(found['nationalCutoff'], found['electorateDate'] or found['nationalCutoff']))
        self.assertEqual(set(found), {'nationalDate', 'nationalCutoff', 'electorateDate', 'releaseDate'})

    def refresh_root(self, tmp, national, electorate):
        (Path(tmp) / plan.WEEKLY).mkdir(parents=True)
        (Path(tmp) / plan.WEEKLY / 'index.json').write_text(json.dumps({'runs': [{'date': d} for d in national]}))
        for d in national:
            (Path(tmp) / plan.WEEKLY / d).mkdir()
            (Path(tmp) / plan.WEEKLY / d / 'estimate.json').write_text(json.dumps({'nowcastInput': {'dataCutoff': d}}))
        if electorate is not None:
            (Path(tmp) / plan.electorate_live.LIVE).mkdir(parents=True)
            (Path(tmp) / plan.electorate_live.LIVE / 'index.json').write_text(json.dumps({'runs': [{'date': d} for d in electorate]}))

    def test_release_date_is_the_later_of_the_national_cutoff_and_the_newest_electorate_run(self):
        # a refresh with neither kind of new poll writes no run, so only new polls make a new forecast
        with tempfile.TemporaryDirectory() as tmp:
            self.refresh_root(tmp, ('2026-10-07', '2026-10-14'), None)
            self.assertEqual(plan.latest_refresh(tmp), {'nationalDate': '2026-10-14', 'nationalCutoff': '2026-10-14', 'electorateDate': None, 'releaseDate': '2026-10-14'})
        with tempfile.TemporaryDirectory() as tmp:
            self.refresh_root(tmp, ('2026-10-07', '2026-10-14'), ('2026-10-10', '2026-10-14'))      # both arrived on the 14th
            self.assertEqual(plan.latest_refresh(tmp)['releaseDate'], '2026-10-14')
        with tempfile.TemporaryDirectory() as tmp:
            self.refresh_root(tmp, ('2026-10-07', '2026-10-14'), ('2026-10-10',))                    # electorate polls older than the national run
            self.assertEqual(plan.latest_refresh(tmp)['releaseDate'], '2026-10-14')
        with tempfile.TemporaryDirectory() as tmp:
            self.refresh_root(tmp, ('2026-10-07', '2026-10-14'), ('2026-10-10', '2026-10-21'))      # only electorate polls on the 21st
            found = plan.latest_refresh(tmp)
            self.assertEqual(found, {'nationalDate': '2026-10-14', 'nationalCutoff': '2026-10-14', 'electorateDate': '2026-10-21', 'releaseDate': '2026-10-21'})
            # that is a new release (a new id) even though the national input is the same one as last week's
            self.assertEqual(plan.decide_work('publish', 'push', ['nowcast-2026-10-14'], found['releaseDate'])[:3], ('release', 'nowcast-2026-10-21', None))

    def test_the_publish_code_reads_no_electorate_poll(self):
        # only the model layers read the polls (test_electorate_refresh); the adoption pins the newest electorate-poll run itself. The planner reads
        # the run index for its date alone, through the one module that owns the file; the other publish files do not touch it at all.
        for name in ('verify.py', 'public.py'):
            text = (ROOT / 'scripts/publish_workflow' / name).read_text(encoding='utf-8')
            for needle in ('electorate' + '-live', 'electorate' + '_live'):          # spelled in two parts so this test is not itself a reader of the file
                self.assertNotIn(needle, text, name)
        planner = (ROOT / 'scripts/publish_workflow/plan.py').read_text(encoding='utf-8')
        self.assertNotIn('electorate' + '-live', planner)
        for call in ('.polls(', '.pinned(', '.live_rows(', 'polls.json'):
            self.assertNotIn(call, planner)

    def test_the_adopted_cutoff_is_read_from_the_configuration_not_from_the_national_input(self):
        adopt = next(text for name, text in steps() if name.startswith('Switch the configuration'))
        self.assertIn('scripts.publish_workflow.plan cutoff --expect "$RELEASE_DATE"', adopt)
        self.assertNotIn('.national.dataCutoff', CODE)          # an electorate-only release is dated after the national cutoff

    def test_a_release_with_new_polls_a_site_only_run_without_and_nothing_for_a_push_that_may_not_publish(self):
        # new national polls (a new data cutoff): a release, in either mode
        self.assertEqual(plan.decide_work('publish', 'push', ['nowcast-2026-10-05'], '2026-10-12')[:3], ('release', 'nowcast-2026-10-12', None))
        self.assertEqual(plan.decide_work('dry-run', 'workflow_dispatch', [], '2026-10-12')[:3], ('release', 'nowcast-2026-10-12', None))
        # no new polls: the live site only, with no new id
        self.assertEqual(plan.decide_work('publish', 'push', ['nowcast-2026-10-12'], '2026-10-12')[:3], ('site', None, None))
        self.assertEqual(plan.decide_work('publish', 'workflow_dispatch', ['nowcast-2026-10-12'], '2026-10-12')[:3], ('site', None, None))
        # a correction is a release again, with the same date
        self.assertEqual(plan.decide_work('publish', 'workflow_dispatch', ['nowcast-2026-10-12'], '2026-10-12', 'nowcast-2026-10-12')[:3],
                         ('release', 'nowcast-2026-10-12-r2', 'nowcast-2026-10-12'))
        # a push run that may not publish builds nothing, and a dry run never rebuilds a site it cannot compare with
        self.assertEqual(plan.decide_work('dry-run', 'push', [], '2026-10-12')[0], 'none')
        self.assertEqual(plan.decide_work('dry-run', 'workflow_dispatch', ['nowcast-2026-10-12'], '2026-10-12')[0], 'none')

    def test_snapshot_ids(self):
        self.assertEqual(plan.snapshot_id('2026-10-12', []), ('nowcast-2026-10-12', None))
        self.assertEqual(plan.snapshot_id('2026-10-12', ['nowcast-2026-10-05']), ('nowcast-2026-10-12', None))
        self.assertEqual(plan.snapshot_id('2026-10-12', ['nowcast-2026-10-12']), (None, None))               # already published: nothing to do
        self.assertEqual(plan.snapshot_id('2026-10-12', ['nowcast-2026-10-12'], 'nowcast-2026-10-12'), ('nowcast-2026-10-12-r2', 'nowcast-2026-10-12'))
        self.assertEqual(plan.snapshot_id('2026-10-12', ['nowcast-2026-10-12', 'nowcast-2026-10-12-r2'], 'nowcast-2026-10-12-r2'),
                         ('nowcast-2026-10-12-r3', 'nowcast-2026-10-12-r2'))
        with self.assertRaises(plan.Refused):
            plan.snapshot_id('2026-10-12', ['nowcast-2026-10-05'], 'nowcast-1999-01-01')
        with self.assertRaises(plan.Refused):           # a correction replaces a release of the newest data cutoff only (its frozen folder is named by that date)
            plan.snapshot_id('2026-10-12', ['nowcast-2026-10-05'], 'nowcast-2026-10-05')
        with self.assertRaises(plan.Refused):
            plan.snapshot_id('12 October', [])

    def test_existing_ids_read_an_index(self):
        self.assertEqual(plan.existing_ids(''), [])
        self.assertEqual(plan.existing_ids(json.dumps({'schemaVersion': 1, 'snapshots': [{'snapshotId': 'a'}, {'snapshotId': 'b'}]})), ['a', 'b'])

    def test_no_release_from_election_day_on(self):
        plan.election_guard('2026-11-02', CONFIG)
        for day in ('2026-11-07', '2026-11-09'):
            with self.assertRaises(plan.Refused):
                plan.election_guard(day, CONFIG)


class OptionsTests(unittest.TestCase):
    def options(self, now=None):
        return plan.build_options(CONFIG, 'nowcast-2026-10-10', '2026-10-10', 'abc123', now or datetime(2026, 10, 12, 0, 5, 3, 999, tzinfo=timezone.utc))

    def test_options_carry_the_configuration_and_the_required_fields(self):
        o = self.options()
        for key in ('snapshotId', 'createdAt', 'dataCutoff', 'electionId', 'electionDate', 'boundaryVersionId', 'modelVersion', 'codeRevision', 'mmp',
                    'nationalBasis', 'limitations', 'probabilityMcseMax'):
            self.assertIn(key, o)
        self.assertEqual(o['createdAt'], '2026-10-12T00:05:03+00:00')
        self.assertEqual(o['dataCutoff'], CONFIG['seatPolls']['pollCutoff'] + 'T00:00:00+00:00')
        self.assertEqual(o['mmp']['blocs'], CONFIG['mmp']['blocs'])
        self.assertEqual(o['mmp']['rulesVersion'], CONFIG['mmp']['rulesVersion'])
        self.assertEqual(o['probabilityMcseMax'], CONFIG['release']['probabilityMcseMax'])
        self.assertEqual(o['codeRevision'], 'abc123')
        self.assertTrue(o['limitations'])

    def test_an_electorate_only_release_is_dated_by_the_seat_polls_and_says_so(self):
        later = json.loads(json.dumps(CONFIG))
        later['seatPolls']['pollCutoff'] = '2026-10-21'
        o = plan.build_options(later, 'nowcast-2026-10-21', '2026-10-14', 'abc', datetime(2026, 10, 22, tzinfo=timezone.utc))
        self.assertEqual(o['dataCutoff'], '2026-10-21T00:00:00+00:00')
        self.assertIn(f"National polls to {CONFIG['national']['dataCutoff']}", o['nationalBasis'])
        self.assertIn('electorate polls to 2026-10-21', o['nationalBasis'])
        self.assertNotIn('electorate polls to', self.options()['nationalBasis'])          # a national release says nothing extra

    def test_a_cutoff_after_the_creation_time_is_refused(self):
        with self.assertRaises(plan.Refused):
            self.options(datetime(2026, 1, 1, tzinfo=timezone.utc))

    def test_nothing_in_the_options_looks_synthetic_or_names_a_tool(self):
        text = json.dumps(self.options()).lower()
        for word in ('synthetic', 'rehearsal', 'placeholder', 'unverified', 'claude', 'anthropic'):
            self.assertNotIn(word, text)

    def test_boundary_version_matches_the_rehearsal_and_is_a_real_id(self):
        self.assertIn(f"'{plan.BOUNDARY_VERSION_ID}'", (ROOT / 'scripts/release_rehearsal/run.py').read_text(encoding='utf-8'))

    def test_adoption_text(self):
        fragment = plan.adoption_fragment('nowcast-2026-10-12', '2026-10-12', '2026-10-12', None, '2026-10-12.1', 'abc')
        self.assertTrue(fragment.startswith('<!-- fold: changelog -->\n## Publish nowcast-2026-10-12 — 2026-10-12'))
        title, body = plan.adoption_pr('nowcast-2026-10-12', '2026-10-12', '2026-10-12', '2026-10-12', '2026-10-12.1', 'abc', 'https://example.test/run/1')
        self.assertTrue(title.startswith('Polls: '))
        for heading in ('## Scope', '## Changes and limits', '## Decisions recorded', '## Local validation', '## CI and boundaries', '## Final published head and hosted validation'):
            self.assertIn(heading, body)


def snapshot_for(snapshot_id, cutoff, kind='model'):
    return {'schemaVersion': 2, 'snapshotId': snapshot_id, 'targetType': 'nowcast', 'dataCutoff': cutoff + 'T00:00:00+00:00', 'provenance': {'kind': kind}}


def write_release(archive, snapshot_id, cutoff, supersedes=None, kind='model'):
    """Append one release to an archive directory, as the TypeScript publisher does."""
    archive = Path(archive)
    text = json.dumps(snapshot_for(snapshot_id, cutoff, kind), sort_keys=True)
    (archive / snapshot_id).mkdir(parents=True, exist_ok=True)
    (archive / snapshot_id / 'snapshot.json').write_text(text)
    index = json.loads((archive / 'index.json').read_text()) if (archive / 'index.json').exists() else {'schemaVersion': 1, 'snapshots': []}
    index['snapshots'].append({'snapshotId': snapshot_id, 'createdAt': cutoff + 'T01:00:00+00:00', 'dataCutoff': cutoff + 'T00:00:00+00:00', 'provenanceKind': kind,
                               'path': snapshot_id + '/snapshot.json', 'sha256': hashlib.sha256(text.encode()).hexdigest(), 'supersedes': supersedes, 'status': 'published',
                               'withdrawnReason': None})
    (archive / 'index.json').write_text(json.dumps(index, sort_keys=True))


class ArchiveCheckTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.prev, self.new = self.tmp / 'prev', self.tmp / 'new'
        self.prev.mkdir()
        write_release(self.prev, 'nowcast-2026-10-05', '2026-10-05')
        shutil.copytree(self.prev, self.new)
        write_release(self.new, 'nowcast-2026-10-12', '2026-10-12')

    def check(self, **kw):
        args = dict(new_dir=self.new, previous_dir=self.prev, snapshot_id='nowcast-2026-10-12', cutoff='2026-10-12')
        args.update(kw)
        return verify.check_archive(**args)

    def test_a_clean_append_passes(self):
        self.assertEqual(self.check(), [])

    def test_first_release_into_an_empty_archive(self):
        first = self.tmp / 'first'
        first.mkdir()
        write_release(first, 'nowcast-2026-10-12', '2026-10-12')
        self.assertEqual(verify.check_archive(first, None, 'nowcast-2026-10-12', '2026-10-12'), [])

    def test_a_correction_must_say_what_it_supersedes(self):
        write_release(self.new, 'nowcast-2026-10-12-r2', '2026-10-12', supersedes='nowcast-2026-10-12')
        # the 10-12 release is itself new here, so build the realistic case: previous holds it
        shutil.rmtree(self.new)
        shutil.copytree(self.prev, self.new)
        write_release(self.prev, 'nowcast-2026-10-12', '2026-10-12')
        shutil.rmtree(self.new)
        shutil.copytree(self.prev, self.new)
        write_release(self.new, 'nowcast-2026-10-12-r2', '2026-10-12', supersedes='nowcast-2026-10-12')
        self.assertEqual(self.check(snapshot_id='nowcast-2026-10-12-r2', supersedes='nowcast-2026-10-12'), [])
        self.assertTrue(self.check(snapshot_id='nowcast-2026-10-12-r2'))

    def test_changing_an_earlier_release_is_caught(self):
        (self.new / 'nowcast-2026-10-05' / 'snapshot.json').write_text('{"tampered": true}')
        self.assertTrue(any('hash' in e for e in self.check()))

    def test_rewriting_an_earlier_index_entry_is_caught(self):
        index = json.loads((self.new / 'index.json').read_text())
        index['snapshots'][0]['status'] = 'withdrawn'
        (self.new / 'index.json').write_text(json.dumps(index))
        self.assertTrue(any('append-only' in e for e in self.check()))

    def test_dropping_an_earlier_release_is_caught(self):
        index = json.loads((self.new / 'index.json').read_text())
        index['snapshots'] = index['snapshots'][1:]
        (self.new / 'index.json').write_text(json.dumps(index))
        self.assertTrue(self.check())

    def test_synthetic_releases_are_refused(self):
        bad = self.tmp / 'bad'
        shutil.copytree(self.prev, bad)
        write_release(bad, 'synthetic-rehearsal-2026-10-12', '2026-10-12', kind='synthetic-fixture')
        self.assertTrue(verify.check_archive(bad, self.prev, 'synthetic-rehearsal-2026-10-12', '2026-10-12'))

    def test_stray_directories_files_and_extra_releases_are_caught(self):
        (self.new / 'rehearsal').mkdir()
        self.assertTrue(any('stray' in e for e in self.check()))
        shutil.rmtree(self.new / 'rehearsal')
        (self.new / 'notes.txt').write_text('x')
        self.assertTrue(any('Unexpected files' in e for e in self.check()))
        (self.new / 'notes.txt').unlink()
        write_release(self.new, 'nowcast-2026-10-13', '2026-10-13')
        self.assertTrue(any('exactly one new entry' in e for e in self.check()))

    def test_a_site_only_run_adds_nothing(self):
        self.assertEqual(verify.check_archive(self.prev, self.prev, None, ''), [])
        self.assertTrue(any('no new entry' in e for e in verify.check_archive(self.new, self.prev, None, '')))

    def test_two_current_forecasts_with_the_same_cutoff_date_are_refused(self):
        write_release(self.new, 'nowcast-2026-10-12-x', '2026-10-12')
        self.assertTrue(any('share a data cutoff date' in e for e in self.check()))

    def test_wrong_cutoff_or_id_is_caught(self):
        self.assertTrue(any('data cutoff' in e for e in self.check(cutoff='2026-10-11')))
        self.assertTrue(self.check(snapshot_id='nowcast-2026-10-19'))


class TreeCheckTests(unittest.TestCase):
    PAGES = ['forecast', 'polls']

    def make(self, tmp):
        site = Path(tmp)
        for rel in ('index.html', '404.html', 'forecasts/index.json', 'forecast/index.html', 'polls/index.html', 'assets/app.js'):
            (site / rel).parent.mkdir(parents=True, exist_ok=True)
            (site / rel).write_text('x')
        return site

    def test_clean_tree_and_each_failure(self):
        with tempfile.TemporaryDirectory() as tmp:
            site = self.make(tmp)
            self.assertEqual(verify.check_tree(site, self.PAGES), [])
            (site / 'polls/index.html').unlink()
            self.assertTrue(verify.check_tree(site, self.PAGES))
            (site / 'polls/index.html').write_text('x')
            for bad in ('assets/app.js.map', 'README.md', '.DS_Store', 'assets/synthetic-data.json'):
                (site / bad).write_text('x')
                self.assertTrue(verify.check_tree(site, self.PAGES), bad)
                (site / bad).unlink()

    def test_pages_are_read_from_the_site_source_when_present(self):
        if all((ROOT / p).is_file() for p in plan.SITE_FILES):         # the site code (PR #108) is on this ref
            self.assertIn('forecast', verify.site_pages(ROOT))


class FrozenCheckTests(unittest.TestCase):
    def make(self, tmp, days=('2026-10-05', '2026-10-12'), folders=None):
        tree = Path(tmp)
        (tree / 'forecasts').mkdir(parents=True)
        for d in days:
            write_release(tree / 'forecasts', 'nowcast-' + d, d)
        for d in (days if folders is None else folders):
            for rel in ('index.html', 'forecast/index.html', 'forecasts/index.json'):
                (tree / 'archive' / d / rel).parent.mkdir(parents=True, exist_ok=True)
                (tree / 'archive' / d / rel).write_text(d)
        return tree

    def test_every_current_forecast_has_its_frozen_copy_and_nothing_else_does(self):
        with tempfile.TemporaryDirectory() as tmp:
            tree = self.make(tmp)
            self.assertEqual(verify.check_frozen(tree), [])
            shutil.rmtree(tree / 'archive/2026-10-05')
            self.assertTrue(any('2026-10-05' in e for e in verify.check_frozen(tree)))
            self.make(tmp + '/x', days=('2026-10-12',), folders=('2026-10-12', '2026-10-01'))
            self.assertTrue(any('belongs to no current forecast' in e for e in verify.check_frozen(Path(tmp) / 'x')))

    def test_a_corrected_release_keeps_one_folder_and_an_incomplete_copy_is_caught(self):
        with tempfile.TemporaryDirectory() as tmp:
            tree = self.make(tmp, days=('2026-10-12',))
            write_release(tree / 'forecasts', 'nowcast-2026-10-12-r2', '2026-10-12', supersedes='nowcast-2026-10-12')
            self.assertEqual(verify.check_frozen(tree), [])
            (tree / 'archive/2026-10-12/forecasts/index.json').unlink()
            self.assertTrue(any('incomplete' in e for e in verify.check_frozen(tree)))


def git(cwd, *args):
    return subprocess.run(['git', *args], cwd=cwd, check=True, capture_output=True, text=True).stdout.strip()


class PublicPushTests(unittest.TestCase):
    """The push logic against a local bare repository standing in for the public one (no network, no token)."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.remote = self.tmp / 'remote.git'
        subprocess.run(['git', 'init', '-q', '--bare', '--initial-branch=main', str(self.remote)], check=True)
        self.url = self.remote.as_uri()
        self.site = self.tmp / 'site'
        for rel, text in (('index.html', 'home'), ('404.html', 'nf'), ('forecast/index.html', 'f'), ('forecasts/index.json', EMPTY_INDEX), ('assets/a.js', 'js')):
            (self.site / rel).parent.mkdir(parents=True, exist_ok=True)
            (self.site / rel).write_text(text)

    def publish(self, message='Update forecast 2026-10-12', site=None):
        clone = self.tmp / ('clone-%d' % len(list(self.tmp.glob('clone-*'))))
        head = public.preflight(clone, self.tmp / 'archive', self.url)
        public.sync_tree(site or self.site, clone)
        return public.commit_and_push(clone, message, self.url, expected_head=head), clone

    def test_first_publish_into_an_empty_repository(self):
        result, _ = self.publish()
        self.assertEqual(result, 'pushed')
        check = self.tmp / 'check'
        subprocess.run(['git', 'clone', '-q', self.url, str(check)], check=True)
        self.assertEqual(git(check, 'log', '-1', '--format=%an|%ae|%cn|%ce|%B').rstrip(), 'jamesfeng24|233003834+jamesfeng24@users.noreply.github.com|jamesfeng24|233003834+jamesfeng24@users.noreply.github.com|Update forecast 2026-10-12')
        self.assertEqual(git(check, 'rev-list', '--count', 'HEAD'), '1')
        raw = git(check, 'cat-file', '-p', 'HEAD')
        for forbidden in ('gpgsig', 'Co-authored', 'Co-Authored', 'Signed-off', 'Claude'):
            self.assertNotIn(forbidden, raw)
        self.assertEqual(sorted(p.name for p in check.iterdir() if p.name != '.git'), ['.nojekyll', '404.html', 'README.md', 'assets', 'forecast', 'forecasts', 'index.html'])
        readme = (check / 'README.md').read_text()
        for word in ('claude', 'anthropic', 'generated by'):
            self.assertNotIn(word, readme.lower())

    def frozen_site(self, name='2026-10-12', text='frozen'):
        frozen = self.tmp / ('frozen-' + name)
        shutil.rmtree(frozen, True)
        for rel in ('index.html', 'forecast/index.html', 'forecasts/index.json'):
            (frozen / rel).parent.mkdir(parents=True, exist_ok=True)
            (frozen / rel).write_text(text)
        return frozen

    def index_site(self, *days):
        """The built live site whose archive index lists the releases of `days`."""
        shutil.rmtree(self.site / 'forecasts', True)
        (self.site / 'forecasts').mkdir(parents=True)
        for d in days:
            write_release(self.site / 'forecasts', 'nowcast-' + d, d)

    def publish_with_frozen(self, name, text='frozen', message='Update forecast', correction=False):
        clone = self.tmp / ('clone-%d' % len(list(self.tmp.glob('clone-*'))))
        head = public.preflight(clone, self.tmp / 'archive', self.url)
        public.sync_tree(self.site, clone, self.frozen_site(name, text), name, correction)
        return public.commit_and_push(clone, message, self.url, expected_head=head), clone

    def clone_of_remote(self):
        check = self.tmp / ('check-%d' % len(list(self.tmp.glob('check-*'))))
        subprocess.run(['git', 'clone', '-q', self.url, str(check)], check=True)
        return check

    def test_frozen_copies_are_written_once_and_never_touched_by_later_publishes(self):
        self.index_site('2026-10-05')
        self.assertEqual(self.publish_with_frozen('2026-10-05', 'week one')[0], 'pushed')
        self.index_site('2026-10-05', '2026-10-12')
        (self.site / 'assets/a.js').write_text('js v2')
        self.assertEqual(self.publish_with_frozen('2026-10-12', 'week two')[0], 'pushed')
        check = self.clone_of_remote()
        self.assertEqual((check / 'archive/2026-10-05/index.html').read_text(), 'week one')
        self.assertEqual((check / 'archive/2026-10-12/index.html').read_text(), 'week two')
        self.assertEqual((check / 'assets/a.js').read_text(), 'js v2')
        # a site-only publish (no frozen copy, a changed live site) rewrites the live root and leaves every frozen copy as it was
        (self.site / 'index.html').write_text('new design')
        (self.site / 'archive').mkdir()
        (self.site / 'archive/index.html').write_text('archive page v2')
        clone = self.tmp / 'clone-site'
        head = public.preflight(clone, self.tmp / 'archive3', self.url)
        public.sync_tree(self.site, clone)
        self.assertEqual(public.commit_and_push(clone, 'Update site 2026-10-14', self.url, expected_head=head), 'pushed')
        check = self.clone_of_remote()
        self.assertEqual((check / 'index.html').read_text(), 'new design')
        self.assertEqual((check / 'archive/index.html').read_text(), 'archive page v2')
        self.assertEqual((check / 'archive/2026-10-05/index.html').read_text(), 'week one')
        self.assertEqual((check / 'archive/2026-10-12/index.html').read_text(), 'week two')

    def test_a_site_only_publish_with_nothing_changed_pushes_nothing(self):
        self.index_site('2026-10-05')
        self.publish_with_frozen('2026-10-05')
        clone = self.tmp / 'clone-same'
        head = public.preflight(clone, self.tmp / 'archive4', self.url)
        public.sync_tree(self.site, clone)
        self.assertEqual(public.commit_and_push(clone, 'Update site 2026-10-14', self.url, expected_head=head), 'unchanged')

    def test_a_frozen_copy_is_replaced_only_for_a_correction_of_that_date(self):
        self.index_site('2026-10-05')
        self.publish_with_frozen('2026-10-05', 'first')
        clone = self.tmp / 'clone-again'
        public.preflight(clone, self.tmp / 'archive5', self.url)
        with self.assertRaises(public.PublicError) as caught:
            public.sync_tree(self.site, clone, self.frozen_site('2026-10-05', 'second'), '2026-10-05')
        self.assertIn('already exists', str(caught.exception))
        write_release(self.site / 'forecasts', 'nowcast-2026-10-05-r2', '2026-10-05', supersedes='nowcast-2026-10-05')
        self.assertEqual(self.publish_with_frozen('2026-10-05', 'corrected', correction=True)[0], 'pushed')
        self.assertEqual((self.clone_of_remote() / 'archive/2026-10-05/index.html').read_text(), 'corrected')

    def test_a_publish_that_would_leave_a_current_forecast_without_a_frozen_copy_is_refused(self):
        self.index_site('2026-10-05', '2026-10-12')           # two current forecasts, one frozen copy offered
        clone = self.tmp / 'clone-bad'
        public.preflight(clone, self.tmp / 'archive6', self.url)
        with self.assertRaises(public.PublicError) as caught:
            public.sync_tree(self.site, clone, self.frozen_site('2026-10-12'), '2026-10-12')
        self.assertIn('archive/2026-10-05/', str(caught.exception))

    def test_a_frozen_copy_needs_a_date_and_the_live_build_may_not_carry_dated_folders(self):
        clone = self.tmp / 'clone-args'
        public.preflight(clone, self.tmp / 'archive7', self.url)
        with self.assertRaises(public.PublicError):
            public.sync_tree(self.site, clone, self.frozen_site(), None)
        with self.assertRaises(public.PublicError):
            public.sync_tree(self.site, clone, self.frozen_site('x'), 'yesterday')
        (self.site / 'archive/2026-10-05').mkdir(parents=True)
        with self.assertRaises(public.PublicError):
            public.sync_tree(self.site, clone)

    def test_an_unchanged_site_pushes_nothing(self):
        self.publish()
        result, _ = self.publish(message='Update forecast 2026-10-19')
        self.assertEqual(result, 'unchanged')

    def test_second_publish_adds_a_commit_and_replaces_stale_files(self):
        self.publish()
        (self.site / 'assets/a.js').unlink()
        (self.site / 'assets/b.js').write_text('js2')
        (self.site / 'forecasts/index.json').write_text(EMPTY_INDEX.replace('}', ', "n": 2}'))
        result, _ = self.publish(message='Update forecast 2026-10-19')
        self.assertEqual(result, 'pushed')
        check = self.tmp / 'check'
        subprocess.run(['git', 'clone', '-q', self.url, str(check)], check=True)
        self.assertEqual(git(check, 'rev-list', '--count', 'HEAD'), '2')
        self.assertFalse((check / 'assets/a.js').exists())
        self.assertEqual((check / 'assets/b.js').read_text(), 'js2')

    def test_files_the_site_build_adds_at_the_top_level_are_owned_not_stray(self):
        # public/ files (icons, share card) are copied to the root by the build; a later publish must not mistake them for someone else's files
        research = self.tmp / 'research'
        (research / 'public/fonts').mkdir(parents=True)
        (research / 'public/favicon.svg').write_text('x')
        (research / 'public/social-card.png').write_text('x')
        (research / 'forecast').mkdir()
        (research / 'forecast/index.html').write_text('x')
        (research / 'src').mkdir()
        names = public.expected_site_names(research)
        self.assertTrue({'favicon.svg', 'social-card.png', 'fonts', 'forecast', 'index.html', 'assets'} <= names)
        self.assertNotIn('src', names)
        site = self.tmp / 'site-icons'
        shutil.copytree(self.site, site)
        (site / 'favicon.svg').write_text('icon')
        (site / 'social-card.png').write_text('card')
        self.publish(site=site)
        clone = self.tmp / 'second'
        with self.assertRaises(public.PublicError):                  # not known before the build: refused ...
            public.preflight(clone, self.tmp / 'a1', self.url)
        shutil.rmtree(clone)
        public.preflight(clone, self.tmp / 'a2', self.url, site_names=names)   # ... known from the research checkout: accepted

    def test_the_archive_is_read_back_from_the_public_repository(self):
        self.publish()
        clone = self.tmp / 'again'
        public.preflight(clone, self.tmp / 'archive2', self.url)
        self.assertEqual((self.tmp / 'archive2' / 'index.json').read_text(), EMPTY_INDEX)

    def test_unexpected_files_stop_the_run_before_anything_is_deleted(self):
        seed = self.tmp / 'seed'
        subprocess.run(['git', 'clone', '-q', self.url, str(seed)], check=True, capture_output=True)
        (seed / 'LICENSE').write_text('mit')
        git(seed, 'checkout', '-q', '-B', 'main')
        git(seed, '-c', 'user.name=x', '-c', 'user.email=x@x', 'add', '-A')
        git(seed, '-c', 'user.name=x', '-c', 'user.email=x@x', 'commit', '-q', '-m', 'seed')
        git(seed, 'push', '-q', 'origin', 'main')
        with self.assertRaises(public.PublicError) as caught:
            public.preflight(self.tmp / 'c', self.tmp / 'a', self.url)
        self.assertIn('LICENSE', str(caught.exception))

    def test_a_change_to_the_public_repository_during_the_build_refuses_the_push(self):
        clone = self.tmp / 'clone-x'
        self.publish()
        head = public.preflight(clone, self.tmp / 'archive', self.url)
        other = self.tmp / 'other'
        subprocess.run(['git', 'clone', '-q', self.url, str(other)], check=True, capture_output=True)
        (other / 'extra.txt').write_text('x')
        git(other, '-c', 'user.name=x', '-c', 'user.email=x@x', 'add', '-A')
        git(other, '-c', 'user.name=x', '-c', 'user.email=x@x', 'commit', '-q', '-m', 'someone else')
        git(other, 'push', '-q', 'origin', 'main')
        (self.site / 'index.html').write_text('changed')
        public.sync_tree(self.site, clone)
        with self.assertRaises(public.PublicError):
            public.commit_and_push(clone, 'Update forecast 2026-10-19', self.url, expected_head=head)
        self.assertEqual(git(self.remote, 'log', '-1', '--format=%s', 'main'), 'someone else')

    def test_a_repository_on_another_branch_is_refused(self):
        seed = self.tmp / 'seed'
        subprocess.run(['git', 'clone', '-q', self.url, str(seed)], check=True, capture_output=True)
        (seed / 'README.md').write_text('x')
        git(seed, 'checkout', '-q', '-B', 'gh-pages')
        git(seed, '-c', 'user.name=x', '-c', 'user.email=x@x', 'add', '-A')
        git(seed, '-c', 'user.name=x', '-c', 'user.email=x@x', 'commit', '-q', '-m', 'seed')
        git(seed, 'push', '-q', 'origin', 'gh-pages')
        git(self.remote, 'symbolic-ref', 'HEAD', 'refs/heads/gh-pages')
        with self.assertRaises(public.PublicError):
            public.preflight(self.tmp / 'c', self.tmp / 'a', self.url)

    def test_the_token_is_a_header_and_is_masked(self):
        args = public.header_args('s3cret')
        self.assertEqual(args[0], '-c')
        self.assertNotIn('s3cret', ' '.join(args))
        self.assertEqual(public.header_args(''), [])
        self.assertEqual(public.scrub('x s3cret y ' + args[1].split('basic ')[1], 's3cret'), 'x *** y ***')

    def test_only_publish_branches_may_be_pushed_to_the_research_repository(self):
        with self.assertRaises(public.PublicError):
            public.push_branch('main')


class WorkflowShapeTests(unittest.TestCase):
    def test_triggers(self):
        self.assertIn('workflow_dispatch:', CODE)
        self.assertRegex(CODE, r'publish:\n\s+description:[^\n]*\n\s+required: false\n\s+type: boolean\n\s+default: false')
        self.assertIn('data/processed/polling/weekly-refresh/index.json', CODE)
        for site_path in ('src/**', 'public/**', "'*/index.html'", 'vite.config.ts', 'package-lock.json'):       # a site-only change republishes the live root
            self.assertIn(site_path, CODE)
        self.assertIn("'!src/release/**'", CODE)
        self.assertNotIn('pull_request', CODE)
        self.assertNotIn('schedule:', CODE)

    def test_limits_and_permissions(self):
        self.assertIn('permissions:\n  contents: read', CODE)
        self.assertLessEqual(int(re.search(r'timeout-minutes: (\d+)', CODE).group(1)), 180)
        self.assertIn('cancel-in-progress: false', CODE)
        self.assertIn('persist-credentials: false', CODE)

    def test_the_token_reaches_only_publish_mode_steps(self):
        for name, text in steps():
            if 'secrets.POLL_REFRESH_TOKEN' in text:
                self.assertIn("steps.mode.outputs.mode == 'publish'", text, name)
        self.assertEqual(sum('secrets.POLL_REFRESH_TOKEN' in t for _, t in steps()) >= 4, True)

    def test_the_token_is_not_used_by_checkout_or_the_build(self):
        for name, text in steps():
            if any(k in text for k in ('actions/checkout', 'npm ', 'nowcast_assembly.run --require-complete', 'weekly_refresh.adopt')):
                self.assertNotIn('secrets.', text, name)

    def test_nothing_forces_or_rewrites_history_or_names_the_public_repo(self):
        for forbidden in ('--force', '-f origin', 'push -f', 'reset --hard', 'jamesfeng24.github.io', 'Co-Authored-By', 'Generated by'):
            self.assertNotIn(forbidden, WORKFLOW, forbidden)

    def test_the_dry_run_path_never_reads_or_writes_the_public_repository(self):
        for name, text in steps():
            if 'scripts.publish_workflow.public' in text:
                self.assertIn("steps.mode.outputs.mode == 'publish'", text, name)

    def test_publication_gates_run_before_any_push_and_the_push_is_last_but_bookkeeping(self):
        order = [name for name, _ in steps()]
        position = {key: next(i for i, n in enumerate(order) if key in n) for key in
                    ('Production run', 'Release gate and archive', 'Build the site and check', 'Build the frozen copy', 'Push the adoption branch', 'Push to the public repository',
                     'Open the adoption')}
        self.assertLess(position['Production run'], position['Release gate and archive'])
        self.assertLess(position['Release gate and archive'], position['Build the site and check'])
        self.assertLess(position['Build the site and check'], position['Build the frozen copy'])
        self.assertLess(position['Build the frozen copy'], position['Push the adoption branch'])
        self.assertLess(position['Push the adoption branch'], position['Push to the public repository'])
        self.assertLess(position['Push to the public repository'], position['Open the adoption'])
        self.assertEqual(order[-1][:4], 'Open')
        adoption = dict(steps())[order[-1]]
        self.assertIn('continue-on-error: true', adoption)       # bookkeeping after the fact cannot fail a published run
        self.assertIn("vars.ADOPTION_PR == 'true'", adoption)     # off by default: the weekly run stays lean

    def test_the_release_chain_runs_only_for_a_release_and_the_site_build_never_for_nothing(self):
        for name, text in steps():
            if name.startswith(('Switch', 'Development', 'Build the site evidence', 'Production', 'Release gate', 'Build the frozen copy', 'Push the adoption', 'Open')):
                self.assertIn("steps.release.outputs.work == 'release'", text, name)
            if name.startswith(('Build the site and check', 'Push to the public repository')):
                self.assertIn("steps.release.outputs.work != 'none'", text, name)
        self.assertNotIn('outputs.skip', CODE)

    def test_a_site_only_publish_adds_no_forecast_and_no_frozen_copy(self):
        text = dict(steps())['Push to the public repository']
        self.assertIn('--frozen site-archived --frozen-name "$CUTOFF"', text)
        self.assertIn('if [ "$WORK" = release ]', text)
        self.assertLess(text.index('if [ "$WORK" = release ]'), text.index('--frozen'))
        self.assertIn('--no-new', dict(steps())['Put the published archive in place (site-only)'])
        self.assertIn("steps.release.outputs.work == 'site'", dict(steps())['Put the published archive in place (site-only)'])

    def test_the_frozen_copy_is_built_checked_and_never_rebuilt_in_place(self):
        text = dict(steps())['Build the frozen copy of the site for this week (release)']
        self.assertIn('SITE_ARCHIVE_DATE="$CUTOFF" SITE_OUT_DIR=site-archived npm run build', text)
        self.assertIn('no_synthetic_in_dist.mjs site-archived', text)
        self.assertIn('check_site.mjs site-archived', text)
        self.assertIn('--correction', dict(steps())['Push to the public repository'])

    def test_logs_print_no_forecast_numbers(self):
        # public logs: no step prints or summarises seats, probabilities or shares
        for word in ('seats by party', 'median', 'P(majority)', 'probability'):
            self.assertNotIn(word, CODE.lower().replace('probabilitymcse', ''))

    def test_the_site_is_not_edited_by_this_workflow(self):
        self.assertNotIn('src/app', CODE)


class SelectorExemptionTests(unittest.TestCase):
    def test_the_publish_workflow_is_a_non_verify_workflow(self):
        from scripts.validate import ci_frozen
        self.assertIn('.github/workflows/publish.yml', ci_frozen.NON_VERIFY_WORKFLOWS)
        self.assertNotIn('publish.yml', (ROOT / '.github/workflows/ci.yml').read_text(encoding='utf-8'))


if __name__ == '__main__':
    unittest.main()
