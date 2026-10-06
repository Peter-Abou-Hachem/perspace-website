#!/usr/bin/env python3
"""PLUG-IN MENU · named from the library, never invented (Peter, 6 Oct 2026: "add 5x more").

Every approved or proven, not merged play in hq/method/play/*/*.md is a move a helper agent can
run. One model call (Claude Sonnet 5, thinking off) turns the plays into short helper names and
says which plays each name runs. The script keeps a name only if it cites real plays, has no
number, no dash, no client or competitor name, and is not a duplicate. The menu that existed on
6 Oct (SEED) is kept with its kinds; every library-derived name is "learned from a cockpit".

    python3 tools/write-plugins.py [path/to/hq]      -> data/plugins.json
Needs ANTHROPIC_API_KEY (read from ~/.openclaw/.env if not in the environment).
"""
import json, os, re, sys
from pathlib import Path
import anthropic

SITE = Path(__file__).resolve().parent.parent
HQ = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.home() / 'hob-cockpit/hq'
MODEL = 'claude-sonnet-5'
TARGET_NEW = 240

BLOCKS = ['Finance', 'People', 'Sales', 'Legal and risk', 'Operations', 'Supply', 'Reporting and content']
EXTRA_OK = 2
SEED = {  # the menu on plugins.html before 6 Oct; kinds as shown there
 'Finance': [('Collections', 'shelf'), 'Invoice', 'Reconciler', 'Expense Audit', 'Cash Forecast', 'Payroll', 'Revenue Recognition'],
 'People': ['Recruiter', 'Onboarding', 'Leave & Attendance', 'Letters', 'Rostering'],
 'Sales': ['Quote Builder', 'Lead Qualifier', 'Pricing', 'Renewals', 'Proposal', 'Pipeline Review', 'Churn Watch'],
 'Legal and risk': ['Contract Reader', 'Compliance', 'KYC', 'Approvals', 'Audit Trail', 'Claims', 'Fraud Watch'],
 'Operations': [('Polynome', 'venture'), 'Inbox Triage', 'Scheduler', 'Dispatch', 'Site Tracker', 'Handoff', 'Escalation', 'Ticket Triage'],
 'Supply': ['Inventory', 'Forecaster', 'Vendor Screener', 'Catalogue Scout', 'Order Desk', 'Restock', 'Quality QC'],
 'Reporting and content': ['Report Writer', 'Data Cleaner', 'Doc Filer', 'Meeting Notes', 'Content Drafter', 'SEO', 'Social', 'Sentiment'],
}
BLOCK = re.compile(r'\b(hypermedia|lever|flourish|naranti|tadweer|mada|elie saab|ellipse|unfamiliar familiar|cloudpulse|'
                   r'perspace|hob|peter|camille|basil|ours)\b', re.I)
RIVAL = re.compile(r'\b(accenture|mckinsey|bcg|bain|deloitte|pwc|kpmg|ey|palantir|c3|celonis|anaplan)\b', re.I)

def key():
    if os.environ.get('ANTHROPIC_API_KEY'):
        return os.environ['ANTHROPIC_API_KEY']
    for line in (Path.home() / '.openclaw/.env').read_text().splitlines():
        if line.startswith('ANTHROPIC_API_KEY='):
            return line.split('=', 1)[1].strip().strip('"\'')
    sys.exit('write-plugins: no ANTHROPIC_API_KEY')

def front(t):
    end = t.find('\n---', 3); fm = {}
    for line in t[3:end].splitlines():
        if ':' in line and not line.startswith((' ', '\t')):
            k, v = line.split(':', 1); fm[k.strip()] = v.strip()
    return fm

plays = []
for p in sorted((HQ / 'method/play').glob('*/*.md')):
    t = p.read_text(encoding='utf-8', errors='replace')
    if not t.startswith('---'):
        continue
    fm = front(t)
    if fm.get('state') not in ('approved', 'proven') or fm.get('merged_into'):
        continue
    h = re.search(r'^# (.+)$', t, re.M)
    if h and not BLOCK.search(h.group(1)):
        plays.append((p.parent.name, re.sub(r'[\u2013\u2014]', ',', h.group(1).strip())))
if not plays:
    sys.exit('write-plugins: read 0 plays from %s' % HQ)

