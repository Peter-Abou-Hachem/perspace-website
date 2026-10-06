#!/usr/bin/env python3
"""SITE COUNTS · rendered from the sources, never typed (Peter, 6 Oct 2026).

plays    = files hq/method/play/*/*.md whose front matter says state: approved or proven,
           and that were not merged into another play (no merged_into:).
systems  = distinct system names in hq/method/connectors/catalogue.json
core     = of those, the finance and ERP systems (groups erp + fin)

Writes data/site-counts.json and stamps each number into every element marked
data-src="<key>" on every page (its data-count, if any, and its text), so the page shows the
real number with or without JavaScript. Run it before every publish:
    python3 tools/site-counts.py [path/to/hq]
"""
import json, re, sys
from pathlib import Path

SITE = Path(__file__).resolve().parent.parent
HQ = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.home() / 'hob-cockpit/hq'
PAGES = ['index.html', 'cockpit.html', 'method.html', 'plugins.html']

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

cat = json.loads((HQ / 'method/connectors/catalogue.json').read_text(encoding='utf-8'))
systems = len({i['n'] for g in cat['groups'].values() for i in g['items']})
core = len({i['n'] for k in ('erp', 'fin') for i in cat['groups'][k]['items']})

counts = {'plays': plays, 'systems': systems, 'core': core}
zero = [k for k, n in counts.items() if not n]
if zero:
    sys.exit('site-counts: read 0 for %s from %s, refusing to write a zero' % (', '.join(zero), HQ))

(SITE / 'data').mkdir(exist_ok=True)
(SITE / 'data/site-counts.json').write_text(json.dumps(counts, indent=1) + '\n')

stamped = {k: 0 for k in counts}
for page in PAGES:
    f = SITE / page
    html = f.read_text(encoding='utf-8')
    for key, n in counts.items():
        pat = re.compile(r'(<(\w+)\b[^>]*\bdata-src="' + key + r'"[^>]*>)[^<]*(</\2>)')
        def fix(m):
            stamped[key] += 1
            tag = re.sub(r'data-count="\d+"', 'data-count="%d"' % n, m.group(1))
            return tag + f'{n:,}' + m.group(3)
        html = pat.sub(fix, html)
    f.write_text(html, encoding='utf-8')
missing = [k for k, v in stamped.items() if v == 0]
print('site-counts:', counts, '· stamped', stamped)
if missing:
    sys.exit('site-counts: no element on any page carries ' + ', '.join(missing))
