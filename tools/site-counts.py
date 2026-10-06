#!/usr/bin/env python3
"""SITE COUNTS · rendered from the sources, never typed (Peter, 6 Oct 2026).

plays  = files hq/method/play/*/*.md whose front matter says state: approved or proven,
         and that were not merged into another play (no merged_into:).

Writes data/site-counts.json and stamps the number into every element marked
data-src="<key>" in index.html (its data-count and its text), so the page shows the
real number with or without JavaScript. Run it before every publish:
    python3 tools/site-counts.py [path/to/hq]
"""
import json, re, sys
from pathlib import Path

SITE = Path(__file__).resolve().parent.parent
HQ = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.home() / 'hob-cockpit/hq'

def front(p):
    t = p.read_text(encoding='utf-8', errors='replace')
    if not t.startswith('---'):
        return {}
    end = t.find('\n---', 3)
    fm = {}
    for line in t[3:end].splitlines():
        if ':' in line and not line.startswith((' ', '\t')):
            k, v = line.split(':', 1)
            fm[k.strip()] = v.strip()
    return fm

plays = 0
for p in sorted((HQ / 'method/play').glob('*/*.md')):
    fm = front(p)
    if fm.get('state') in ('approved', 'proven') and not fm.get('merged_into'):
        plays += 1
if plays == 0:
    sys.exit('site-counts: read 0 plays from ' + str(HQ) + ', refusing to write a zero')

counts = {'plays': plays}
(SITE / 'data').mkdir(exist_ok=True)
(SITE / 'data/site-counts.json').write_text(json.dumps(counts, indent=1) + '\n')

for page in ['index.html']:
    f = SITE / page
    html = f.read_text(encoding='utf-8')
    for key, n in counts.items():
        html = re.sub(r'<b data-count="\d+" data-src="' + key + r'">[^<]*</b>',
                      '<b data-count="%d" data-src="%s">%s</b>' % (n, key, f'{n:,}'), html)
    f.write_text(html, encoding='utf-8')
print('site-counts:', counts)
