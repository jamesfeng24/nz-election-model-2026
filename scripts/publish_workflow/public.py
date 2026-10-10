"""The only code that reads or writes the public site repository (jamesfeng24/jamesfeng24.github.io), for the Publish workflow.

    python3 -m scripts.publish_workflow.public preflight --clone DIR --archive-to DIR --head-file PATH
    python3 -m scripts.publish_workflow.public push --clone DIR --site DIR --message TEXT --expected-head SHA
    python3 -m scripts.publish_workflow.public push-branch --branch NAME

The token comes from the environment (PUBLISH_TOKEN, James's POLL_REFRESH_TOKEN secret) and is sent as a request header for each git command only;
it is never written into a remote URL or a git config, and it is masked in anything printed. Commits to the public repository carry James's
public GitHub identity as author and committer and no trailers. Nothing is ever force-pushed. A dry run of the workflow never calls this module.
"""
import argparse
import base64
import os
import shutil
import subprocess
import sys
from pathlib import Path

PUBLIC_REPO = 'jamesfeng24/jamesfeng24.github.io'
PUBLIC_BRANCH = 'main'
AUTHOR_NAME = 'jamesfeng24'
AUTHOR_EMAIL = '233003834+jamesfeng24@users.noreply.github.com'
README_TEMPLATE = Path(__file__).with_name('public-README.md')
# Kept when the tree is replaced.
KEEP = {'.git', 'CNAME'}
# Everything the public repository may contain besides the built site: the entries a publish itself writes. Any other top-level entry stops the
# run before it deletes anything, so James decides about it (a LICENSE file, notes, a forgotten folder).
OWNED = {'README.md', '.nojekyll', 'index.html', '404.html', 'forecast', 'electorates', 'polls', 'methodology', 'archive', 'about', 'forecasts',
         'assets', 'fonts', 'data'}


class PublicError(Exception):
    pass


def header_args(token):
    """git -c arguments that authenticate one command without storing the token anywhere."""
    if not token:
        return []
    basic = base64.b64encode(f'x-access-token:{token}'.encode()).decode()
    return ['-c', f'http.extraheader=AUTHORIZATION: basic {basic}']


def scrub(text, token):
    if token:
        basic = base64.b64encode(f'x-access-token:{token}'.encode()).decode()
        text = text.replace(token, '***').replace(basic, '***')
    return text


def git(args, cwd=None, token=None, identity=False, check=True):
    env = dict(os.environ, GIT_TERMINAL_PROMPT='0')
    if identity:
        # A commit made here is plain: no signature, hooks or templates from a machine's global git configuration.
        args = ['-c', 'commit.gpgsign=false', '-c', 'tag.gpgsign=false', '-c', 'core.hooksPath=/dev/null', '-c', 'commit.template='] + args
    if identity:
        env.update(GIT_AUTHOR_NAME=AUTHOR_NAME, GIT_AUTHOR_EMAIL=AUTHOR_EMAIL, GIT_COMMITTER_NAME=AUTHOR_NAME, GIT_COMMITTER_EMAIL=AUTHOR_EMAIL)
    run = subprocess.run(['git'] + header_args(token) + args, cwd=cwd, env=env, capture_output=True, text=True)
    if check and run.returncode != 0:
        raise PublicError(scrub(f"git {' '.join(args[:2])} failed: {run.stderr.strip() or run.stdout.strip()}", token))
    return run


def head_of(clone):
    run = git(['rev-parse', '-q', '--verify', 'HEAD'], cwd=clone, check=False)
    return run.stdout.strip() or None


def unexpected_entries(directory, site_names=()):
    """Top-level entries of `directory` that neither the site nor a publish owns."""
    allowed = KEEP | OWNED | set(site_names)
    return sorted(p.name for p in Path(directory).iterdir() if p.name not in allowed)


def preflight(clone, archive_to, remote, token=None, head_file=None):
    """Clone the public repository, confirm the branch, the contents and the token's right to push, and copy its release archive to `archive_to`.

    Returns the commit the archive was read from (None for an empty repository). Pushes nothing.
    """
    clone = Path(clone)
    git(['clone', '--quiet', '--depth', '1', remote, str(clone)], token=token)
    head = head_of(clone)
    if head:
        branch = git(['symbolic-ref', '--short', 'HEAD'], cwd=clone).stdout.strip()
        if branch != PUBLIC_BRANCH:
            raise PublicError(f'The public repository is on branch {branch}; GitHub Pages must deploy from {PUBLIC_BRANCH}')
    extra = unexpected_entries(clone)
    if extra:
        raise PublicError('The public repository holds entries a publish does not own: ' + ', '.join(extra) + '. Remove them, or ask for them to be allowed, then run again.')
    probe = clone
    if not head:
        git(['checkout', '-q', '-B', PUBLIC_BRANCH], cwd=probe)
        git(['commit', '-q', '--allow-empty', '-m', 'probe'], cwd=probe, identity=True)
    # A dry-run push is accepted only when the token may write, so a read-only or expired token fails here and not after the build.
    git(['push', '--dry-run', 'origin', f'HEAD:refs/heads/{PUBLIC_BRANCH}'], cwd=probe, token=token)
    if not head:
        git(['update-ref', '-d', f'refs/heads/{PUBLIC_BRANCH}'], cwd=probe)       # back to an unborn branch: the probe commit is never kept
    archive = clone / 'forecasts'
    if archive.is_dir():
        shutil.copytree(archive, archive_to, dirs_exist_ok=True)
    if head_file:
        Path(head_file).write_text((head or '') + '\n', encoding='utf-8')
    return head


