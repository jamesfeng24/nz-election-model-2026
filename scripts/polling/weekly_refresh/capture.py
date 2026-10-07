"""Capture the pinned Wikipedia REST table into a dated, never-overwritten raw directory (needs network; curl)."""
import re
import shutil
import subprocess
import time
from datetime import datetime, timezone
from .common import RAW, WIKI_URL, USER_AGENT, CAPTURE, rel, sha


def fetch(run_date, retries=5):
    d = RAW / run_date
    if d.exists():
        raise FileExistsError('Raw capture directory already exists; earlier captures are never overwritten: ' + str(d))
    d.mkdir(parents=True)
    log = []
    body, head = d / CAPTURE, d / (CAPTURE + '.headers')
    for attempt in range(1, retries + 1):
        stamp = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
        tmp = d / 'attempt.html'
        done = subprocess.run(['curl', '-sS', '-L', '-m', '90', '-A', USER_AGENT, '-D', str(head) + '.tmp', '-o', str(tmp), '-w', '%{http_code}', WIKI_URL],
                              capture_output=True, text=True)
        code = int(done.stdout.strip() or 0)
        size = tmp.stat().st_size if tmp.exists() else 0
        log.append(f'{stamp}\t{code}\t{WIKI_URL}\t{size}')
        if code == 200 and size > 100000:
            tmp.replace(body); (d / (CAPTURE + '.headers.tmp')).replace(head)
            break
        for p in (tmp, d / (CAPTURE + '.headers.tmp')):
            p.unlink(missing_ok=True)
        if attempt < retries:
            time.sleep(30 * attempt)
    (d / 'fetch-log.tsv').write_text('\n'.join(log) + '\n')
    if not body.exists():
        text = (d / 'fetch-log.tsv').read_text(); shutil.rmtree(d)   # nothing worth preserving; a rerun may use the same date
        raise RuntimeError('Wikipedia capture failed after retries:\n' + text)
    return body


def revision(run_date):
    h = (RAW / run_date / (CAPTURE + '.headers')).read_text()
    m = re.search(r'(?im)^content-revision-id:\s*(\d+)', h)
    lm = re.search(r'(?im)^last-modified:\s*(.+)$', h)
    return (m.group(1) if m else None), (lm.group(1).strip() if lm else None)
