"""Validate a standalone book publication without local upstream checkouts."""
from pathlib import Path
from html.parser import HTMLParser
from urllib.parse import urlsplit, unquote
import argparse
import hashlib
import json
import re
import zipfile

ROOT = Path(__file__).resolve().parents[1]


class Page(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids, self.links, self.h1 = set(), [], 0

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if 'id' in attrs:
            self.ids.add(attrs['id'])
        self.h1 += tag == 'h1'
        self.links.extend(attrs[k] for k in ('href', 'src') if attrs.get(k))


def audit():
    dist = ROOT / 'dist'
    manifest = json.loads((ROOT / 'publication.json').read_text())
    errors, link_count = [], 0
    for rel, expected in manifest['sourceFiles'].items():
        fp = ROOT / rel
        if not fp.is_file() or hashlib.sha256(fp.read_bytes()).hexdigest() != expected:
            errors.append('source snapshot mismatch: ' + rel)

    pages = {}
    for fp in dist.rglob('*.html'):
        parser = Page()
        parser.feed(fp.read_text())
        pages[fp.resolve()] = parser
    for fp, page in pages.items():
        if page.h1 != 1:
            errors.append('main heading: ' + str(fp.relative_to(dist)))
        for value in page.links:
            u = urlsplit(value)
            if u.scheme or u.netloc:
                continue
            if u.path.startswith('/'):
                errors.append('project base path escape: ' + value)
                continue
            target = (fp.parent / unquote(u.path)).resolve() if u.path else fp
            if target.is_dir():
                target = target / 'index.html'
            if not target.is_relative_to(dist) or not target.exists():
                errors.append('missing or escaped link: ' + value)
            elif u.fragment and target in pages and unquote(u.fragment) not in pages[target].ids:
                errors.append('missing fragment: ' + value)
            link_count += 1

    private = re.compile(r'/Users/[A-Za-z0-9]|/private/tmp/[A-Za-z0-9]|gh[pousr]_[A-Za-z0-9]{24,}|sk-[A-Za-z0-9]{24,}|-----BEGIN (?:OPENSSH|RSA|EC|DSA) PRIVATE KEY-----')
    forbidden = ('.openai', 'research', '.ssh', '.env')
    for name in forbidden:
        if (ROOT / name).exists():
            errors.append('excluded publication entry: ' + name)
    for rel in manifest['sourceFiles']:
        fp = ROOT / rel
        if fp.suffix in {'.html', '.md', '.json', '.py', '.js', '.css', '.yml'} and private.search(fp.read_text()):
            errors.append('private data pattern: ' + rel)

    archive = dist / 'downloads/agent-engineering-book-offline.zip'
    with zipfile.ZipFile(archive) as z:
        if z.testzip():
            errors.append('ZIP CRC')
        names = z.namelist()
        expected_names = {'agent-engineering-book/' + fp.relative_to(dist).as_posix() for fp in dist.rglob('*') if fp.is_file() and fp != archive}
        if set(names) != expected_names or len(names) != len(set(names)):
            errors.append('ZIP file set mismatch')
        for name in names:
            rel = Path(name).relative_to('agent-engineering-book')
            target = (dist / rel).resolve()
            if not target.is_relative_to(dist) or not target.is_file() or z.read(name) != target.read_bytes():
                errors.append('ZIP content mismatch: ' + name)
    if (ROOT / 'BOOK.md').read_bytes() != (dist / 'downloads/agent-engineering-book.md').read_bytes():
        errors.append('Markdown download mismatch')
    cases = json.loads((ROOT / 'content/cases.json').read_text())
    counts = {'cases': len(cases), 'concepts': sum(len(c['concepts']) for c in cases), 'conceptAnchors': sum(len(x['anchors']) for c in cases for x in c['concepts']), 'htmlPages': len(pages)}
    if counts != manifest['counts']:
        errors.append('publication counts mismatch')
    return dict(status='FAIL' if errors else 'PASS', **counts, sourceFiles=len(manifest['sourceFiles']), localLinksAndAssets=link_count, zipFiles=len(names), upstreamSourceRechecked=False, upstreamRuntimeExecuted=False, errors=errors)


if __name__ == '__main__':
    args = argparse.ArgumentParser()
    args.add_argument('--output', type=Path)
    opts = args.parse_args()
    result = audit()
    if opts.output:
        opts.output.parent.mkdir(parents=True, exist_ok=True)
        opts.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(result, ensure_ascii=False))
    raise SystemExit(result['status'] != 'PASS')
