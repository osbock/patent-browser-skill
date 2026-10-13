"""Step 3: extract fields from the USPTO docs and group patents into families.

  group.py WORK

A family is patents with the same normalized title, or linked by continuity data
with a title similarity above 0.93. Writes WORK/meta/grouped.json.
"""
import collections, difflib, html, json, os, re, sys

W = sys.argv[1]
meta = json.load(open(W + '/meta/final.json'))
src = json.load(open(W + '/meta/source.json'))


def clean(s):
    s = re.sub(r'<br\s*/?>', '\n', s or '')
    return html.unescape(re.sub(r'<[^>]+>', '', s)).strip()


def lst(v):
    return [] if v is None else v if isinstance(v, list) else [v]


P, nodoc, who = {}, [], collections.Counter()
for k in sorted(meta):
    f = f'{W}/meta/docs/{k}.json'
    if not os.path.exists(f):
        nodoc.append(k); continue
    d = json.load(open(f))
    cl = clean(d.get('claimsHtml'))
    c1 = re.sub(r'^\s*1\s*\.\s*', '', re.split(r'\n\s*2\s*\. ', cl, maxsplit=1)[0]).strip()
    cont = clean(' '.join(lst(d.get('continuityData'))))
    rel = [x[:10] for x in lst(d.get('relatedApplFilingDate'))] + [x[:10] for x in lst(d.get('priorityClaimsDate')) if x]
    filed = lst(d.get('applicationFilingDate'))[0][:10]
    P[k] = dict(n=k, id=d['guid'].replace('-', ''), kind=d['guid'].split('-')[-1], title=clean(d['inventionTitle']),
                inv=[' '.join(reversed([y.strip() for y in x.split(';')])) for x in lst(d.get('inventorsName'))],
                filed=filed, granted=d['datePublished'][:10], prio=min([filed] + [r for r in rel if r > '1990']),
                app=d['applicationNumber'],
                assignee='; '.join(dict.fromkeys(clean(x) for x in lst(d.get('assigneeName')))),
                abstract=clean(d.get('abstractHtml')), claim1=c1,
                nclaims=int(d.get('numberOfClaims') or 0), pages=int(d.get('pageCount') or 0),
                cpc=[c.split()[0] for c in lst(d.get('cpcInventive'))][:8],
                apps=set(re.findall(r'\b(\d{8})\b', cont)) | {re.sub(r'\D', '', d['applicationNumber'])})
    last = (src.get('inventor') or '').split()[-1:]  # report spellings/locations of the searched inventor
    for nm, ci, st in zip(lst(d.get('inventorsName')), lst(d.get('inventorCity')), lst(d.get('inventorState')) or [''] * 99):
        if last and last[0].lower() in nm.lower():
            who[(nm, ci, st)] += 1


def norm(t):
    return re.sub(r'[^a-z0-9 ]', '', t.lower()).strip()


par = {k: k for k in P}


def find(x):
    while par[x] != x:
        par[x] = par[par[x]]; x = par[x]
    return x


ks = list(P)
bt = collections.defaultdict(list)
for k in ks: bt[norm(P[k]['title'])].append(k)
for v in bt.values():
    for x in v[1:]: par[find(x)] = find(v[0])
for i, x in enumerate(ks):
    for y in ks[i + 1:]:
        if find(x) != find(y) and P[x]['apps'] & P[y]['apps'] and difflib.SequenceMatcher(None, norm(P[x]['title']), norm(P[y]['title'])).ratio() > 0.93:
            par[find(y)] = find(x)
G = collections.defaultdict(list)
for k in ks: G[find(k)].append(k)
groups = sorted(G.values(), key=lambda v: (min(P[x]['prio'] for x in v), v[0]))
out = []
for i, v in enumerate(groups):
    v.sort(key=lambda x: P[x]['granted'])
    for x in v: P[x]['fam'] = 'F%03d' % (i + 1)
    out.append(dict(id='F%03d' % (i + 1), members=v, title=P[v[0]]['title'], titles=sorted({P[x]['title'] for x in v}), prio=min(P[x]['prio'] for x in v)))
for q in P.values(): q['apps'] = sorted(q['apps'])
json.dump(dict(patents=P, groups=out), open(W + '/meta/grouped.json', 'w'))
print(f'{len(P)} patents in {len(out)} families')
if nodoc: print('NO TEXT DOC (not included):', nodoc)
print('Assignees:', dict(collections.Counter(p['assignee'] for p in P.values()).most_common(10)))
if who:
    print('Searched inventor as recorded by the USPTO (check these are one person):')
    for (nm, ci, st), c in who.most_common(): print(f'  {c:4d}  {nm} — {ci}, {st}')
