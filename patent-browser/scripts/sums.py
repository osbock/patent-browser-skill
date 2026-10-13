"""Parser for WORK/meta/sums.txt, the hand-written summaries. Format:

  #theme key|Label                      one line per theme, in display order
  @<any member number>|<theme key>|concept; concept; ...|Use-case area; Use-case area
  S: one-paragraph family summary
  U: use case; use case; use case
  <patent number>: what this patent's claim 1 covers      one line per family member
"""


def load_sums(path):
    """Returns (themes {key: label}, families {family id: entry}, focus {patent number: text})."""
    import json, os
    work = os.path.dirname(os.path.dirname(path))
    P = json.load(open(work + '/meta/grouped.json'))['patents']
    themes, fam, foc, cur = {}, {}, {}, None
    for i, line in enumerate(open(path), 1):
        line = line.rstrip('\n')
        if not line.strip(): continue
        try:
            if line.startswith('#theme '):
                k, v = line[7:].split('|'); themes[k.strip()] = v.strip()
            elif line.startswith('#'):
                continue
            elif line.startswith('@'):
                n, th, co, us = line[1:].split('|')
                fid = P[n.strip()]['fam']
                if fid in fam: raise ValueError('family written twice')
                cur = fam[fid] = dict(theme=th.strip(), concepts=[x.strip() for x in co.split(';') if x.strip()],
                                      useTags=[x.strip() for x in us.split(';') if x.strip()], summary='', uses=[])
            elif line.startswith('S: '):
                cur['summary'] = line[3:].strip()
            elif line.startswith('U: '):
                cur['uses'] = [x.strip() for x in line[3:].split(';') if x.strip()]
            else:
                n, t = line.split(': ', 1)
                if n not in P: raise ValueError('unknown patent number')
                if fam.get(P[n]['fam']) is not cur: raise ValueError('listed under the wrong family')
                if n in foc: raise ValueError('focus written twice')
                foc[n] = t.strip()
        except Exception as e:
            raise SystemExit(f'{path} line {i}: {e}: {line[:80]}')
    return themes, fam, foc
