---
name: patent-browser
description: Build a searchable HTML browser of US granted patents with per-patent summaries, concepts and use cases, PDFs and full text downloaded from the USPTO. Use when the user asks to summarize, catalogue or browse a set of patents found by inventor and/or assignee search, by a USPTO query, or from a list of patent numbers (including messy lists with duplicates and foreign filings).
---

# Patent browser

Produces, for a set of US granted patents:

- `<name>-patents.html` — one self-contained page: full-text search, filters (theme, use-case area, grant year, concept, inventor), index tabs for concepts, use cases and families, an "About the data" tab, and per-patent links to the local PDF, USPTO full text, USPTO PDF, Patent Center and Google Patents
- `<name>-patents.csv` — the same data as a table
- `<name>-pdfs/` — one USPTO PDF per patent, in its own directory
- `<name>-text/` — full USPTO text (abstract, claims, description) per patent

The scripts do the retrieval and assembly. The summaries are yours to write: you read each patent's abstract and first claim and write the family summary, concept tags, use cases and a claim-focus line per patent.

## Setup

Scripts are in `scripts/` beside this file; they need only Python 3 (standard library) and network access to `ppubs.uspto.gov`. Run them with `python3 -I`.

Pick a short lowercase `<name>` for the set (e.g. `dragonball`), the output directory `OUT` (default: the current project directory), and keep the work directory at `OUT/.patent-work/<name>`. The work directory is permanent: it holds your hand-written summaries, so later sets can reuse them and the page can be rebuilt.

```
K=<this skill's directory>/scripts
OUT=<output directory>
W=$OUT/.patent-work/<name>
```

## Steps

### 1. Decide the set

Inventor and/or assignee:

```
python3 -I $K/search.py $W --inventor "Joe Dragonball" --assignee "Z-corp"
```

`--inventor` matches first and last name in either order with a middle name allowed; `--assignee` matches the words as a phrase in the assignee or, for grants that record no assignee, the applicant. Either can be used alone. `--query '<BRS>'` adds or replaces with a raw Patent Public Search query (fields: `.in.` inventor, `.as.` assignee, `.ti.` title, `.ab.` abstract, `.clm.` claims, `.pn.` patent number, `.app.` application number as `"16/359334"`, `.cpc.`; operators `AND OR NOT ADJ NEARn`). Only granted patents (USPAT) are searched; say so if the user may expect pending applications.

A list of numbers:

```
python3 -I $K/search.py $W --numbers list.csv
```

Every row that looks like a US grant or application number is looked up at the USPTO; application numbers are resolved to their patents.

Then read the output and curate. Nothing is dropped silently — each decision is recorded and shown on the About tab:

- **Inventor + assignee search.** The script lists patents that match the inventor name but not the assignee. Common names match unrelated people; check the assignee list and, after step 3, the inventor's recorded name spellings and cities.
- **Number lists.** Foreign numbers often coincide with unrelated US patents (a 7-digit foreign registration matches a 1920s US patent; an EU design number without its suffix matches a random modern one). The script prints grant decades and every patent not assigned to the majority assignee. Remove the coincidences, and classify every row the script could not use:

```
python3 -I $K/curate.py $W --drop-granted-before 1976-01-01 --reason "Foreign 7-digit numbers that match old, unrelated US patents"
python3 -I $K/curate.py $W --drop 8170401 --reason "EU design number without its suffix; as a US number it is an unrelated patent"
python3 -I $K/curate.py $W --classify '^\d{9}-\d{4}$' --reason "EU registered design numbers"
python3 -I $K/curate.py $W --classify-rest --reason "…"
python3 -I $K/curate.py $W --flag 12670497 "Different assignee from the rest of the list; kept, may be a typo in the source."
python3 -I $K/curate.py $W --note "Inventor name" "Recorded as Joe Dragonball (82) and Joe David Dragonball (9); treated as one person."
```

  A country label you infer from a number's format is an inference: word the reason as "format matches …" unless the list states the jurisdiction. Keep a valid patent that looks out of place (different assignee) and `--flag` it rather than dropping it, unless it is clearly a coincidence. A number higher than the newest issued patent is not a grant yet.

The build refuses to run while any source row is unclassified.

### 2. Download text and PDFs

```
python3 -I $K/fetch.py $W $OUT/<name>-pdfs --reuse $OUT/*-pdfs
```

