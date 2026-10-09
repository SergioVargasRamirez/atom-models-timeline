#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
build.py — regenerates index.html from template/index.template.html plus the
content files under content/.

Usage:
    python3 build.py

Sergio's workflow: edit a file under content/events, content/questions,
content/models, or one of content/tools.md, content/eras.md, content/ideas.md,
then run this script. It validates everything and rewrites index.html.
Any problem is reported with the exact file and field — nothing is silently
dropped or guessed.

This is a small, dependency-free frontmatter parser: it understands exactly
the subset of YAML the content files use (string, int, null, and a simple
list of strings). It is not a general YAML parser on purpose, so that a typo
fails loudly instead of being "creatively" interpreted.
"""
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
CONTENT = os.path.join(ROOT, "content")
TEMPLATE = os.path.join(ROOT, "template", "index.template.html")
OUT = os.path.join(ROOT, "index.html")

MIN_YEAR, MAX_YEAR = 1785, 1950
ERRORS = []


def fail(msg):
    ERRORS.append(msg)


def read_file(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


def split_frontmatter(path):
    text = read_file(path)
    m = re.match(r"^---\n(.*?)\n---\n?(.*)$", text, re.S)
    if not m:
        fail(f"{path}: fehlt ein gültiger Frontmatter-Block (--- ... ---)")
        return {}, ""
    return parse_yaml_block(m.group(1), path), m.group(2)


_STR_RE = re.compile(r'^"(.*)"$')


def _scalar(raw, path, key):
    raw = raw.strip()
    if raw == "" or raw == "null":
        return None
    m = _STR_RE.match(raw)
    if m:
        return m.group(1).replace('\\"', '"')
    # bare number
    if re.match(r"^-?\d+$", raw):
        return int(raw)
    fail(f"{path}: Feld '{key}' hat einen nicht erkannten Wert: {raw!r} "
         f"(Zeichenketten in Anführungszeichen setzen)")
    return raw


def parse_yaml_block(block, path):
    lines = block.split("\n")
    data = {}
    i = 0
    while i < len(lines):
        line = lines[i]
        if not line.strip():
            i += 1
            continue
        m = re.match(r"^([A-Za-z_äöüÄÖÜß][\w äöüÄÖÜß]*):\s*(.*)$", line)
        if not m:
            fail(f"{path}: Zeile {i+1} im Frontmatter nicht verständlich: {line!r}")
            i += 1
            continue
        key, rest = m.group(1).strip(), m.group(2)
        if rest.strip() == "":
            # could be a list on following lines, or an empty/null scalar
            items = []
            j = i + 1
            while j < len(lines) and re.match(r"^\s*-\s*(.*)$", lines[j]):
                im = re.match(r"^\s*-\s*(.*)$", lines[j])
                items.append(_scalar(im.group(1), path, key))
                j += 1
            if items:
                data[key] = items
                i = j
                continue
            data[key] = None
            i += 1
            continue
        if rest.strip() == "[]":
            data[key] = []
            i += 1
            continue
        data[key] = _scalar(rest, path, key)
        i += 1
    return data


def js_str(s):
    return json.dumps(s if s is not None else "", ensure_ascii=False)


def js_val(v):
    if v is None:
        return "null"
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, int):
        return str(v)
    return js_str(v)


def check_year(path, field, y):
    if y is None:
        fail(f"{path}: Pflichtfeld '{field}' fehlt")
        return
    if not (MIN_YEAR <= y <= MAX_YEAR):
        fail(f"{path}: {field}={y} liegt außerhalb des Zeitstrahls "
             f"({MIN_YEAR}–{MAX_YEAR})")


def require(d, path, *fields):
    for f in fields:
        if d.get(f) is None:
            fail(f"{path}: Pflichtfeld '{f}' fehlt oder ist leer")


LP_VALUES = {"k", "p"}


def check_lehrplan(d, path):
    lp = d.get("lehrplan")
    if lp is None:
        return
    if lp not in LP_VALUES:
        fail(f"{path}: Feld 'lehrplan' muss 'k' oder 'p' sein, nicht {lp!r}")
    if not d.get("lehrplan_text"):
        fail(f"{path}: 'lehrplan' ist gesetzt, aber 'lehrplan_text' fehlt")


# ---------- load events ----------
def load_events():
    out = []
    ids = {}
    d_events = os.path.join(CONTENT, "events")
    for name in sorted(os.listdir(d_events)):
        if not name.endswith(".md"):
            continue
        path = os.path.join(d_events, name)
        fm, body = split_frontmatter(path)
        require(fm, path, "id", "jahr", "spur", "art", "kurz", "personen")
        check_year(path, "jahr", fm.get("jahr"))
        check_lehrplan(fm, path)
        art_map = {"modell": "model", "entdeckung": "disc", "hinweis": "hint", "treffen": "meet"}
        art = fm.get("art")
        if art is not None and art not in art_map:
            fail(f"{path}: 'art' muss eines von {sorted(art_map)} sein, nicht {art!r}")
        spur_map = {"M", "E", "S", "R", "C", "P"}
        if fm.get("spur") is not None and fm.get("spur") not in spur_map:
            fail(f"{path}: 'spur' muss eines von {sorted(spur_map)} sein, nicht {fm.get('spur')!r}")
        nid = fm.get("id")
        if nid:
            if nid in ids:
                fail(f"{path}: id '{nid}' ist nicht eindeutig (auch in {ids[nid]})")
            ids[nid] = path
        out.append({
            "id": nid,
            "y": fm.get("jahr"),
            "tr": fm.get("spur"),
            "k": art_map.get(art, art),
            "s": fm.get("kurz"),
            "who": fm.get("personen"),
            "txt": body.strip(),
            "needs": fm.get("voraussetzungen"),
            "rel": fm.get("bezug"),
            "lehrplan": fm.get("lehrplan"),
            "lehrplan_text": fm.get("lehrplan_text"),
            "geprüft": fm.get("geprüft"),
            "_path": path,
        })
    return out, ids


def load_questions(known_ids):
    out = []
    ids = {}
    d_q = os.path.join(CONTENT, "questions")
    for name in sorted(os.listdir(d_q)):
        if not name.endswith(".md"):
            continue
        path = os.path.join(d_q, name)
        fm, body = split_frontmatter(path)
        require(fm, path, "id", "von", "bis", "kurz", "beantwortet_durch")
        check_year(path, "von", fm.get("von"))
        check_year(path, "bis", fm.get("bis"))
        check_lehrplan(fm, path)
        qid = fm.get("id")
        if qid:
            if qid in ids:
                fail(f"{path}: id '{qid}' ist nicht eindeutig (auch in {ids[qid]})")
            ids[qid] = path
        out.append({
            "id": qid,
            "from": fm.get("von"),
            "to": fm.get("bis"),
            "s": fm.get("kurz"),
            "by": fm.get("beantwortet_durch"),
            "txt": body.strip(),
            "lehrplan": fm.get("lehrplan"),
            "lehrplan_text": fm.get("lehrplan_text"),
            "geprüft": fm.get("geprüft"),
            "_path": path,
        })
    return out, ids


CHAIN_ROW_RE = re.compile(r"^\|(.+)\|(.+)\|(.+)\|(.+)\|$")


def parse_body_model(body, path):
    sections = re.split(r"(?m)^## (.+)$", body)
    # sections[0] is leading text before first heading (ignored)
    secs = {}
    for i in range(1, len(sections), 2):
        title = sections[i].strip()
        content = sections[i + 1].strip() if i + 1 < len(sections) else ""
        secs[title] = content

    def bullets(text):
        return [l[2:].strip() for l in text.split("\n") if l.strip().startswith("- ")]

    know = bullets(secs.get("Das wusste man", ""))
    good = secs.get("Was das Modell gut konnte", "").strip()
    notyet = bullets(secs.get("Fragen, die man noch nicht stellen konnte", ""))

    chain = []
    chain_text = secs.get("Voraussetzungen für ein besseres Modell", "")
    for line in chain_text.split("\n"):
        line = line.strip()
        if not line.startswith("|") or line.startswith("|---"):
            continue
        m = CHAIN_ROW_RE.match(line)
        if not m:
            continue
        cells = [c.strip() for c in m.groups()]
        if cells[0] in ("Nötig für das bessere Modell",):
            continue
        noetig, voraussetzt, zeitraum, jahr = cells
        try:
            jahr_i = int(jahr)
        except ValueError:
            fail(f"{path}: Jahr in der Kette '{jahr}' ist keine Zahl")
            jahr_i = MIN_YEAR
        chain.append([noetig, voraussetzt, zeitraum, jahr_i])

    if not know:
        fail(f"{path}: Abschnitt 'Das wusste man' fehlt oder ist leer")
    if not good:
        fail(f"{path}: Abschnitt 'Was das Modell gut konnte' fehlt oder ist leer")
    if not notyet:
        fail(f"{path}: Abschnitt 'Fragen, die man noch nicht stellen konnte' fehlt oder ist leer")
    if not chain:
        fail(f"{path}: Tabelle 'Voraussetzungen für ein besseres Modell' fehlt oder ist leer")

    note = None
    note_title_used = None
    rival_note = None
    for title, content in secs.items():
        if title in ("Das wusste man", "Was das Modell gut konnte",
                      "Fragen, die man noch nicht stellen konnte",
                      "Voraussetzungen für ein besseres Modell"):
            continue
        if title == "Konkurrenz im selben Jahr":
            rival_note = content
        else:
            note = content
            note_title_used = title
    return know, good, notyet, chain, note, note_title_used, rival_note


def load_models(event_ids):
    out = {}
    d_m = os.path.join(CONTENT, "models")
    for name in sorted(os.listdir(d_m)):
        if not name.endswith(".md"):
            continue
        path = os.path.join(d_m, name)
        fm, body = split_frontmatter(path)
        require(fm, path, "id", "jahr", "verdict")
        check_year(path, "jahr", fm.get("jahr"))
        mid = fm.get("id")
        if mid and mid not in event_ids:
            fail(f"{path}: Modell-id '{mid}' hat kein passendes Ereignis in content/events/")
        know, good, notyet, chain, note, note_title, rival_note = parse_body_model(body, path)
        m = {
            "know": know, "good": good, "notyet": notyet, "chain": chain,
            "verdict": fm.get("verdict"),
            "resolved": fm.get("resolved") or [],
            "geprüft": fm.get("geprüft"),
        }
        if fm.get("hinweis_titel") or note_title:
            m["noteTitle"] = fm.get("hinweis_titel") or note_title
        if note:
            m["note"] = note
        if fm.get("konkurrenz"):
            m["rivals"] = fm.get("konkurrenz")
        if rival_note:
            m["rivalNote"] = rival_note
        if mid:
            out[mid] = m
    return out


def load_table_file(name, cols, path_label):
    path = os.path.join(CONTENT, name)
    fm, body = split_frontmatter(path)
    rows = []
    for line in body.split("\n"):
        line = line.strip()
        if not line.startswith("|") or line.startswith("|---"):
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if cells == cols or all(c in cols for c in cells[:1]):
            # header row (matches column names) — skip
            if cells[0] == cols[0]:
                continue
        rows.append(cells)
    return fm, rows, path


def load_tools():
    fm, rows, path = load_table_file("tools.md", ["Jahr", "Werkzeug", "Art"], "tools.md")
    out = []
    for cells in rows:
        if len(cells) < 3:
            fail(f"{path}: Zeile mit zu wenigen Spalten: {cells!r}")
            continue
        jahr, name, art = cells[0], cells[1], cells[2]
        try:
            jahr_i = int(jahr)
        except ValueError:
            fail(f"{path}: Jahr '{jahr}' ist keine Zahl")
            continue
        check_year(path, "Jahr", jahr_i)
        if art not in ("i", "k"):
            fail(f"{path}: Art '{art}' muss 'i' oder 'k' sein (Zeile: {name})")
        out.append([jahr_i, name, art])
    return fm.get("geprüft"), out


def load_eras():
    fm, rows, path = load_table_file("eras.md", ["Von", "Bis", "Modell", "Erklärung"], "eras.md")
    out = []
    for cells in rows:
        if len(cells) < 4:
            fail(f"{path}: Zeile mit zu wenigen Spalten: {cells!r}")
            continue
        von, bis, modell, erkl = cells[0], cells[1], cells[2], cells[3]
        try:
            von_i, bis_i = int(von), int(bis)
        except ValueError:
            fail(f"{path}: Von/Bis '{von}'/'{bis}' ist keine Zahl")
            continue
        check_year(path, "Von", von_i)
        check_year(path, "Bis", bis_i)
        out.append({"f": von_i, "t": bis_i, "m": modell, "x": erkl})
    return fm.get("geprüft"), out


def load_ideas():
    fm, rows, path = load_table_file(
        "ideas.md", ["Idee", "Nötige Messung/Beobachtung", "Gerät/Methode", "Zeitraum", "Jahr"], "ideas.md")
    out = []
    for cells in rows:
        if len(cells) < 5:
            fail(f"{path}: Zeile mit zu wenigen Spalten: {cells!r}")
            continue
        idee, messung, geraet, zeitraum, jahr = cells[:5]
        try:
            jahr_i = int(jahr)
        except ValueError:
            fail(f"{path}: Jahr '{jahr}' ist keine Zahl")
            continue
        check_year(path, "Jahr", jahr_i)
        out.append([idee, messung, geraet, zeitraum, jahr_i])
    return fm.get("geprüft"), out


def check_cross_refs(events, event_ids, questions, question_ids, models):
    for e in events:
        for ref in (e.get("rel") or []):
            if ref not in event_ids:
                fail(f"{e['_path']}: 'bezug' verweist auf unbekannte id '{ref}'")
    for q in questions:
        by = q.get("by")
        if by and by not in event_ids:
            fail(f"{q['_path']}: 'beantwortet_durch' verweist auf unbekannte id '{by}'")
    for mid, m in models.items():
        for ref in m.get("resolved", []):
            if ref not in event_ids:
                fail(f"content/models (id={mid}): 'resolved' verweist auf unbekannte id '{ref}'")
        for ref in m.get("rivals", []):
            if ref not in event_ids:
                fail(f"content/models (id={mid}): 'konkurrenz' verweist auf unbekannte id '{ref}'")
        for row in m["chain"]:
            pass  # chain rows are free text + year, no id cross-ref to check


def main():
    if not os.path.isdir(CONTENT):
        print(f"FEHLER: content/-Ordner fehlt unter {CONTENT}", file=sys.stderr)
        sys.exit(1)

    events, event_ids = load_events()
    questions, question_ids = load_questions(event_ids)
    models = load_models(event_ids)
    tools_reviewed, tools = load_tools()
    eras_reviewed, eras = load_eras()
    ideas_reviewed, ideas = load_ideas()
    check_cross_refs(events, event_ids, questions, question_ids, models)

    if ERRORS:
        print(f"build.py: {len(ERRORS)} Fehler gefunden, index.html wurde NICHT geschrieben:\n", file=sys.stderr)
        for e in ERRORS:
            print(" - " + e, file=sys.stderr)
        sys.exit(1)

    def node_js(n):
        fields = {"id": n["id"], "y": n["y"], "tr": n["tr"], "k": n["k"], "s": n["s"],
                  "who": n["who"], "txt": n["txt"]}
        extra = {}
        if n.get("needs"):
            extra["needs"] = n["needs"]
        if n.get("rel"):
            extra["rel"] = n["rel"]
        if n.get("lehrplan"):
            extra["lehrplan"] = n["lehrplan"]
            extra["lehrplan_text"] = n["lehrplan_text"]
        extra["geprüft"] = n.get("geprüft")
        parts = ",".join(js_val(fields[k]) for k in ["id", "y", "tr", "k", "s", "who", "txt"])
        ex = "{" + ",".join(f"{k}:{js_val(v)}" if not isinstance(v, list) else
                             f"{k}:[" + ",".join(js_val(x) for x in v) + "]"
                             for k, v in extra.items()) + "}"
        return f"N({parts},{ex})"

    nodes_js = "[\n" + ",\n".join(node_js(n) for n in events) + "\n]"

    def q_js(q):
        obj = {"id": q["id"], "from": q["from"], "to": q["to"], "s": q["s"], "by": q["by"], "txt": q["txt"]}
        if q.get("lehrplan"):
            obj["lehrplan"] = q["lehrplan"]
            obj["lehrplan_text"] = q["lehrplan_text"]
        obj["geprüft"] = q.get("geprüft")
        return "{" + ",".join(f"{k}:{js_val(v)}" for k, v in obj.items()) + "}"

    qs_js = "[\n" + ",\n".join(q_js(q) for q in questions) + "\n]"

    tools_js = "[\n" + ",\n".join(
        "[" + f"{t[0]},{js_val(t[1])},{js_val(t[2])}" + "]" for t in tools) + "\n]"

    eras_js = "[\n" + ",\n".join(
        "{" + f"f:{e['f']},t:{e['t']},m:{js_val(e['m'])},x:{js_val(e['x'])}" + "}" for e in eras) + "\n]"

    def model_js(mid, m):
        parts = [f"know:[" + ",".join(js_val(x) for x in m["know"]) + "]",
                 f"good:{js_val(m['good'])}",
                 f"notyet:[" + ",".join(js_val(x) for x in m["notyet"]) + "]",
                 "chain:[" + ",".join(
                     "[" + ",".join(js_val(c) for c in row[:3]) + f",{row[3]}" + "]"
                     for row in m["chain"]) + "]"]
        if m.get("noteTitle"):
            parts.append(f"noteTitle:{js_val(m['noteTitle'])}")
        if m.get("note"):
            parts.append(f"note:{js_val(m['note'])}")
        if m.get("rivals"):
            parts.append("rivals:[" + ",".join(js_val(x) for x in m["rivals"]) + "]")
        if m.get("rivalNote"):
            parts.append(f"rivalNote:{js_val(m['rivalNote'])}")
        parts.append(f"verdict:{js_val(m['verdict'])}")
        parts.append("resolved:[" + ",".join(js_val(x) for x in m["resolved"]) + "]")
        parts.append(f"geprüft:{js_val(m.get('geprüft'))}")
        return mid + ":{" + ",".join(parts) + "}"

    models_js = "{\n" + ",\n".join(model_js(mid, m) for mid, m in models.items()) + "\n}"

    ideas_js = "[\n" + ",\n".join(
        "[" + ",".join(js_val(c) for c in row[:4]) + f",{row[4]}" + "]" for row in ideas) + "\n]"

    n_reviewed = sum(1 for n in events if n.get("geprüft")) + sum(1 for q in questions if q.get("geprüft"))
    n_total = len(events) + len(questions)

    if not os.path.isfile(TEMPLATE):
        print(f"FEHLER: Template fehlt unter {TEMPLATE}", file=sys.stderr)
        sys.exit(1)
    tpl = read_file(TEMPLATE)

    replacements = {
        "/*__NODES__*/": nodes_js,
        "/*__QS__*/": qs_js,
        "/*__TOOLS__*/": tools_js,
        "/*__ERAS__*/": eras_js,
        "/*__MODELS__*/": models_js,
        "/*__IDEAS__*/": ideas_js,
        "/*__REVIEW_COUNT__*/": str(n_reviewed),
        "/*__REVIEW_TOTAL__*/": str(n_total),
    }
    missing = [k for k in replacements if k not in tpl]
    if missing:
        print(f"FEHLER: Template-Platzhalter fehlen: {missing}", file=sys.stderr)
        sys.exit(1)
    for k, v in replacements.items():
        tpl = tpl.replace(k, v)

    with open(OUT, "w", encoding="utf-8") as f:
        f.write(tpl)

    print(f"OK: index.html geschrieben ({len(events)} Ereignisse, {len(questions)} Fragen, "
          f"{len(models)} Modelle, {len(tools)} Werkzeuge, {len(eras)} Epochen, {len(ideas)} Ideen).")
    print(f"Geprüft: {n_reviewed}/{n_total} Ereignisse und Fragen.")


if __name__ == "__main__":
    main()
