# Contributing to the Tycoon Gaming Wiki

Thanks for helping keep the wiki up to date! Every page is a single file in [`content/`](content), so you can fix a typo or update a list without touching anything else.

## Quick edit (no tools needed)

1. Find the page. Press <kbd>t</kbd> on the repo's GitHub page and type the page name, or browse `content/EN/<Topic>/`.
   - Staff list: [`content/EN/Other/Credits.html`](content/EN/Other/Credits.html)
2. Click the **pencil** icon (Edit this file).
3. Make your change, then press **Commit changes** and choose **Create a new branch / open a pull request**.
4. A check runs on your PR. If it shows a red cross, open it to see what to fix.

That's it. When a maintainer merges the PR, the site rebuilds itself automatically.

## Where things live

```
content/
  languages.json        the list of languages
  aliases.json          redirects (old name -> real page name)
  EN/                   English pages
    Jobs/Airline Pilot.html
    Items/...
    Other/Credits.html
  DE/ PL/ FR/ ...       translations, one folder per language code
data/                   GENERATED. Do not edit by hand.
tools/build.py          builds data/ from content/
index.html              the wiki app
```

The topic folders (`Jobs`, `Items`, ...) are only there to keep things tidy. The page's real title and categories come from the header inside the file, so you can move a file between folders freely.

## Page file format

```html
---
title: Airline Pilot
categories:
  - Jobs
  - Piloting
---
<p><b>Airline Pilot</b> is one of the jobs available in Transport Tycoon...</p>
<h2 id="Getting_Started">Getting Started</h2>
<p>...</p>
```

- The **header** (between the `---` lines) has the page `title` and a list of `categories`.
- Everything below it is the page body, written in simple **HTML**.
- Other languages use the same format. The file lives in that language's folder (for example `content/DE/...`) and the `title` is the page name **without** the language prefix.

### HTML you can use

| You want | Write |
|---|---|
| Paragraph | `<p>Text</p>` |
| Headings (they build the contents list) | `<h2 id="Name">Name</h2>`, `<h3>`, `<h4>` |
| Bold / italic | `<b>bold</b>`, `<i>italic</i>` |
| Bullet / numbered list | `<ul><li>One</li></ul>`, `<ol><li>One</li></ol>` |
| Table | `<table><tr><th>Head</th></tr><tr><td>Cell</td></tr></table>` |
| Link to another wiki page | `<a data-p="Job Center">Job Center</a>` |
| Link to a section of a page | `<a data-p="Job Center" data-f="Section_Name">text</a>` |
| Link to a section on the same page | `<a data-a="Section_Name">text</a>` |
| External link | `<a href="https://example.com" target="_blank" rel="noopener">text</a>` |

Wiki links use `data-p="Page title"` rather than `href`. The title is the page's `title:` header. In a translation, link to the translated page the same way.

### Not allowed

`<script>`, `<style>`, `<form>`, `<svg>`, event attributes such as `onclick`, and `javascript:` links are rejected by the check. Embedded `<iframe>`s are only allowed for YouTube (`https://www.youtube.com/embed/...`). The wiki has no images.

## Adding a new page

1. Create `content/EN/<Topic>/<Page name>.html` (use **Add file** on GitHub). Pick the topic folder that fits, or `Other`.
2. Start it with the header:
   ```
   ---
   title: My New Page
   categories:
     - Jobs
   ---
   <p>Page text...</p>
   ```
3. Titles must be unique within a language. Don't use `/ \ : * ? " < > |` in the **file name** (the title itself can contain them).

To make a page reachable under another name, add a redirect to [`content/aliases.json`](content/aliases.json), for example `"Car Dealer": "Vehicle Shop"`.

## Renaming or deleting a page

Change `title:` in the header (and rename the file to match, if you like). Remember to update links to it (`data-p="..."`) in other pages. To delete a page, delete its file.

## Adding a language

1. Add the language to [`content/languages.json`](content/languages.json) (`code`, English `name`, `native` name).
2. Create `content/<CODE>/` and add pages.

## Working locally (optional)

Python 3 is the only requirement.

```bash
python3 tools/build.py            # check everything and rebuild data/
python3 tools/build.py --check    # check only
python3 tools/build.py --links    # also list links that point at a page that doesn't exist
python3 -m http.server            # then open http://localhost:8000/#/EN/home
```

You don't have to run the build for a PR. The `data/` folder is rebuilt automatically after merge, so please leave it out of your changes.