seed_names = [x if isinstance(x, str) else x[0] for v in SEED.values() for x in v]
prompt = f"""Below are {len(plays)} plays from a library. Each play is one move a company can make, and each one can be run by a helper agent that reads the company's files.

Name {TARGET_NEW} helper agents, no more, that between them run as many of these plays as possible. Prefer a name that runs several plays over one that runs a single play. Rules for each name:
- two or three words, Title Case, job-title style, like "Rate Card Checker", "Lease Expiry Watch", "Supplier Price Match"
- says the job plainly, in words an operations manager uses; no jargon, no numbers, no dashes, no company names, no product names
- different from every other name and from these existing ones: {', '.join(seed_names)}
- each name must run at least one play below; list up to five play numbers it runs, no more
- put each name in one block: {', '.join(BLOCKS)}; you may add at most {EXTRA_OK} new blocks only if many plays clearly do not fit (for example "Property and sites")
- spread names so every block gets a fair share

Reply with JSON only, no prose: [{{"n": "Name", "b": "Block", "p": [play numbers]}}, ...]

PLAYS (number | kind of money | play):
""" + '\n'.join(f'{i} | {c} | {t}' for i, (c, t) in enumerate(plays))

RAW = Path(os.environ.get('PLUGINS_RAW', '/tmp/write-plugins-raw.json'))  # reuse with PLUGINS_REUSE=1, never committed
if os.environ.get('PLUGINS_REUSE') and RAW.exists():
    raw = json.loads(RAW.read_text())
else:
    client = anthropic.Anthropic(api_key=key())
    with client.messages.stream(model=MODEL, max_tokens=64000, thinking={'type': 'disabled'},
                                messages=[{'role': 'user', 'content': prompt}]) as s:
        msg = s.get_final_message()
    if msg.stop_reason not in ('end_turn',):
        sys.exit('write-plugins: model stopped on %s' % msg.stop_reason)
    txt = ''.join(b.text for b in msg.content if b.type == 'text')
    raw = json.loads(txt[txt.index('['):txt.rindex(']') + 1])
    RAW.write_text(json.dumps(raw))
RENAME = {'Estate': 'Property and sites', 'Property': 'Property and sites', 'Sites': 'Property and sites'}

def norm(n):
    return re.sub(r's\b', '', re.sub(r'[^a-z ]', '', n.lower())).strip()

seen = {norm(n) for n in seed_names}
out = []
for b, items in SEED.items():
    for x in items:
        n, kind = (x, 'cockpit') if isinstance(x, str) else x
        out.append({'n': n, 'b': b, 'k': kind})
extra = {}
dropped = []
for r in raw:
    n = re.sub(r'\s+', ' ', str(r.get('n', ''))).strip()
    b = str(r.get('b', '')).strip()
    b = RENAME.get(b, b)
    ids = [i for i in r.get('p', []) if isinstance(i, int) and 0 <= i < len(plays)]
    why = ('no play' if not ids else 'words' if not 2 <= len(n.split()) <= 3 else
           'number' if re.search(r'\d', n) else 'dash' if re.search(r'[\u2013\u2014-]', n) else
           'name' if BLOCK.search(n) or RIVAL.search(n) else 'duplicate' if norm(n) in seen else '')
    if why:
        dropped.append((n, why)); continue
    if b not in BLOCKS:
        extra.setdefault(b, 0); extra[b] += 1
    seen.add(norm(n))
    out.append({'n': n, 'b': b, 'k': 'cockpit', 'plays': len(set(ids))})
keep_extra = sorted(extra, key=lambda b: -extra[b])[:EXTRA_OK]
out = [o for o in out if o['b'] in BLOCKS or o['b'] in keep_extra]
# five times the old menu, shared fairly: each block gets an equal quota, a block with fewer
# good names keeps them all and its spare room goes to the others; names that run more plays first
TOTAL = 5 * len(seed_names)
groups = {b: [o for o in out if o['b'] == b] for b in BLOCKS + keep_extra}
for g in groups.values():
    g.sort(key=lambda o: (o.get('plays') is not None, -(o.get('plays') or 0)))
quota = {b: 0 for b in groups}
left = TOTAL
while left > 0:
    open_b = [b for b in groups if quota[b] < len(groups[b])]
    if not open_b:
        break
    for b in open_b:
        if left == 0:
            break
        quota[b] += 1; left -= 1
out = [o for b in groups for o in groups[b][:quota[b]]]
order = BLOCKS[:5] + keep_extra + BLOCKS[5:]
js = {'kinds': {'shelf': 'Off the shelf', 'cockpit': 'Learned from a cockpit', 'venture': 'Sourced from the world'},
      'blocks': [{'n': b, 'items': [{k: v for k, v in o.items() if k != 'b'} for o in out if o['b'] == b]} for b in order],
      'from_plays': len(plays), 'model': MODEL}
text = json.dumps(js, ensure_ascii=False, indent=1)
if re.search('[\u2013\u2014]', text) or BLOCK.search(text):
    sys.exit('write-plugins: blocked text survived')
(SITE / 'data/plugins.json').write_text(text + '\n', encoding='utf-8')
print('write-plugins: %d names (%d new) in %d blocks; dropped %d %s' % (len(out), len(out) - len(seed_names),
      len(order), len(dropped), dropped[:12]))
print({b['n']: len(b['items']) for b in js['blocks']})
