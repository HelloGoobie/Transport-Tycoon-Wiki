#!/usr/bin/env python3
"""Build the wiki data files (data/*.json) from the editable sources in content/.

    python3 tools/build.py            # validate + rebuild data/
    python3 tools/build.py --check    # validate only, and fail if data/ is out of date

Source layout (see CONTRIBUTING.md):
    content/languages.json            languages the wiki can be translated INTO (code / names / translator code / rtl)
    content/aliases.json              redirects: "Old title" -> "Real title"
    content/EN/<Topic>/<Page>.html    one file per wiki page. Pages are written in English only;
                                      other languages are translated automatically in the browser.

Only the standard library is used.
"""
import argparse
import collections
import html.parser
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONTENT = os.path.join(ROOT, "content")
DATA = os.path.join(ROOT, "data")

# Elements that never have a closing tag.
VOID = {"br", "hr", "img", "wbr", "col"}
# Things a page must never contain: the app injects page HTML straight into the document.
BANNED_TAGS = {"script", "object", "embed", "style", "link", "meta", "base", "form", "input", "button", "svg", "math", "frame", "frameset"}


class FormatError(Exception):
    pass


# --------------------------------------------------------------------------- file format
def parse_page(text, where="page"):
    """Parse a content file into (title, categories, html)."""
    text = text.lstrip("﻿").replace("\r\n", "\n")
    if not text.startswith("---\n"):
        raise FormatError(f"{where}: file must start with a '---' header block")
    end = text.find("\n---\n", 4)
    if end < 0:
        raise FormatError(f"{where}: header block is not closed with '---'")
    head, body = text[4:end], text[end + 5:]
    title, cats, in_cats = None, [], False
    for line in head.split("\n"):
        if not line.strip():
            continue
        if line.startswith("title:"):
            title = line[6:].strip()
            in_cats = False
        elif line.startswith("categories:"):
            in_cats = True
            rest = line[11:].strip()
            if rest:
                raise FormatError(f"{where}: write categories as a list, one '  - Name' per line")
        elif in_cats and line.lstrip().startswith("- "):
            cats.append(line.lstrip()[2:].strip())
        else:
            raise FormatError(f"{where}: unexpected header line: {line!r}")
    if not title:
        raise FormatError(f"{where}: missing 'title:'")
    return title, cats, body.strip()


def format_page(title, cats, body):
    head = f"---\ntitle: {title}\n"
    if cats:
        head += "categories:\n" + "".join(f"  - {c}\n" for c in cats)
    return head + "---\n" + body.strip() + "\n"


