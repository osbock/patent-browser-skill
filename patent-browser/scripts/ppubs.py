"""Minimal client for USPTO Patent Public Search (ppubs.uspto.gov). Standard library only."""
import json, time, urllib.request

UA = {'User-Agent': 'Mozilla/5.0', 'Content-Type': 'application/json',
      'Origin': 'https://ppubs.uspto.gov', 'Referer': 'https://ppubs.uspto.gov/pubwebapp/'}
API = 'https://ppubs.uspto.gov/api'
PDF = 'https://image-ppubs.uspto.gov/dirsearch-public/print/downloadPdf/'


class PP:
    def __init__(self):
        self.login()

    def login(self):
        r = urllib.request.urlopen(urllib.request.Request(API + '/users/me/session', data=b'-1', headers=UA), timeout=60)
        self.tok = r.headers['X-Access-Token']
        self.case = json.load(r)['userCase']['caseId']

    def req(self, path, data=None):
        for i in range(6):
            try:
                h = dict(UA)
                h['X-Access-Token'] = self.tok
                body = json.dumps(data).encode() if data is not None else None
                return json.load(urllib.request.urlopen(urllib.request.Request(API + path, data=body, headers=h), timeout=120))
            except Exception as e:
                err = e
                time.sleep(3 + 5 * i)
                if getattr(e, 'code', 0) in (401, 403):
                    self.login()
        raise err

    def search_page(self, q, start=0, n=500, dbs=('USPAT',)):
        d = {"start": start, "pageCount": n, "sort": "date_publ desc", "docFamilyFiltering": "noFiltering",
             "searchType": 1, "familyIdEnglishOnly": True, "familyIdFirstPreferred": "US-PGPUB",
             "familyIdSecondPreferred": "USPAT", "familyIdThirdPreferred": "FPRS",
             "showDocPerFamilyPref": "showEnglish", "queryId": 0, "tagDocSearch": False,
             "query": {"caseId": self.case, "hl_snippets": "2", "op": "OR", "q": q, "queryName": q,
                       "highlights": "0", "qt": "brs", "spellCheck": False, "viewName": "tile", "plurals": True,
                       "britishEquivalents": True,
                       "databaseFilters": [{"databaseName": x, "countryCodes": []} for x in dbs],
                       "searchType": 1, "ignorePersist": True, "userEnteredQuery": q}}
        return self.req('/searches/searchWithBeFamily', d)

    def search(self, q, dbs=('USPAT',)):
        """All results for a BRS query, as a list of result records."""
        out, start = [], 0
        while True:
            r = self.search_page(q, start, 500, dbs)
            if r.get('error'):
                raise RuntimeError(f"USPTO rejected query {q!r}: {r['error']}")
            got = r.get('patents') or []
            out += got
            start += len(got)
            if not got or start >= (r.get('numFound') or 0):
                return out

    def doc(self, guid, src='USPAT'):
        return self.req(f'/patents/highlight/{guid}?queryId=1&source={src}&includeSections=true&uniqueId=')


def pdf_bytes(number):
    b = urllib.request.urlopen(urllib.request.Request(PDF + number, headers={'User-Agent': 'Mozilla/5.0'}), timeout=180).read()
    if b[:4] != b'%PDF' or len(b) < 20000:
        raise ValueError('not a PDF')
    return b
