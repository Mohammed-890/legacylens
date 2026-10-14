"""Trusted fixture replay, never arbitrary uploaded repository execution.

Temporary directories isolate changes, not hostile processes. This runner executes
only the bundled demonstration. Real untrusted execution requires a hardened sandbox.
"""
import difflib
import hashlib
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / 'fixtures' / 'invoice_service'


def fixture_files():
    return {p.name:p.read_text() for p in sorted(FIXTURE.iterdir()) if p.is_file()}


def proposal():
    source = (FIXTURE/'invoices.py').read_text()
    replacement = source.replace('customer["full_name"]', 'customer["display_name"]')
    patch = ''.join(difflib.unified_diff(source.splitlines(True), replacement.splitlines(True),
                                       fromfile='a/invoices.py', tofile='b/invoices.py'))
    return dict(id=hashlib.sha256(patch.encode()).hexdigest()[:16], path='invoices.py', diff=patch,
                summary='Update the invoice consumer to the customer schema v2 field.',
                origin='Maintainer-authored demonstration repair',
                scope='Disposable copy of the bundled invoice fixture only. Your imported files are never modified.')


def execute_approved(proposal_id):
    expected = proposal()
    if proposal_id != expected['id']:
        raise ValueError('Proposal changed; review the current diff first.')
    started = time.monotonic()
    with tempfile.TemporaryDirectory(prefix='legacylens-fixture-') as temp:
        work = Path(temp)
        for name, content in fixture_files().items():
            (work/name).write_text(content)
        def test():
            result = subprocess.run([sys.executable, '-m', 'unittest', '-v', 'test_invoices'],
                                    cwd=work, capture_output=True, text=True, timeout=10,
                                    env={'PATH':os.defpath,'PYTHONIOENCODING':'utf-8','PYTHONDONTWRITEBYTECODE':'1'})
            return {'exit_code':result.returncode, 'output':(result.stdout+result.stderr)[-14000:],
                    'passed': result.returncode == 0}
        before = test()
        file = work/'invoices.py'
        file.write_text(file.read_text().replace('customer["full_name"]','customer["display_name"]'))
        after = test()
    return dict(proposal=expected, before=before, after=after, elapsed_ms=round((time.monotonic()-started)*1000),
                tests=5, verified=not before['passed'] and after['passed'],
                environment='Trusted bundled fixture in a disposable directory; not an untrusted-code sandbox.')
