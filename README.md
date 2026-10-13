# patent-browser

A Claude Code skill that builds a searchable, self-contained HTML browser for a set of US granted patents. Claude finds the patents at the USPTO, downloads their text and PDFs, groups them into families, writes a summary for each, and assembles the page.

## What you get

For a set named `<name>`, in the output directory:

| File | Contents |
|---|---|
| `<name>-patents.html` | One page with full-text search, filters (theme, use-case area, grant year, concept, inventor), index tabs for concepts, use cases and families, and an "About the data" tab. Each patent links to its local PDF, USPTO full text, USPTO PDF, Patent Center and Google Patents. |
| `<name>-patents.csv` | The same data as a table. |
| `<name>-pdfs/` | One USPTO PDF per patent. |
| `<name>-text/` | Full USPTO text (abstract, claims, description) per patent. |
| `.patent-work/<name>/` | Working data, including the hand-written summaries, so the page can be rebuilt and later sets can reuse them. |

The HTML page links to the PDFs by relative path, so keep it beside `<name>-pdfs/`.

## Requirements

- [Claude Code](https://claude.com/claude-code)
- Python 3 (standard library only)
- Network access to `ppubs.uspto.gov`

## Install

Clone the repository and copy the `patent-browser/` directory into your skills directory.

For all your projects:

```
git clone https://github.com/osbock/patent-browser-skill.git
mkdir -p ~/.claude/skills
cp -R patent-browser-skill/patent-browser ~/.claude/skills/patent-browser
```

For one project only, copy it into that project instead:

```
mkdir -p /path/to/project/.claude/skills
cp -R patent-browser-skill/patent-browser /path/to/project/.claude/skills/patent-browser
```

To track updates from the clone, symlink instead of copying:

```
ln -s "$(pwd)/patent-browser-skill/patent-browser" ~/.claude/skills/patent-browser
```

Start a new Claude Code session and check that `patent-browser` appears when you type `/`.

## Examples

Ask in plain language, or start the request with `/patent-browser`.

By inventor and assignee:

```
Build a patent browser for the patents of <inventor name> at <company>.
```

By assignee alone:

```
/patent-browser all granted patents assigned to <company>
```

By a USPTO Patent Public Search query:

```
/patent-browser patents matching the query: (beacon NEAR5 NFC).clm. AND <company>.as.
```

From a list of numbers, including a messy one with duplicates, application numbers and foreign filings:

```
/patent-browser summarize the patents listed in portfolio.csv
```

Adding a second set that overlaps an earlier one (summaries already written are reused):

```
/patent-browser build a set called "payments" from payments.csv, reusing the summaries from the earlier sets here
```

Claude reports the patent and family counts, what it left out and why, anything it flagged, and where the files are.

## Things to know

- Only granted US patents are searched, not pending applications.
- A common inventor name can match unrelated people, and foreign numbers in a list can coincide with unrelated US patents. Claude curates these and records every decision on the "About the data" tab; nothing is dropped silently.
- Summaries, concepts and use cases are Claude's reading of each patent's abstract and first claim. They are not a reading of the full specification and are not a legal scope analysis.
- Expect roughly 2 MB of downloads and a few seconds per patent.

## Running the scripts yourself

The scripts in `patent-browser/scripts/` can be run by hand with `python3 -I`. The steps, in order, are `search.py`, `curate.py`, `fetch.py`, `group.py`, `digest.py` and `build.py`; [`patent-browser/SKILL.md`](patent-browser/SKILL.md) documents each one and the format of the summaries file.
