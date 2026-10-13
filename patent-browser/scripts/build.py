"""Step 5: build the browser page, CSV and text files.

  build.py WORK OUT --name dragonball --title "Joe Dragonball patents (Z-corp)" [--pdf-dir dragonball-pdfs]

Writes OUT/<name>-patents.html, OUT/<name>-patents.csv and OUT/<name>-text/.
The PDF directory must be inside OUT (the page links to it by relative path);
it defaults to <name>-pdfs. Refuses to build while any family or patent lacks
its summary, so a clean build means the hand-written file is complete.
"""
import argparse, collections, csv, datetime, html, json, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from sums import load_sums

ap = argparse.ArgumentParser()
ap.add_argument('work'); ap.add_argument('out'); ap.add_argument('--name', required=True)
ap.add_argument('--title', required=True); ap.add_argument('--pdf-dir')
a = ap.parse_args()
W, OUT, name = a.work, a.out, a.name
pdfdir, textdir = a.pdf_dir or f'{name}-pdfs', f'{name}-text'
g = json.load(open(W + '/meta/grouped.json'))
P, G = g['patents'], {x['id']: x for x in g['groups']}
src = json.load(open(W + '/meta/source.json'))
themes, fam, focus = load_sums(W + '/meta/sums.txt')

err = []
if not themes: err.append('no "#theme key|Label" lines in sums.txt')
for fid, x in G.items():
    f = fam.get(fid)
    if not f: err.append(f'family {fid} ({x["members"][0]} {x["title"][:50]}) has no entry'); continue
    if f['theme'] not in themes: err.append(f'family {fid}: unknown theme "{f["theme"]}"')
    for k in ('summary', 'uses', 'concepts', 'useTags'):
        if not f[k]: err.append(f'family {fid}: {k} is empty')
for n in P:
    if focus.get(n, 'TODO') in ('TODO', ''): err.append(f'patent {n}: no claim-focus line')
un = src.get('unclassified') or {}
if any(un.values()):
    err.append('source.json still has rows under "unclassified"; move each into "removed" (with a reason) and delete the key')
if err:
    print('\n'.join(err[:60])); sys.exit(f'{len(err)} problems; nothing written')

flags = src.get('flags') or {}
URL = 'https://ppubs.uspto.gov/pubwebapp/external.html?q=({}).pn.&db=USPAT&type=queryString'
pats = []
for n, p in sorted(P.items(), key=lambda kv: (kv[1]['granted'], kv[0])):
    pdf = f"{pdfdir}/{p['id']}.pdf"
    pats.append(dict(n=n, id=p['id'], kind=p['kind'], title=p['title'], inv=p['inv'], filed=p['filed'], granted=p['granted'],
                     prio=p['prio'], app=p['app'], assignee=html.unescape(p['assignee']), abstract=p['abstract'],
                     claim1=p['claim1'], nclaims=p['nclaims'], pages=p['pages'], cpc=p['cpc'], fam=p['fam'],
                     focus=focus[n], pdf=pdf, flag=flags.get(n, ''), hasPdf=os.path.exists(os.path.join(OUT, pdf))))
fams = {fid: dict(title=G[fid]['title'], members=G[fid]['members'], prio=G[fid]['prio'], **fam[fid]) for fid in G}
used = collections.OrderedDict((k, v) for k, v in themes.items() if any(f['theme'] == k for f in fams.values()))
source = dict(intro=src.get('intro', ''), query=src.get('query', ''), rows=src.get('rows', len(P)),
              removed=src.get('removed', []), notes=src.get('notes', []))
data = dict(built=datetime.date.today().isoformat(), title=a.title, name=name, pdfDir=pdfdir, textDir=textdir,
            themes=used, patents=pats, families=fams, source=source)
js = json.dumps(data, ensure_ascii=False, separators=(',', ':')).replace('</', '<\\/')
page = f'{OUT}/{name}-patents.html'
open(page, 'w').write(open(HERE + '/template.html').read().replace('__DATA__', js))

with open(f'{OUT}/{name}-patents.csv', 'w', newline='') as f:
    w = csv.writer(f)
    w.writerow(['patent_number', 'kind', 'title', 'granted', 'earliest_priority', 'filed', 'application', 'inventors', 'assignee',
                'family', 'theme', 'concepts', 'use_case_areas', 'claim_focus', 'family_summary', 'use_cases', 'pdf', 'uspto_url', 'note'])
    for p in pats:
        F = fams[p['fam']]
        w.writerow([p['n'], p['kind'], p['title'], p['granted'], p['prio'], p['filed'], p['app'], '; '.join(p['inv']), p['assignee'],
                    p['fam'], themes[F['theme']], '; '.join(F['concepts']), '; '.join(F['useTags']), p['focus'], F['summary'],
                    '; '.join(F['uses']), p['pdf'], URL.format(p['n']), p['flag']])


def clean(s):
    s = re.sub(r'<br\s*/?>', '\n', s or '')
    return html.unescape(re.sub(r'<[^>]+>', '', s)).strip()


os.makedirs(f'{OUT}/{textdir}', exist_ok=True)
for p in pats:
    d = json.load(open(f"{W}/meta/docs/{p['n']}.json"))
    open(f"{OUT}/{textdir}/{p['id']}.txt", 'w').write(
        f"US {p['n']} {p['kind']}\n{p['title']}\nGranted {p['granted']} | Filed {p['filed']} | Application {p['app']}\n"
        f"Inventors: {', '.join(p['inv'])}\nAssignee: {p['assignee']}\nSource: USPTO Patent Public Search\n\n"
        f"ABSTRACT\n{p['abstract']}\n\nCLAIMS\n{clean(d.get('claimsHtml'))}\n\nDESCRIPTION\n"
        f"{clean(d.get('backgroundTextHtml'))}\n\n{clean(d.get('briefHtml'))}\n\n{clean(d.get('descriptionHtml'))}\n")

print(f'{page}: {len(pats)} patents, {len(fams)} families, {os.path.getsize(page) // 1024} KB')
print('missing PDFs:', [p['n'] for p in pats if not p['hasPdf']] or 'none')
print('themes:', dict(collections.Counter(themes[f['theme']] for f in fams.values() for _ in f['members'])))
print('use-case areas:', dict(collections.Counter(t for f in fams.values() for t in f['useTags']).most_common()))
print('concept tags:', len({c for f in fams.values() for c in f['concepts']}))