def sync_tree(site, clone):
    """Make the working tree of the clone equal to the built site plus the README and .nojekyll, keeping only `KEEP`."""
    site, clone = Path(site), Path(clone)
    names = {p.name for p in site.iterdir()}
    extra = unexpected_entries(clone, names)
    if extra:
        raise PublicError('The public repository holds entries a publish does not own: ' + ', '.join(extra))
    for entry in clone.iterdir():
        if entry.name in KEEP:
            continue
        shutil.rmtree(entry) if entry.is_dir() else entry.unlink()
    for entry in site.iterdir():
        target = clone / entry.name
        shutil.copytree(entry, target) if entry.is_dir() else shutil.copy2(entry, target)
    shutil.copyfile(README_TEMPLATE, clone / 'README.md')
    (clone / '.nojekyll').write_text('', encoding='utf-8')


def commit_and_push(clone, message, remote, token=None, expected_head=None):
    """Commit the working tree as James and push to main, unless the public repository moved since it was read or nothing changed."""
    clone = Path(clone)
    git(['add', '-A'], cwd=clone)
    if git(['status', '--porcelain'], cwd=clone).stdout.strip() == '' and head_of(clone):
        return 'unchanged'
    if (expected_head or '') != (head_of(clone) or ''):
        raise PublicError('The local clone is not at the commit the archive was read from')
    if expected_head:
        git(['fetch', '--quiet', '--depth', '1', 'origin', PUBLIC_BRANCH], cwd=clone, token=token)
        remote_head = git(['rev-parse', 'FETCH_HEAD'], cwd=clone).stdout.strip()
        if remote_head != expected_head:
            raise PublicError('The public repository changed while the forecast was being built; nothing was pushed. Run the workflow again.')
    git(['checkout', '-q', '-B', PUBLIC_BRANCH], cwd=clone)
    git(['commit', '-q', '-m', message], cwd=clone, identity=True)
    shown = git(['log', '-1', '--format=%an|%ae|%cn|%ce|%B'], cwd=clone).stdout.rstrip('\n')
    if shown != f'{AUTHOR_NAME}|{AUTHOR_EMAIL}|{AUTHOR_NAME}|{AUTHOR_EMAIL}|{message}':
        raise PublicError('The commit does not carry exactly James\'s identity and the plain message; nothing was pushed')
    git(['push', 'origin', f'HEAD:refs/heads/{PUBLIC_BRANCH}'], cwd=clone, token=token)
    return 'pushed'


def push_branch(branch, token=None, cwd=None):
    """Push HEAD of the research checkout to a publish/ branch (a fast-forward at most, never forced)."""
    if not branch.startswith('publish/'):
        raise PublicError('Only publish/ branches are pushed by this workflow')
    git(['push', 'origin', f'HEAD:refs/heads/{branch}'], cwd=cwd, token=token)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest='command', required=True)
    p = sub.add_parser('preflight'); p.add_argument('--clone', required=True); p.add_argument('--archive-to', required=True); p.add_argument('--head-file', required=True)
    q = sub.add_parser('push')
    q.add_argument('--clone', required=True); q.add_argument('--site', required=True); q.add_argument('--message', required=True); q.add_argument('--expected-head', default='')
    b = sub.add_parser('push-branch'); b.add_argument('--branch', required=True)
    a = ap.parse_args(argv)
    token = os.environ.get('PUBLISH_TOKEN', '')
    if token:
        print('::add-mask::' + token)
        print('::add-mask::' + base64.b64encode(f'x-access-token:{token}'.encode()).decode())
    try:
        if a.command == 'preflight':
            head = preflight(a.clone, a.archive_to, f'https://github.com/{PUBLIC_REPO}.git', token, a.head_file)
            print('Public repository reachable and writable; branch main at', head or '(empty repository)')
        elif a.command == 'push':
            sync_tree(a.site, a.clone)
            print('Public repository:', commit_and_push(a.clone, a.message, f'https://github.com/{PUBLIC_REPO}.git', token, a.expected_head or None))
        else:
            repo = os.environ.get('GITHUB_REPOSITORY', '')
            if repo != 'jamesfeng24/nz-election-model-2026':
                raise PublicError('push-branch runs in the research repository only')
            push_branch(a.branch, token)
            print('Pushed', a.branch)
    except PublicError as error:
        print('::error::' + scrub(str(error), token), file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
