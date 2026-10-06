#!/usr/bin/env python3
"""PLAY MATRIX · the library as a grid, rendered from the sources, never typed (Peter, 6 Oct 2026).

rows     = industries in hq/method/evidence/segments.json
columns  = the constraint a play fires on: the folder it sits in, hq/method/play/<constraint>/
cell     = plays whose front matter says state: approved or proven, not merged (no merged_into:),
           whose 'segments:' line names a segment of that industry
drawer   = per play: its title (the H1), when it fires (the 'Fires when' line), and where it was
           read from (read_from), keeping only public publishers and documents

PUBLIC SITE SAFETY: no client world, no client name, no internal path, no source graded ours.
The script refuses to write if any blocked word survives into the JSON.

    python3 tools/write-matrix.py [path/to/hq]     -> data/matrix.json
"""
import json, re, sys
from pathlib import Path

SITE = Path(__file__).resolve().parent.parent
HQ = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.home() / 'hob-cockpit/hq'

BLOCK = re.compile(r'\b(hypermedia|lever|lever brands|flourish|naranti|tadweer|mada|elie saab|ellipse|'
                   r'unfamiliar familiar|cloudpulse|al ?zorah|hob|hob-private|hob-cockpit|perspace|peter|camille|'
                   r'basil|ours|internal|client session)\b|/home/|hq/|\.md\b|\.xlsx\b|\.json\b', re.I)

# the kind of money each constraint caps (play/README.md, 'The seven constraints', plus margin and operations)
COLS = {
    'demand':     ('Demand',     'What the market will buy'),
    'cash':       ('Cash',       'Earned, not yet collected'),
    'estate':     ('Capacity',   'Rooms, screens, sites, fleets'),
    'people':     ('People',     'Hours of skilled people'),
    'licence':    ('Licence',    'Permission to operate'),
    'supply':     ('Supply',     'What you can source'),
    'margin':     ('Margin',     'What is left of the price'),
    'operations': ('Operations', 'Work and waiting'),
    'data':       ('Data',       'The measure under the rest'),
}

# Perspace's own competitors are never named on our surfaces (feedback_no_competitors_on_our_own_surfaces)
RIVAL = re.compile(r'\b(accenture|mckinsey|boston consulting|bcg|bain|deloitte|pwc|pricewaterhouse|kpmg|ernst|ey|'
                   r'palantir|c3\.ai|oliver wyman|kearney|roland berger|alvarez|celonis|anaplan)\b', re.I)

def front(t):
    if not t.startswith('---'):
        return {}
    end = t.find('\n---', 3)
    fm = {}
    for line in t[3:end].splitlines():
        if ':' in line and not line.startswith((' ', '\t')):
            k, v = line.split(':', 1)
            fm[k.strip()] = v.strip()
    return fm

def plain(s):
    s = re.sub(r'(\d)\s*[\u2013\u2014]\s*(\d)', r'\1 to \2', s)
    s = re.sub(r'\s*[\u2013\u2014]\s*', ', ', s)
    s = re.sub(r'\*\*|`', '', s)
    return re.sub(r'\s+', ' ', s).strip()

def sources(raw):
    out = []
    for e in re.split(r';\s+(?![^()]*\))', raw or ''):
        e = re.sub(r'\s*\[[^\]]*\]\s*$', '', e).strip()
        if not e or BLOCK.search(e) or RIVAL.search(e) or len(e) < 6:
            continue
        e = plain(e)
        if e not in out:
            out.append(e)
    return out[:4]

seg = json.loads((HQ / 'method/evidence/segments.json').read_text(encoding='utf-8'))['industries']
inds = list(seg)
name2ind = {}
for ind, v in seg.items():
    for s in v['segments']:
        name2ind.setdefault(s['n'].lower(), set()).add(ind)
names = sorted(name2ind, key=len, reverse=True)

def industries_of(line):
    s = ' ' + line.lower() + ' '
    hits = []
    for nm in names:
        pat = re.compile(r'(?<![a-z])' + re.escape(nm) + r'(?![a-z])')
        if pat.search(s):
            hits.append(nm)
            s = pat.sub(' ', s)
    sure = set().union(*[name2ind[h] for h in hits if len(name2ind[h]) == 1]) if hits else set()
    out = set(sure)
    for h in hits:
        if len(name2ind[h]) > 1:
            both = name2ind[h] & sure
            out |= both if both else name2ind[h]
    return out

cols = [c for c in COLS if (HQ / 'method/play' / c).is_dir()]
plays, cells = [], {}
for c in cols:
    for p in sorted((HQ / 'method/play' / c).glob('*.md')):
        t = p.read_text(encoding='utf-8', errors='replace')
        fm = front(t)
        if fm.get('state') not in ('approved', 'proven') or fm.get('merged_into'):
            continue
        h = re.search(r'^# (.+)$', t, re.M)
        fw = re.search(r'^\*\*Fires when\*\*\s*(.+)$', t, re.M)
        title = plain(h.group(1)) if h else ''
        when = plain(fw.group(1)) if fw else ''
        if not title or BLOCK.search(title) or RIVAL.search(title):
            continue
        if BLOCK.search(when) or RIVAL.search(when):
            when = ''
        src = sources(fm.get('read_from')) if fm.get('source') != 'ours' else []
        i = len(plays)
        plays.append({'t': title, 'w': when, 's': src})
        for ind in industries_of(fm.get('segments', '')):
            cells.setdefault(ind, {}).setdefault(c, []).append(i)

used = sorted({i for r in cells.values() for l in r.values() for i in l})
remap = {o: n for n, o in enumerate(used)}
out = {
    'unit': 'plays',
    'rule': 'approved or proven, not merged; a play counts in every industry its segments belong to',
    'cols': [{'id': c, 'n': COLS[c][0], 'b': COLS[c][1]} for c in cols],
    'rows': [{'n': ind[0].upper() + ind[1:], 'segs': len(seg[ind]['segments']),
              'c': {c: [remap[i] for i in cells.get(ind, {}).get(c, [])] for c in cols if cells.get(ind, {}).get(c)}}
             for ind in inds],
    'plays': [plays[i] for i in used],
}
filled = sum(len(r['c']) for r in out['rows'])
out['totals'] = {'plays': len(used), 'industries': len(inds), 'cells_filled': filled, 'cells': len(inds) * len(cols)}
if not used or not filled:
    sys.exit('write-matrix: read 0 plays from %s, refusing to write' % HQ)

js = json.dumps(out, ensure_ascii=False, separators=(',', ':'))
leak = BLOCK.search(js.replace('"plays"', '')) or RIVAL.search(js)
if leak:
    sys.exit('write-matrix: blocked word in output: %r' % js[max(0, leak.start() - 80):leak.end() + 40])
if re.search('[\u2013\u2014]', js):
    sys.exit('write-matrix: a dash survived')
(SITE / 'data').mkdir(exist_ok=True)
(SITE / 'data/matrix.json').write_text(js + '\n', encoding='utf-8')
print('write-matrix:', out['totals'], '· %d KB' % (len(js) // 1024))