`--reuse` copies PDFs already downloaded for earlier sets instead of fetching them again. The USPTO returns occasional 504s; the script retries, and re-running fetches only what is missing. A number with no text and no PDF is probably withdrawn: drop it with `curate.py` and say so. Expect roughly 2 MB and a few seconds per patent.

The PDFs are page-image scans. Do not try to extract text from them; the full text comes from the USPTO text API and is what you read.

### 3. Group into families

```
python3 -I $K/group.py $W
```

Patents with the same title, or linked by continuity data with near-identical titles, become one family (continuations share a specification, so they share a summary). The output also shows how the USPTO records the searched inventor's name and city; if there are several, decide whether they are one person and record it with `curate.py --note`.

### 4. Write the summaries

Reuse earlier work first, if other sets exist under `OUT/.patent-work/`:

```
python3 -I $K/digest.py $W --seed $OUT/.patent-work/capsule $OUT/.patent-work/other
```

This starts `$W/meta/sums.txt` from the earlier sets for every family that shares a patent with them, and marks new members `TODO`. Then print what is left to write:

```
python3 -I $K/digest.py $W            # families still to write: abstract + claim 1 of each member
python3 -I $K/digest.py $W --from 0 --to 20    # in batches for large sets
```

Read it and write `$W/meta/sums.txt`:

```
#theme pay|Payments, tokens & checkout
#theme auth|Authentication & identity

@10616745|tap|beacon-triggered NFC; Bluetooth beacon; signal-strength threshold|Payments at POS; Loyalty, offers & content
S: A phone keeps its NFC application dormant until it hears a wireless beacon. It reads the beacon identifier, decides whether to wake the application, and then communicates with NFC tags inside the beacon's range.
U: Wake a phone's NFC reader on entering a store; Read in-store tags without opening an app first; Keep NFC off elsewhere to save power
10616745: Method: the phone reads a beacon identifier, decides from it whether to activate, and communicates with an NFC transmitter inside the beacon's range volume.
10798551: Broader method: on receiving a beacon signal the phone checks activation criteria and switches the NFC application on.
```

- `#theme key|Label` — 5 to 10 themes that divide this particular set sensibly; choose them after skimming the whole digest, not before. A seeded file brings its themes with it; add to them if the new families need it.
- `@<any member's number>|<theme key>|<concepts>|<use-case areas>` — one block per family. Concepts are 3–8 short technical tags, reused across families wherever the same mechanism recurs so the concept filter is useful. Use-case areas are 1–3 broad buckets from a small shared vocabulary (aim for under 20 across the set).
- `S:` — what the family's invention does and how, in one to three plain sentences. Describe the mechanism, not the legal form.
- `U:` — two to four concrete use cases, separated by semicolons (so no semicolons inside one).
- `<number>: …` — one line per member saying what that patent's claim 1 covers and how it differs from its siblings (who performs it — card, phone, server; which limitation is new). This is the part that makes a large continuation family navigable, so do not repeat the family summary here.

Writing rules:

- Write only what the abstract and claim support. Use cases are your reading of what the mechanism is for; keep them plausible and specific, and do not attribute them to the patent text.
- The digest cuts long claims to head and tail. When siblings look identical in the digest, raise `--len` or read the full claim in `$W/meta/docs/<number>.json` before writing the focus line; do not guess the difference.
- Read every family. Do not write a focus line from the title alone.
- For large sets write the file in batches and re-run `digest.py` to see what remains; it parses the file and reports format errors with line numbers.

### 5. Build and check

```
python3 -I $K/build.py $W $OUT --name <name> --title "Joe Dragonball patents (Z-corp)"
```

The build stops with a list if any family or patent lacks its entry, so a successful build means the summaries are complete. It reports missing PDFs, and counts per theme and use-case area: if one theme holds most of the set, or there are dozens of use-case areas, revise the tags and rebuild.

Open the page in a browser if one is available (headless Chrome with `--screenshot` works; URL state such as `#q=beacon` or `#view=about` is supported) and check the list, one search and the About tab.

The page links to PDFs by relative path, so it must stay beside `<name>-pdfs/`. For that reason do not publish it as a hosted artifact unless the user asks; it is a local file.

## Report to the user

State the counts (patents, families), what was left out and why, anything flagged for their attention, and where the files are. Also say plainly:

- summaries, concepts and use cases are your reading of the abstract and first claim, not of the full specification, and are not a legal scope analysis;
- any jurisdiction labels for removed foreign numbers are inferred from number formats;
- which summaries were reused from an earlier set, if any;
- what you checked on the built page and what you did not.
