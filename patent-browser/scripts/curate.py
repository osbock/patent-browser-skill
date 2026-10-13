r'''Record decisions about what is in the set. Run after search.py, as often as needed.

  curate.py WORK --drop 8170401 1659815 --reason "Foreign numbers that match unrelated US patents"
  curate.py WORK --drop-granted-before 1976-01-01 --reason "Foreign numbers that match old, unrelated US patents"
  curate.py WORK --classify '^\d{9}-\d{4}$' --reason "EU registered design numbers"
  curate.py WORK --classify-rest --reason "Not a US patent number"
  curate.py WORK --flag 12670497 "Assignee is Red Ribbon, Inc., unlike the rest of the list; kept, may be a typo."
  curate.py WORK --note "Inventor name" "Listed as Joe Dragonball and Joe David Dragonball; treated as one person."
  curate.py WORK --show

--drop removes granted patents from the set. --classify moves source-list rows
that search.py could not use (matched by regex) into the "left out" table.
Every decision appears on the page's "About the data" tab.
'''
import argparse, json, re, sys

ap = argparse.ArgumentParser()
ap.add_argument('work'); ap.add_argument('--drop', nargs='*'); ap.add_argument('--classify')
ap.add_argument('--drop-granted-before', metavar='YYYY-MM-DD')
ap.add_argument('--classify-rest', action='store_true'); ap.add_argument('--reason')
ap.add_argument('--flag', nargs=2, metavar=('NUMBER', 'TEXT')); ap.add_argument('--note', nargs=2, metavar=('ENTRY', 'TEXT'))
ap.add_argument('--show', action='store_true')
a = ap.parse_args()
fj, sj = a.work + '/meta/final.json', a.work + '/meta/source.json'
final, src = json.load(open(fj)), json.load(open(sj))
un = src.get('unclassified') or {}


def remove(rows):
    if not a.reason: sys.exit('--reason is required')
    if not rows: sys.exit('nothing matched')
    for r in src['removed']:
        if r['reason'] == a.reason:
            r['count'] += len(rows); break
    else:
        src['removed'].append(dict(reason=a.reason, count=len(rows), examples=', '.join(rows[:4]) + (' …' if len(rows) > 4 else '')))
    print(f'left out {len(rows)}: {a.reason}')


if a.drop_granted_before:
    a.drop = (a.drop or []) + [n for n, x in final.items() if (x.get('datePublished') or '9') < a.drop_granted_before]
if a.drop:
    bad = [n for n in a.drop if n not in final]
    if bad: sys.exit(f'not in the set: {bad}')
    for n in a.drop:
        del final[n]; src.get('flags', {}).pop(n, None)
    remove(a.drop)
if a.classify or a.classify_rest:
    hit = []
    for k in list(un):
        keep = []
        for r in un[k]:
            (hit if a.classify_rest or re.search(a.classify, r) else keep).append(r)
        un[k] = keep
    remove(hit)
if a.flag:
    if a.flag[0] not in final: sys.exit('not in the set: ' + a.flag[0])
    src.setdefault('flags', {})[a.flag[0]] = a.flag[1]
    src['notes'].append(dict(entry='US ' + a.flag[0] + ' — ' + (final[a.flag[0]].get('inventionTitle') or ''), note=a.flag[1]))
if a.note:
    src['notes'].append(dict(entry=a.note[0], note=a.note[1]))
if 'unclassified' in src and not any(un.values()):
    del src['unclassified']
json.dump(final, open(fj, 'w')); json.dump(src, open(sj, 'w'), indent=1)
if True:
    print(f'{len(final)} patents in the set')
    for r in src['removed']: print(f"  left out {r['count']:4d}  {r['reason']}  [{r['examples']}]")
    for k, v in (src.get('unclassified') or {}).items():
        if v: print(f'  STILL UNCLASSIFIED ({k}): {len(v)} rows, e.g. {v[:8]}')
    for r in src['notes']: print(f"  note: {r['entry']}: {r['note'][:100]}")
