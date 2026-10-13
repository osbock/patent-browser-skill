"""Step 1: decide which US granted patents are in the set.

  search.py WORK --inventor "Joe Dragonball" --assignee "Z-corp"
  search.py WORK --assignee "Capsule Corp"
  search.py WORK --query '(nfc AND beacon).ti. AND (z ADJ corp).as.'
  search.py WORK --numbers list.csv

Writes WORK/meta/final.json (patent number -> USPTO search record) and
WORK/meta/source.json (how the set was made, what was left out, notes, flags).
"""
import argparse, collections, json, os, re, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ppubs import PP


def words(s):
    return [w for w in re.sub(r'[^A-Za-z0-9 ]', ' ', s).lower().split() if w]


def inventor_q(name):
    w = words(name)
    if len(w) == 1:
        return f'({w[0]}).in.'
    # first and last name within two words of each other, either order (USPTO stores "Last; First Middle")
    return f'({w[-1]} NEAR2 {w[0]}).in.'


def assignee_q(name):
    w = [x for x in words(name) if x not in ('llc', 'inc', 'corp', 'ltd', 'co')]
    ph = '(' + ' ADJ '.join(w) + ')'
    # some grants record no assignee and name the company only as applicant
    return f'({ph}.as. OR {ph}.aanm.)'


def num(x):
    return x['publicationReferenceDocumentNumber']


def brief(x):
    return f"{num(x)} | {'; '.join(x.get('assigneeName') or ['(no assignee)'])} | {x.get('inventionTitle')}"


ap = argparse.ArgumentParser()
ap.add_argument('work')
ap.add_argument('--inventor')
ap.add_argument('--assignee')
ap.add_argument('--query', help='raw Patent Public Search (BRS) query; ANDed with the other options')
ap.add_argument('--numbers', help='file with one patent or application number per line (a header line is fine)')
a = ap.parse_args()
os.makedirs(a.work + '/meta/docs', exist_ok=True)
p = PP()
src = dict(mode='', query='', intro='', removed=[], notes=[], flags={})

if a.numbers:
    rows = [l.strip().strip('"') for l in open(a.numbers, encoding='utf-8-sig').read().splitlines() if l.strip()]
    if rows and not re.search(r'\d', rows[0]):
        rows = rows[1:]
    grants, apps, other, dup, seen = {}, {}, [], [], set()
    for r in rows:
        if r in seen:
            dup.append(r); continue
        seen.add(r)
        c = re.sub(r'^US\s*', '', r, flags=re.I).replace(',', '').replace(' ', '')
        c = re.sub(r'[AB]\d$', '', c)
        if re.fullmatch(r'\d{2}/\d{6}', c):
            apps[r] = c
        elif re.fullmatch(r'(\d{7,8}|(D|RE|PP)\d{4,7})', c, flags=re.I):
            grants[r] = c.upper()
        else:
            other.append(r)
    found = {}
    vals = sorted(set(grants.values()))
    for i in range(0, len(vals), 40):
        for x in p.search('(' + ' | '.join(f'"{v}"' for v in vals[i:i + 40]) + ').pn.'):
            found[num(x)] = x
    final, missing, resolved = {}, [], {}
    for r, c in grants.items():
        if c in found:
            final[c] = found[c]
        elif re.fullmatch(r'(1[3-9]|29|35)\d{6}', c):
            # too high to be a grant number, so try it as an application number (series 13-19, 29, 35)
            apps[r] = c[:2] + '/' + c[2:]
        else:
            missing.append(r)
    for r, c in apps.items():
        hit = p.search(f'"{c}".app.')
        if hit:
            final[num(hit[0])] = hit[0]; resolved[r] = num(hit[0])
        else:
            missing.append(r)
    src.update(mode='numbers', rows=len(rows), intro=f'The set comes from the list {os.path.basename(a.numbers)} ({len(rows)} rows).')
    if dup:
        src['removed'].append(dict(reason='Duplicate row', count=len(dup), examples=', '.join(dup[:4])))
    if resolved:
        src['notes'].append(dict(entry='Application numbers', note='Listed by application number and resolved to the granted patent: ' + ', '.join(f'{k} is US {v}' for k, v in resolved.items())))
        for k, v in resolved.items():
            src['flags'][v] = f'Listed in the source by application number {k}; resolved to this patent.'
    # Claude must classify these two lists before building (see SKILL.md)
    src['unclassified'] = dict(not_us_format=other, us_format_not_found=missing)
    print(f'{len(rows)} rows: {len(final)} US grants found, {len(dup)} duplicates, {len(resolved)} resolved from application numbers')
    print(f'{len(other)} rows are not in a US number format:', other[:60], '...' if len(other) > 60 else '')
    print(f'{len(missing)} US-format numbers have no granted patent:', missing)
else:
    parts = []
    if a.inventor: parts.append(inventor_q(a.inventor))
    if a.assignee: parts.append(assignee_q(a.assignee))
    if a.query: parts.append('(' + a.query + ')')
    if not parts:
        ap.error('give --inventor, --assignee, --query or --numbers')
    q = ' AND '.join(parts)
    res = p.search(q)
    final = {num(x): x for x in res}
    who = ' and '.join(x for x in [a.inventor and f'inventor {a.inventor}', a.assignee and f'assignee {a.assignee}'] if x)
    src.update(mode='search', query=q, inventor=a.inventor or '', assignee=a.assignee or '',
               intro=f'The set comes from a USPTO Patent Public Search query for {who or "the query below"}, granted US patents only.')
    print(f'{q}\n{len(final)} granted US patents')
    if a.inventor and a.assignee:
        # same inventor name, different assignee: report so the user can see what the assignee filter removed
        rest = [x for x in p.search(inventor_q(a.inventor)) if num(x) not in final]
        if rest:
            by = collections.Counter('; '.join(x.get('assigneeName') or ['(no assignee recorded)']) for x in rest)
            src['removed'].append(dict(reason=f'Inventor named {a.inventor} but not assigned to {a.assignee}: ' + '; '.join(f'{k} ({v})' for k, v in by.most_common(8)),
                                       count=len(rest), examples=', '.join(num(x) for x in rest[:4]) + (' …' if len(rest) > 4 else '')))
            print(f'{len(rest)} more patents match the inventor name but not the assignee:')
            for x in rest[:40]: print('  ', brief(x))

def key(x):
    return ' '.join(words('; '.join(x.get('assigneeName') or ['(none)']))[:2])


print('\nAssignees in the set:')
for k, v in collections.Counter('; '.join(x.get('assigneeName') or ['(none)']) for x in final.values()).most_common(15):
    print(f'  {v:4d}  {k}')
print('Grant decades:', dict(sorted(collections.Counter((x.get('datePublished') or '????')[:3] + '0s' for x in final.values()).items())))
if final:
    top = collections.Counter(key(x) for x in final.values()).most_common(1)[0][0]
    odd = [x for x in final.values() if key(x) != top]
    if odd:
        print(f'{len(odd)} patents are not assigned to the majority assignee. In a number list these are usually foreign numbers or typos')
        print('that happen to match an unrelated US patent; in a search they may be legitimate. Check, then remove with curate.py:')
        for x in odd[:40]: print('  ', (x.get('datePublished') or 'no date')[:10], brief(x))
json.dump(final, open(a.work + '/meta/final.json', 'w'))
json.dump(src, open(a.work + '/meta/source.json', 'w'), indent=1)
