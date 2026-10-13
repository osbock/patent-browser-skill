"""Step 4 helper: print what Claude needs to read to write WORK/meta/sums.txt.

  digest.py WORK [--all] [--from N] [--to N] [--len CHARS]
  digest.py WORK --seed PRIORWORK [PRIORWORK ...]

Default prints only families that still need writing (no entry in sums.txt, or a
member without a claim-focus line). Long claims are cut to head + tail; raise
--len or read WORK/meta/docs/<n>.json when a claim's middle matters.

--seed starts sums.txt from earlier work directories: every family that shares a
patent with an earlier set gets that set's theme, concepts, summary, use cases
and claim-focus lines; members the earlier set did not have are marked TODO.
"""
import argparse, json, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sums import load_sums

ap = argparse.ArgumentParser()
ap.add_argument('work'); ap.add_argument('--all', action='store_true')
ap.add_argument('--from', dest='a', type=int, default=0); ap.add_argument('--to', dest='b', type=int, default=10**6)
ap.add_argument('--len', dest='L', type=int, default=900); ap.add_argument('--seed', nargs='*')
a = ap.parse_args()
g = json.load(open(a.work + '/meta/grouped.json'))
P = g['patents']
sf = a.work + '/meta/sums.txt'

if a.seed:
    if os.path.exists(sf):
        sys.exit(f'{sf} already exists; delete it first if you really want to re-seed')
    themes, pfam, pfoc = {}, {}, {}
    for w in a.seed:
        t, fam, foc = load_sums(w + '/meta/sums.txt')
        pp = json.load(open(w + '/meta/grouped.json'))['patents']
        themes.update(t)
        for n in pp:
            if pp[n]['fam'] in fam and n not in pfam:
                pfam[n] = fam[pp[n]['fam']]
        for n, x in foc.items(): pfoc.setdefault(n, x)
    out, used, todo = [], set(), 0
    for G in g['groups']:
        f = next((pfam[n] for n in G['members'] if n in pfam), None)
        if not f: continue
        used.add(f['theme'])
        out.append(f"@{G['members'][0]}|{f['theme']}|{'; '.join(f['concepts'])}|{'; '.join(f['useTags'])}")
        out += ['S: ' + f['summary'], 'U: ' + '; '.join(f['uses'])]
        for n in G['members']:
            out.append(f"{n}: {pfoc.get(n, 'TODO')}"); todo += n not in pfoc
    head = [f'#theme {k}|{v}' for k, v in themes.items()]
    open(sf, 'w').write('\n'.join(head + out) + '\n')
    print(f'seeded {sum(l.startswith("@") for l in out)} of {len(g["groups"])} families; {todo} members marked TODO; themes carried over: {len(themes)}')

themes, fam, foc = load_sums(sf) if os.path.exists(sf) else ({}, {}, {})
if themes: print('THEMES:', '; '.join(f'{k}={v}' for k, v in themes.items()))
left = 0
for G in g['groups'][a.a:a.b]:
    need = [n for n in G['members'] if foc.get(n, 'TODO') == 'TODO']
    if G['id'] in fam and not need and not a.all: continue
    left += 1
    print(f"\n## {G['id']} | {' / '.join(G['titles'])} | priority {G['prio']} | {len(G['members'])} patents" + (' | family entry exists, members need focus lines' if G['id'] in fam else ''))
    print('ABSTRACT:', P[G['members'][0]]['abstract'])
    for n in (G['members'] if a.all or G['id'] not in fam else need):
        c = P[n]['claim1']
        print(f"- {n} ({P[n]['granted']}): " + (c if len(c) <= a.L else c[:a.L * 2 // 3] + ' […] ' + c[-a.L // 3:]))
print(f'\n{left} families printed' + ('' if a.all else ' (still to write)'))
