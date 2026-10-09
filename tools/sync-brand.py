#!/usr/bin/env python3
"""BRAND SYNC · perspace.ai reads the Perspace brand from its one source, never typed by hand
(Peter, 9 Oct 2026: "One source of truth for brand elements, translated to all assets").

The source is hob-cockpit hq/brand/ (brand.json, built by build-brand.py). This script copies the
generated files into the site as /brand/ with the same layout, so themes/website.css's
@import "../brand.css" and brand.css's assets/fonts/ url resolve unchanged:
    brand/brand.css · brand/themes/website.css · brand/assets/fonts/* · brand/assets/<logo files>
Then it writes the lines of themes/website-head.html (plus the site's own token-only
site-brand.css) into every page head, just before </head>, between marker comments, so a
second run replaces the block instead of adding another (idempotent).

    python3 tools/sync-brand.py [path/to/hq/brand]     -> copy + stamp every page
    python3 tools/sync-brand.py --check                -> exit 1 if anything is stale
Run hq/brand/build-brand.py first after any change to brand.json.
"""
import filecmp, os, re, shutil, sys
from pathlib import Path

SITE = Path(__file__).resolve().parent.parent
args = [a for a in sys.argv[1:] if not a.startswith('--')]
CHECK = '--check' in sys.argv
SRC = Path(args[0] if args else os.environ.get('PERSPACE_BRAND', Path.home() / 'hob-cockpit/hq/brand')).resolve()
DST = SITE / 'brand'
if not (SRC / 'brand.json').exists() or not (SRC / 'themes/website.css').exists():
    sys.exit(f'sync-brand: no brand source at {SRC} (needs brand.json and themes/website.css)')

FILES = ['brand.css', 'themes/website.css']
ASSETS = ['favicon.png', 'perspace-lockup-ink.png', 'perspace-lockup-white.png', 'perspace-wordmark-ink.png',
          'perspace-wordmark-white.png', 'perspace-symbol-ink.png', 'perspace-symbol-white.png',
          'perspace-symbol-chrome.png', 'perspace-star-chrome.png']
FILES += ['assets/' + a for a in ASSETS]
FILES += ['assets/fonts/' + f.name for f in sorted((SRC / 'assets/fonts').iterdir()) if f.is_file()]

stale = []
for rel in FILES:
    s, d = SRC / rel, DST / rel
    if not s.exists():
        sys.exit(f'sync-brand: missing in source: {rel}')
    if d.exists() and filecmp.cmp(s, d, shallow=False):
        continue
    stale.append(rel)
    if not CHECK:
        d.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(s, d)

# the head block: website-head.html's tags (comments dropped), then the site's token-only overrides
head = (SRC / 'themes/website-head.html').read_text(encoding='utf-8')
tags = re.findall(r'<link[^>]+>', re.sub(r'<!--.*?-->', '', head, flags=re.S))
if not tags:
    sys.exit('sync-brand: website-head.html has no <link> lines')
tags.append('<link rel="stylesheet" href="/site-brand.css">')
BEGIN, END = '<!-- brand:begin · tools/sync-brand.py, from hq/brand. Do not edit by hand. -->', '<!-- brand:end -->'
block = BEGIN + '\n' + '\n'.join(tags) + '\n' + END + '\n'
pat = re.compile(re.escape(BEGIN.split(' · ')[0]) + r'.*?' + re.escape(END) + r'\n?', re.S)

pages = sorted(p for p in SITE.glob('*.html'))
for p in pages:
    html = p.read_text(encoding='utf-8')
    if '</head>' not in html:
        continue   # a one-line forward (grip.html) has no head to dress
    new = pat.sub('', html)
    new = new.replace('</head>', block + '</head>', 1)
    if new != html:
        stale.append(p.name)
        if not CHECK:
            p.write_text(new, encoding='utf-8')

if CHECK:
    if stale:
        print('sync-brand: stale:', ', '.join(stale)); sys.exit(1)
    print('sync-brand: brand files and page heads are current')
else:
    print(f'sync-brand: {SRC} -> {DST.relative_to(SITE)}/ ; updated {len(stale)}: ' + (', '.join(stale) or 'nothing'))
