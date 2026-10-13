"""Step 2: download full text (to WORK/meta/docs) and PDFs (to PDFDIR) from the USPTO.

  fetch.py WORK PDFDIR [--reuse DIR ...]

--reuse copies a PDF from an earlier output directory when it already holds the
same file name (USPTO PDFs are named by publication id, e.g. US10616745B2.pdf).
Safe to re-run: only missing files are fetched.
"""
import argparse, json, os, shutil, sys, time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ppubs import PP, pdf_bytes

ap = argparse.ArgumentParser()
ap.add_argument('work'); ap.add_argument('pdfdir'); ap.add_argument('--reuse', nargs='*', default=[])
a = ap.parse_args()
meta = json.load(open(a.work + '/meta/final.json'))
os.makedirs(a.work + '/meta/docs', exist_ok=True)
os.makedirs(a.pdfdir, exist_ok=True)
p, fail, copied, got = None, [], 0, 0
for k, x in sorted(meta.items()):
    f = f'{a.work}/meta/docs/{k}.json'
    if not os.path.exists(f):
        try:
            p = p or PP()
            json.dump(p.doc(x['guid']), open(f, 'w')); time.sleep(0.4)
        except Exception as e:
            fail.append(f'text {k}: {e}')
    name = x['guid'].replace('-', '') + '.pdf'
    f = os.path.join(a.pdfdir, name)
    if os.path.exists(f):
        continue
    for d in a.reuse:
        s = os.path.join(d, name)
        if os.path.exists(s) and open(s, 'rb').read(4) == b'%PDF':
            shutil.copy(s, f); copied += 1; break
    else:
        for i in range(5):
            try:
                b = pdf_bytes(k)
                open(f + '.part', 'wb').write(b); os.rename(f + '.part', f); got += 1; break
            except Exception as e:
                err = e; time.sleep(10 * (i + 1))
        else:
            fail.append(f'pdf {k}: {err}')
        time.sleep(1)
have = sum(os.path.exists(os.path.join(a.pdfdir, x['guid'].replace('-', '') + '.pdf')) for x in meta.values())
print(f'{len(meta)} patents: {len(os.listdir(a.work + "/meta/docs"))} text docs; PDFs {have} present ({copied} copied, {got} downloaded)')
if fail:
    print('FAILED (re-run to retry; a number with no text and no PDF is probably withdrawn):')
    for x in fail: print('  ', x)
    sys.exit(1)
