#!/usr/bin/env python3
"""ENGINE BLOCK · written from data/engine.json, never typed (Peter, 8 Oct 2026: "the engine should
have one source of truth and should match the live site").

data/engine.json holds the example projects (order, flags, category, name, line), the tag above
the drawing and the company count. This script rewrites the stat row and the engine drawing in
index.html from it, as static HTML: the nodes sit on an ellipse round the core, clockwise from top
left, in the file's order. The plays, industries and segments figures keep their data-src and are
stamped by tools/site-counts.py (their current value is read from data/site-counts.json).
The Perspace decks read the same file at build time (hob-cockpit hq/decks/perspace/src/shared_slides.py).
    python3 tools/write-engine.py            -> index.html
    python3 tools/write-engine.py --check    -> exit 1 if index.html differs from the file
"""
import json, math, re, sys
from pathlib import Path

SITE = Path(__file__).resolve().parent.parent
E = json.loads((SITE / 'data/engine.json').read_text(encoding='utf-8'))
C = json.loads((SITE / 'data/site-counts.json').read_text(encoding='utf-8'))
P = sorted(E['projects'], key=lambda p: p['order'])
if not P or not E.get('tag') or not E.get('stat', {}).get('n'):
    sys.exit('write-engine: engine.json has no projects, tag or company count')

W, H, CX, CY, RX, RY = 1168, 560, 584, 280, 460, 215   # the drawing's box and the ellipse the nodes sit on
STEP = 360 / len(P)
pts = []
for i in range(len(P)):
    a = math.radians(-90 - STEP / 2 + STEP * i)
    pts.append((CX + RX * math.cos(a), CY + RY * math.sin(a)))

def f(n):
    return '{:,}'.format(n)

nums = ('  <div class="nums rv">\n'
        f'    <div class="num"><b data-count="{E["stat"]["n"]}">{E["stat"]["n"]}</b><span>{E["stat"]["label"]}</span></div>\n'
        f'    <div class="num"><b data-count="{C["plays"]}" data-src="plays">{f(C["plays"])}</b><span>transformation initiatives in the library</span></div>\n'
        f'    <div class="num"><b data-count="{C["industries"]}" data-src="industries">{f(C["industries"])}</b><span>industries mapped</span></div>\n'
        f'    <div class="num"><b data-count="{C["segments"]}" data-src="segments">{f(C["segments"])}</b><span>segments, split by how they make money</span></div>\n'
        '  </div>\n')
r = lambda v: int(round(v))
lines = ''.join(f'<line x1="{CX}" y1="{CY}" x2="{r(x)}" y2="{r(y)}"/>' for x, y in pts)
sparks = ''
for i, (x, y) in enumerate(pts):
    a, b = (f'{r(x)},{r(y)}', f'{CX},{CY}') if i % 2 == 0 else (f'{CX},{CY}', f'{r(x)},{r(y)}')
    sparks += f'<circle class="spark" r="4"><animateMotion dur="2.6s" begin="{i * 0.33:.2f}s" repeatCount="indefinite" path="M{a} L{b}"/></circle>'
nodes = ''.join(
    f'<div class="co" style="left:calc({100 * x / W:.1f}% - 110px);top:calc({100 * y / H:.1f}% - 42px)">'
    f'<i>{" ".join(p["flags"])} · {p["category"].upper()}</i><b>{p["name"]}</b>{p["line"]}</div>'
    for p, (x, y) in zip(P, pts))
engine = (f'  <div class="engtag">{E["tag"]}</div>\n'
          '  <div class="engine">\n'
          f'    <svg viewBox="0 0 {W} {H}" preserveAspectRatio="none"><g stroke="#8BA6B7" stroke-width="1.2" stroke-dasharray="4 5" fill="none">{lines}</g>{sparks}</svg>\n'
          f'    {nodes}\n'
          '    <div class="core"><div><img src="img/star-crop.png" alt=""><small>THE ENGINE</small></div></div>\n'
          '  </div>\n')

page = SITE / 'index.html'
html = page.read_text(encoding='utf-8')
pat = re.compile(r'  <div class="nums rv">\n.*?\n  </div>\n  <div class="engtag">.*?\n  <div class="engine">\n.*?\n  </div>\n(?=</div></section>)', re.S)
if len(pat.findall(html)) != 1:
    sys.exit('write-engine: found %d engine blocks in index.html, expected 1' % len(pat.findall(html)))
new = pat.sub(lambda m: nums + engine, html)
if '--check' in sys.argv:
    sys.exit(0 if new == html else 'write-engine: index.html differs from data/engine.json, run tools/write-engine.py')
page.write_text(new, encoding='utf-8')
print('write-engine: %d projects, %s %s; %s' % (len(P), E['stat']['n'], E['stat']['label'], 'unchanged' if new == html else 'index.html rewritten'))