# --------------------------------------------------------------------------- HTML checks
class _Check(html.parser.HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.stack, self.errors = [], []

    def handle_starttag(self, tag, attrs):
        if tag == "iframe":
            src = dict(attrs).get("src") or ""
            if src and not re.match(r"https://(www\.)?youtube(-nocookie)?\.com/embed/", src):
                self.errors.append("<iframe> is only allowed for YouTube embeds (https://www.youtube.com/embed/...)")
        elif tag in BANNED_TAGS:
            self.errors.append(f"<{tag}> is not allowed")
        for k, v in attrs:
            if k.startswith("on"):
                self.errors.append(f"attribute '{k}' is not allowed")
            if k in ("href", "src") and v and re.match(r"\s*(javascript|data|vbscript):", v, re.I):
                self.errors.append(f"{k}='{v[:30]}' is not allowed")
        if tag not in VOID:
            self.stack.append(tag)

    def handle_startendtag(self, tag, attrs):
        if tag in BANNED_TAGS:
            self.errors.append(f"<{tag}> is not allowed")
        for k, v in attrs:
            if k.startswith("on"):
                self.errors.append(f"attribute '{k}' is not allowed")

    def handle_endtag(self, tag):
        if tag in VOID:
            return
        if not self.stack:
            self.errors.append(f"stray </{tag}>")
        elif self.stack[-1] == tag:
            self.stack.pop()
        elif tag in self.stack:
            # Tolerate omitted </li>, </p>, </td>... the browser recovers, but a real mismatch is reported.
            skipped = []
            while self.stack[-1] != tag:
                skipped.append(self.stack.pop())
            self.stack.pop()
            if any(t not in ("li", "p", "td", "th", "tr", "dt", "dd", "tbody", "thead") for t in skipped):
                self.errors.append(f"</{tag}> closes unclosed <{skipped[-1]}>")
        else:
            self.errors.append(f"stray </{tag}>")


def check_html(body):
    c = _Check()
    c.feed(body)
    c.close()
    errs = list(c.errors)
    left = [t for t in c.stack if t not in ("li", "p", "td", "th", "tr", "dt", "dd")]
    if left:
        errs.append("unclosed <" + ">, <".join(left) + ">")
    return errs


def snippet(body):
    t = re.sub(r"<[^>]+>", " ", body)
    return re.sub(r"\s+", " ", t).strip()[:200]


# --------------------------------------------------------------------------- loading
def load_content():
    """Return (languages, aliases, pages) where pages is {"EN": [page dicts]}. Raises on bad input."""
    errors = []
    langs = json.load(open(os.path.join(CONTENT, "languages.json"), encoding="utf8"))
    aliases = json.load(open(os.path.join(CONTENT, "aliases.json"), encoding="utf8"))
    codes = {l["code"] for l in langs}
    for l in langs:
        for need in ("code", "name", "native", "tl"):
            if not l.get(need):
                errors.append(f"content/languages.json: language {l.get('code', '?')} is missing '{need}'")
    if len(codes) != len(langs):
        errors.append("content/languages.json: duplicate language code")
    pages = {"EN": []}
    seen = {}
    for lang in sorted(os.listdir(CONTENT)):
        d = os.path.join(CONTENT, lang)
        if not os.path.isdir(d):
            continue
        if lang != "EN":
            errors.append(f"content/{lang}/: only English pages live in content/EN/. Other languages are translated automatically.")
            continue
        for dp, _, fs in os.walk(d):
            for fn in sorted(fs):
                path = os.path.join(dp, fn)
                rel = os.path.relpath(path, ROOT).replace(os.sep, "/")
                if not fn.endswith(".html"):
                    errors.append(f"{rel}: pages must be .html files")
                    continue
                try:
                    title, cats, body = parse_page(open(path, encoding="utf8").read(), rel)
                except FormatError as e:
                    errors.append(str(e))
                    continue
                for e in check_html(body):
                    errors.append(f"{rel}: {e}")
                if len(re.sub(r"<[^>]+>", "", body).strip()) < 1:
                    errors.append(f"{rel}: page has no text")
                key = title
                if key.lower() in seen:
                    errors.append(f"{rel}: duplicate of {seen[key.lower()]} (same title)")
                    continue
                seen[key.lower()] = rel
                pages[lang].append({"k": key, "t": title, "c": cats, "h": body, "s": snippet(body), "_f": rel})
    if errors:
        raise FormatError("\n".join(errors))
    return langs, aliases, pages


def build_outputs(langs, aliases, pages):
    """Return {filename: json text} for everything that goes into data/."""
    out = {}
    for code, ps in pages.items():
        if not ps:
            continue
        ps = sorted(ps, key=lambda p: (p["t"].lower(), p["k"]))
        out[f"{code}.json"] = dump({"lang": code, "pages": [{k: p[k] for k in ("k", "t", "c", "h", "s")} for p in ps]})
    catc = collections.Counter(c for p in pages.get("EN", []) for c in p["c"])
    ordered = sorted(langs, key=lambda l: (l["code"] != "EN", l["name"].lower()))
    meta = {
        "langs": [dict({"code": l["code"], "name": l["name"], "native": l["native"], "tl": l["tl"]}, **({"rtl": True} if l.get("rtl") else {})) for l in ordered],
        "aliases": aliases,
        "cats": sorted(catc.items(), key=lambda kv: (-kv[1], kv[0])),
    }
    out["meta.json"] = dump(meta)
    return out


def dump(o):
    return json.dumps(o, ensure_ascii=False, separators=(",", ":"))


def broken_links(pages, aliases):
    """Warnings (not errors): internal links that point at a page that does not exist."""
    keys = {}
    for code, ps in pages.items():
        keys[code] = {p["t"].lower() for p in ps}
    alias_l = {a.lower() for a in aliases}
    warn = []
    for code, ps in pages.items():
        for p in ps:
            for m in re.finditer(r'data-p="([^"]+)"', p["h"]):
                t = m.group(1).replace("&amp;", "&")
                base = t.split(":", 1)[1] if ":" in t and t.split(":", 1)[0].upper() in keys and t.split(":", 1)[0].upper() != "EN" else t
                if base.lower() not in keys.get("EN", set()) and t.lower() not in keys.get(code, set()) and base.lower() not in keys.get(code, set()) and t.lower() not in alias_l:
                    warn.append(f"{p['_f']}: link to '{t}' matches no page")
    return list(dict.fromkeys(warn))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="validate only; fail if data/ is out of date")
    ap.add_argument("--links", action="store_true", help="also list internal links that match no page")
    a = ap.parse_args()
    try:
        langs, aliases, pages = load_content()
    except FormatError as e:
        print("Problems found:\n" + str(e), file=sys.stderr)
        return 1
    out = build_outputs(langs, aliases, pages)
    total = sum(len(v) for v in pages.values())
    if a.links:
        for w in broken_links(pages, aliases):
            print("warning:", w)
    if a.check:
        stale = [fn for fn, txt in out.items() if not os.path.exists(os.path.join(DATA, fn)) or open(os.path.join(DATA, fn), encoding="utf8").read() != txt]
        extra = [f for f in os.listdir(DATA) if f.endswith(".json") and f not in out] if os.path.isdir(DATA) else []
        print(f"{total} pages OK (English), translatable into {len(langs) - 1} languages.")
        if stale or extra:
            print("data/ is out of date: " + ", ".join(stale + extra) + "\nRun: python3 tools/build.py", file=sys.stderr)
            return 2
        return 0
    os.makedirs(DATA, exist_ok=True)
    for fn, txt in out.items():
        with open(os.path.join(DATA, fn), "w", encoding="utf8", newline="\n") as f:
            f.write(txt)
    for f in os.listdir(DATA):
        if f.endswith(".json") and f not in out:
            os.remove(os.path.join(DATA, f))
    print(f"Built {total} pages (English), translatable into {len(langs) - 1} languages -> data/")
    return 0


if __name__ == "__main__":
    sys.exit(main())
