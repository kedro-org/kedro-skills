#!/usr/bin/env python3
"""Build a self-contained HTML dashboard from a kedro-quality-review results.json.

Usage: build_dashboard.py RESULTS_JSON OUTPUT_HTML [--open]

The page is built like a small component tree. Every component is a function that returns an HTML
string, and the component's styles sit in a CSS_<NAME> constant right above it. Standard library only.

Where to change what
--------------------
  Colours, header yellow, page width, gutter ... DESIGN TOKENS      (DARK_THEME, LIGHT_THEME, LAYOUT)
  Fonts, page background, text helpers ......... BASE
  Logo, title, rules line .................... Header, Brand       (CSS_HEADER)
  Search box ................................. SearchBox           (CSS_HEADER)
  Pass / Mixed / Fail filter buttons ......... StatusFilter        (CSS_HEADER)
  Opening verdict and score numeral .......... Hero                (CSS_HERO)
  Coloured segment bar ....................... SegmentBar          (CSS_SEGMENTS)
  Group scoreboard under the verdict ......... Scoreboard          (CSS_BOARD)
  Group heading + score above each table ..... GroupBand           (CSS_BAND)
  Table, rows, status badge .................. CriteriaTable, CriterionRow, StatusBadge (CSS_TABLE)
  Click-to-open rule and evidence ............ Toggle, Collapse, RuleDetails (CSS_COLLAPSE)
  Search, filters and open/close behaviour ... SCRIPT
  Wording of labels .......................... LABELS
"""
import argparse
import html
import json
import sys
import webbrowser
from pathlib import Path

E = html.escape


GROUPS = ("functional_appropriateness", "performance_efficiency", "maintainability")
STATUSES = ("pass", "mixed", "fail")
LABELS = {"pass": "Pass", "mixed": "Mixed", "fail": "Fail", "optional": "Nice to have"}
ICONS = {
    "pass": '<path d="M3 8.5l3.2 3L13 4.5"/>',
    "mixed": '<path d="M3.5 8h9"/>',
    "fail": '<path d="M4 4l8 8M12 4l-8 8"/>',
    "optional": '<circle cx="8" cy="8" r="4"/>',
}


DARK_THEME = {
    "surface": "#0f0f11",      # page background
    "band": "#141516",         # every second section
    "card": "#1e1f21",         # cards and tables
    "ink": "#d9dcde",          # main text
    "ink2": "#989898",         # secondary text
    "grid": "#2b2d2f",         # borders and dividers
    "hover": "rgba(255,255,255,.08)",
    "focus": "#FFC900",        # keyboard focus ring
    "pass": "#5e6c74", "mixed": "#ffbc00", "fail": "#f03b3a", "optional": "#989898",              # fills (pass is neutral on purpose)
    "pass-t": "#989898", "mixed-t": "#ffbc00", "fail-t": "#f03b3a", "optional-t": "#989898",      # text
}
LIGHT_THEME = {
    "surface": "#f2f3f4", "band": "#ecedef", "card": "#fdfdfd",
    "ink": "#151515", "ink2": "#636363", "grid": "#d9dcde", "hover": "rgba(0,0,0,.06)", "focus": "#151515",
    "pass": "#abb2b7", "mixed": "#ffbc00", "fail": "#dc3938", "optional": "#717d84",
    "pass-t": "#636363", "mixed-t": "#7d5c00", "fail-t": "#dc3938", "optional-t": "#636363",
}
LAYOUT = {
    "content-max": "1200px",   # width of the centred content column
    "radius": "8px",           # hover areas and filter buttons. Set to 0 for sharp corners.
    "radius-lg": "16px",       # the overview box
    "gutter": "48px",          # minimum side padding, and the vertical padding of each section
    "header-bg": "#F7CA46",    # yellow header
    "header-ink": "#151515",
    "header-strong": "rgba(21,21,21,.7)",
    "header-muted": "rgba(21,21,21,.65)",
    "header-line": "rgba(21,21,21,.4)",
    "header-hover": "rgba(21,21,21,.08)",
}


def _vars(tokens):
    return "".join(f"--{k}:{v};" for k, v in tokens.items())


CSS_TOKENS = (f":root{{color-scheme:dark;{_vars(DARK_THEME)}{_vars(LAYOUT)}}}\n"
              f"@media(prefers-color-scheme:light){{:root{{color-scheme:light;{_vars(LIGHT_THEME)}}}}}")

# ======================================================================================================
# BASE: reset, page, typography helpers
# ======================================================================================================
CSS_BASE = """
* {
  box-sizing: border-box;
}

[hidden] {
  display: none !important;
}

html,
body {
  height: 100%;
}

body {
  margin: 0;
  display: grid;
  grid-template-columns: minmax(0, 1fr);
  background: var(--surface);
  color: var(--ink);
  font: 400 14px/1.43 Inter, system-ui, sans-serif;
  letter-spacing: -.028px;
  overflow: hidden;
}

main {
  overflow: auto;
  min-width: 0;
  scroll-behavior: smooth;
  scroll-padding-top: 88px;
}

.sub {
  color: var(--ink2);
  font-size: 12px;
  line-height: 1.33;
  letter-spacing: .024px;
}

.t {
  color: var(--ink2);
}

.stack {
  display: flex;
  flex-direction: column;
  gap: 32px;
  min-width: 0;
}

.ic {
  width: 16px;
  height: 16px;
  flex: none;
}

@media (prefers-reduced-motion: reduce) {
  * {
    transition: none !important;
  }

  main {
    scroll-behavior: auto;
  }
}

@media (max-width: 900px) {
  body {
    overflow: auto;
    height: auto;
  }

  main {
    overflow: visible;
  }
}
"""

# ======================================================================================================
# Header: Brand, SearchBox, StatusFilter
# ======================================================================================================
CSS_HEADER = """
.bar {
  position: sticky;
  top: 0;
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 12px 24px;
  background: var(--header-bg);
  color: var(--header-ink);
  padding: 16px 32px;
}

.hd {
  flex: 1 1 320px;
  min-width: 0;
}

.brand {
  display: flex;
  align-items: center;
  gap: 8px 16px;
}

.logo {
  flex: none;
}

.proj {
  padding-left: 16px;
  border-left: 1px solid var(--header-line);
  min-width: 0;
}

.proj h1 {
  margin: 0;
  font-size: 16px;
  font-weight: 400;
  line-height: 1.5;
  letter-spacing: -.032px;
  overflow-wrap: anywhere;
}

.meta {
  margin-top: 2px;
  font-size: 12px;
  line-height: 1.33;
  letter-spacing: .024px;
  color: var(--header-strong);
  white-space: nowrap;
}

.tools {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 12px 8px;
  max-width: 100%;
}

/* Search is a single underline, not a box. */
.search {
  display: flex;
  align-items: center;
  gap: 8px;
  width: 220px;
  max-width: 100%;
  margin-right: 16px;
  padding: 0 2px;
  border-bottom: 1px solid var(--header-strong);
  color: var(--header-muted);
}

.search input {
  flex: 1;
  min-width: 0;
  height: 34px;
  background: none;
  border: 0;
  color: var(--header-ink);
  font: inherit;
  font-size: 14px;
  outline: 0;
}

.search input::placeholder {
  color: var(--header-muted);
}

.search:focus-within {
  border-bottom-color: var(--header-ink);
  box-shadow: 0 1px 0 var(--header-ink);
}

.chips {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}

/* Status filters are plain toggles. A struck-through label means that status is hidden. */
.f {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  min-height: 36px;
  padding: 0 10px;
  background: none;
  border: 0;
  border-radius: var(--radius);
  color: var(--header-ink);
  font: inherit;
  font-size: 14px;
  cursor: pointer;
  transition: background-color .2s;
}

.f:hover {
  background: var(--header-hover);
}

.f:focus-visible {
  outline: 2px solid var(--header-ink);
  outline-offset: 1px;
}

.f i {
  display: inline-block;
  width: 8px;
  height: 8px;
  background: var(--optional);
  box-shadow: 0 0 0 1px var(--header-strong);
}

.f .n {
  color: var(--header-muted);
  font-variant-numeric: tabular-nums;
}

.f.pass i {
  background: var(--pass);
}

.f.mixed i {
  background: var(--mixed);
}

.f.fail i {
  background: var(--fail);
}

.f.optional i {
  background: none;
}

.f[aria-pressed=false] {
  color: var(--header-muted);
  text-decoration: line-through;
}

.f[aria-pressed=false] i {
  background: none !important;
}

@media (max-width: 900px) {
  .bar {
    padding: 16px;
    position: static;
  }

  .brand {
    flex-wrap: wrap;
  }

  .meta {
    white-space: normal;
    overflow-wrap: anywhere;
  }

  .tools {
    width: 100%;
  }

  .search {
    width: 100%;
    margin-right: 0;
  }
}
"""


def Brand(project, rules, evaluated):
    return f"""
        <div class="brand">
          {LOGO}
          <div class="proj">
            <h1>Quality review: {E(project)}</h1>
            <div class="meta">Rules: {E(rules)} · evaluated {E(evaluated)}</div>
          </div>
        </div>
    """


def SearchBox():
    return f"""
        <label class="search">
          {ICON_SEARCH}
          <input id="q" type="search" placeholder="Search criteria" aria-label="Search criteria">
        </label>
    """


def StatusFilter(n):
    buttons = "".join(
        f"""
        <button class="f {k}" data-filter="{k}" aria-pressed="true">
          <i></i>{LABELS[k]}<span class="n">{n[k]}</span>
        </button>
        """
        for k in (*STATUSES, "optional")
        if n[k]
    )
    return f"""
        <div class="chips" role="group" aria-label="Filter by status">
          {buttons}
        </div>
    """


def Header(project, rules, evaluated, n):
    return f"""
        <header class="bar">
          <div class="hd">{Brand(project, rules, evaluated)}</div>
          <div class="tools">
            {SearchBox()}
            {StatusFilter(n)}
          </div>
        </header>
    """


# ======================================================================================================
# SegmentBar: one coloured block per criterion
# ======================================================================================================
CSS_SEGMENTS = """
.seg {
  display: flex;
  gap: 2px;
  height: 8px;
  margin-top: 8px;
}

.seg span {
  flex: 1;
}

.seg .pass {
  background: var(--pass);
}

.seg .mixed {
  background: var(--mixed);
}

.seg .fail {
  background: var(--fail);
}

.seg .optional {
  background: none;
  box-shadow: inset 0 0 0 1px var(--optional);
}
"""


def SegmentBar(criteria):
    n = counts(criteria)
    label = f'{n["pass"]} pass, {n["mixed"]} mixed, {n["fail"]} fail, {n["optional"]} nice to have'
    cells = "".join(
        f'<span class="{c["shown"]}" title="{E(c["title"])}: {LABELS[c["shown"]]}"></span>'
        for c in criteria
    )
    return f"""
        <div class="seg" role="img" aria-label="{label}">{cells}</div>
    """


# ======================================================================================================
# Hero: the score numeral and a one-sentence verdict
# ======================================================================================================
CSS_HERO = """
.band.hero-band {
  padding-top: 96px;
}

/* One rounded box holds the score (left) and the group scoreboard (right). */
.overview {
  display: flex;
  align-items: stretch;
  flex-wrap: wrap;
  gap: 24px 64px;
  padding: 28px 32px;
  background: var(--card);
  border: 1px solid var(--grid);
  border-radius: var(--radius-lg);
}

.verdict {
  flex: none;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  gap: 24px;
}

.caption {
  white-space: nowrap;
  font-size: 14px;
  line-height: 1.43;
  letter-spacing: -.028px;
  color: var(--ink2);
}

.score {
  display: flex;
  align-items: baseline;
}

.big {
  font-size: 104px;
  font-weight: 300;
  line-height: .9;
  letter-spacing: -4px;
  font-variant-numeric: tabular-nums;
}

.pct {
  margin-left: 4px;
  font-size: 40px;
  font-weight: 300;
  color: var(--ink2);
}

@media (max-width: 900px) {
  .band.hero-band {
    padding-top: 40px;
  }

  .overview {
    padding: 20px 16px;
  }

  .caption {
    white-space: normal;
  }

  .big {
    font-size: 72px;
    letter-spacing: -2px;
  }
}
"""


def Hero(allc, n):
    optional = f' · {n["optional"]} nice to have' if n["optional"] else ""
    caption = f'overall score · {n["pass"]} pass · {n["mixed"]} mixed · {n["fail"]} fail{optional} of {len(allc)} criteria'
    return f"""
        <div class="verdict">
          <div class="score" role="img" aria-label="Overall score {score(allc)} percent">
            <span class="big">{score(allc)}</span><span class="pct">%</span>
          </div>
          <div class="caption">{caption}</div>
        </div>
    """


# ======================================================================================================
# Scoreboard: one ruled row per group under the hero (replaces the summary cards)
# ======================================================================================================
CSS_BOARD = """
.board {
  flex: 1 1 480px;
  min-width: 0;
  list-style: none;
  margin: 0;
  padding: 0;
}

.board li {
  border-bottom: 1px solid var(--grid);
}

.board li:last-child {
  border-bottom: 0;
}

.board a {
  display: grid;
  grid-template-columns: 190px minmax(0, 1fr) 96px;
  align-items: center;
  gap: 24px;
  margin: 0 -8px;
  padding: 16px 8px;
  border-radius: var(--radius);
  color: var(--ink);
  text-decoration: none;
  transition: background-color .2s;
}

.board a:hover {
  background: var(--hover);
}

.board a:focus-visible {
  outline: 2px solid var(--focus);
  outline-offset: -2px;
}

.board .seg {
  margin: 0;
}

.board .count {
  text-align: right;
  color: var(--ink2);
  font-variant-numeric: tabular-nums;
}

@media (max-width: 640px) {
  .board a {
    grid-template-columns: 1fr auto;
    gap: 8px 16px;
  }

  .board .seg {
    grid-column: 1 / -1;
    grid-row: 2;
  }
}
"""


def Scoreboard(groups):
    """One row per group: name, the bar, and 'x of y pass'. Each row links to its section."""
    rows = "".join(
        f"""
        <li>
          <a href="#band-{index}">
            <span>{E(label)}</span>
            {SegmentBar(criteria)}
            <span class="count">{counts(criteria)["pass"]} of {len(scored(criteria))} pass</span>
          </a>
        </li>
        """
        for index, label, criteria in groups
    )
    return f'<ul class="board">{rows}</ul>'


# ======================================================================================================
# GroupBand: a full-width section with the group heading and score on top, then the table
# ======================================================================================================
CSS_BAND = """
.band {
  padding: 48px max(var(--gutter), calc((100% - var(--content-max)) / 2));
}

.lab {
  display: flex;
  flex-wrap: wrap;
  align-items: flex-end;
  justify-content: space-between;
  gap: 16px 32px;
  margin-bottom: 32px;
  padding-top: 24px;
  border-top: 1px solid var(--grid);
}

.lab h2 {
  margin: 0;
  font-size: 28px;
  font-weight: 300;
  line-height: 1.2;
  letter-spacing: -.28px;
}

.lab .sub {
  margin-top: 8px;
  max-width: 60ch;
  font-size: 14px;
  line-height: 1.43;
  letter-spacing: -.028px;
}

.gstat {
  text-align: right;
}

.gs {
  font-size: 32px;
  font-weight: 300;
  line-height: 1.25;
  letter-spacing: -.128px;
  font-variant-numeric: tabular-nums;
}

.gstat .sub {
  margin-top: 0;
  font-size: 12px;
}

@media (max-width: 900px) {
  .band {
    padding: 32px 16px;
  }

  .gstat {
    text-align: left;
  }
}
"""


def _summary(n):
    parts = [f'{n[k]} {w}' for k, w in (("mixed", "mixed"), ("fail", "fail"), ("optional", "nice to have")) if n[k]]
    return ", ".join(parts)


def GroupBand(index, group, rows_html):
    cs = group["criteria"]
    n = counts(cs)
    detail = f'{n["pass"]} of {len(scored(cs))} pass'
    if _summary(n):
        detail += f', {_summary(n)}'
    return f"""
        <section class="band" id="band-{index}">
          <div class="lab">
            <div>
              <h2>{E(group["label"])}</h2>
              <div class="sub">{E(group.get("question", ""))}</div>
            </div>
            <div class="gstat">
              <div class="gs">{score(cs)}%</div>
              <div class="sub">{E(detail)}</div>
            </div>
          </div>
          {CriteriaTable(rows_html)}
        </section>
    """


# ======================================================================================================
# CriteriaTable, CriterionRow, StatusBadge
# ======================================================================================================
CSS_TABLE = """
table {
  width: 100%;
  table-layout: fixed;
  border-collapse: collapse;
}

th {
  padding: 0 16px 12px 0;
  border-bottom: 1px solid var(--grid);
  text-align: left;
  font-size: 12px;
  font-weight: 600;
  line-height: 1.33;
  color: var(--ink2);
}

td {
  padding: 20px 16px 20px 0;
  vertical-align: top;
  overflow-wrap: anywhere;
}

tr.row td {
  border-top: 1px solid var(--grid);
}

tr.row:first-child td {
  border-top: 0;
}

tr.detail td {
  padding: 0;
}

/* Good news is quiet: passing rows are set in secondary text and regular weight. */
tr.row.pass td {
  color: var(--ink2);
}

tr.row.pass .tg {
  font-weight: 400;
}

.badge {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-weight: 600;
  white-space: nowrap;
  min-height: 20px;
}

.badge.pass {
  color: var(--pass-t);
  font-weight: 400;
}

.badge.mixed {
  color: var(--mixed-t);
}

.badge.fail {
  color: var(--fail-t);
}

.badge.optional {
  color: var(--optional-t);
}

.suggest {
  margin-top: 8px;
  color: var(--ink);
}

.suggest b {
  color: var(--ink2);
  font-weight: 600;
}

@media (max-width: 900px) {
  .tw {
    overflow-x: auto;
  }

  table {
    min-width: 560px;
  }
}
"""
COLUMN_WIDTHS = ("32%", "136px", "auto")   # Criterion, Result, Finding


def StatusBadge(status):
    return f"""
        <span class="badge {status}">
          <svg class="ic" viewBox="0 0 16 16" aria-hidden="true" fill="none" stroke="currentColor"
               stroke-width="2" stroke-linecap="square" stroke-linejoin="miter">{ICONS[status]}</svg>
          {LABELS[status]}
        </span>
    """


def CriterionRow(i, c):
    """Two table rows: the visible row, and a hidden one that opens to show the rule behind the check."""
    text = E(f'{c["title"]} {c["message"]} {c.get("suggestion", "")}'.lower())
    rule = RuleDetails(c)
    title = Toggle(f"d{i}", E(c["title"])) if rule else E(c["title"])
    detail = Collapse(f"d{i}", rule)

    evidence = ""
    if c["evidence"]:
        items = "".join(f"<li>{E(x)}</li>" for x in c["evidence"])
        evidence = Toggle(f"e{i}", f'Evidence ({len(c["evidence"])})', small=True) + Collapse(f"e{i}", f'<ul class="ev">{items}</ul>')

    suggestion = ""
    if c.get("suggestion"):
        suggestion = f'<div class="suggest"><b>Suggestion:</b> {E(c["suggestion"])}</div>'

    return f"""
        <tr class="row {c["shown"]}" id="r{i}" data-status="{c["shown"]}" data-text="{text}">
          <td>{title}</td>
          <td>{StatusBadge(c["shown"])}</td>
          <td>
            {E(c["message"])}
            {suggestion}
            {evidence}
          </td>
        </tr>
        <tr class="detail" data-for="r{i}">
          <td colspan="3">{detail}</td>
        </tr>
    """


def CriteriaTable(rows_html):
    cols = "".join(f'<col style="width:{w}">' if w != "auto" else "<col>" for w in COLUMN_WIDTHS)
    return f"""
        <div class="tw">
          <table>
            <colgroup>{cols}</colgroup>
            <thead>
              <tr><th>Criterion</th><th>Result</th><th>Finding</th></tr>
            </thead>
            <tbody>
              {rows_html}
            </tbody>
          </table>
        </div>
    """


# ======================================================================================================
# Toggle + Collapse (animated open/close) and RuleDetails (the content of the rule panel)
# ======================================================================================================
CSS_COLLAPSE = """
.tg {
  display: flex;
  align-items: center;
  gap: 8px;
  min-height: 36px;
  margin: -8px;
  padding: 8px;
  width: calc(100% + 16px);
  background: none;
  border: 0;
  border-radius: var(--radius);
  color: inherit;
  font: inherit;
  font-weight: 600;
  text-align: left;
  cursor: pointer;
  transition: background-color .2s;
}

.tg:hover {
  background: var(--hover);
}

.tg:focus-visible {
  outline: 2px solid var(--focus);
  outline-offset: -2px;
}

.tg .chev {
  width: 16px;
  height: 16px;
  flex: none;
  color: var(--ink2);
  transition: transform .2s;
}

.tg[aria-expanded=true] .chev {
  transform: rotate(90deg);
}

.tg.sm {
  font-size: 12px;
  font-weight: 400;
  line-height: 1.33;
  color: var(--ink2);
  min-height: 28px;
  margin: 4px -8px -8px;
  padding: 4px 8px;
}

.collapse {
  display: grid;
  grid-template-rows: 0fr;
  visibility: hidden;
  transition: grid-template-rows .2s ease, visibility .2s;
}

.collapse.open {
  grid-template-rows: 1fr;
  visibility: visible;
}

.collapse>.inner {
  overflow: hidden;
  min-height: 0;
}

.rule {
  max-width: 72ch;
  padding: 0 16px 20px 24px;
  font-size: 12px;
  line-height: 1.33;
  letter-spacing: .024px;
  color: var(--ink2);
}

.rule h4 {
  margin: 12px 0 4px;
  font-size: 12px;
  font-weight: 600;
  color: var(--ink);
}

.rule ul {
  margin: 0;
  padding-left: 16px;
  font-family: inherit;
}

.ev {
  margin: 8px 0 0;
  padding-left: 16px;
  font-family: "Roboto Mono", ui-monospace, monospace;
  font-size: 12px;
  line-height: 1.33;
  color: var(--ink2);
}
"""


def Toggle(controls, label_html, small=False):
    size = " sm" if small else ""
    return f"""
        <button class="tg{size}" aria-expanded="false" aria-controls="{controls}">
          {ICON_CHEVRON}{label_html}
        </button>
    """


def Collapse(id_, inner_html):
    return f"""
        <div class="collapse" id="{id_}">
          <div class="inner">{inner_html}</div>
        </div>
    """


def RuleDetails(c):
    rule = c.get("rule")
    if not isinstance(rule, dict):
        return ""

    def section(key, heading):
        items = rule.get(key) or []
        if not items:
            return ""
        lis = "".join(f"<li>{E(x)}</li>" for x in items)
        return f"<h4>{heading}</h4><ul>{lis}</ul>"

    return f"""
        <div class="rule">
          {E(rule.get("summary", ""))}
          {section("good", "Good pattern")}
          {section("anti", "Anti-pattern")}
          <div class="sub" style="margin-top:12px">Source: {E(c.get("source", ""))}</div>
        </div>
    """


# ======================================================================================================
# SCRIPT: search, status filters, open/close. Hooks: #q, [data-filter], .tg[aria-controls], [data-status]
# ======================================================================================================
SCRIPT = """
const search = document.getElementById('q');
const hiddenStatuses = new Set();

// Open or close the panel a toggle button points at.
function setOpen(button, open) {
  button.setAttribute('aria-expanded', open);
  document.getElementById(button.getAttribute('aria-controls')).classList.toggle('open', open);
}

// Show a row only if its status is not filtered out and it matches the search text.
function applyFilters() {
  const text = search.value.trim().toLowerCase();
  document.querySelectorAll('[data-status]').forEach((row) => {
    const visible = !hiddenStatuses.has(row.dataset.status) && (!text || row.dataset.text.includes(text));
    row.hidden = !visible;
    // The hidden "rule" row that belongs to this row follows it.
    const detail = row.id && document.querySelector('[data-for="' + row.id + '"]');
    if (detail) detail.hidden = !visible;
  });
}

search.addEventListener('input', applyFilters);

document.addEventListener('click', (event) => {
  const toggle = event.target.closest('.tg');
  if (toggle) {
    setOpen(toggle, toggle.getAttribute('aria-expanded') !== 'true');
  }

  const filter = event.target.closest('.f');
  if (filter) {
    const status = filter.dataset.filter;
    const on = filter.getAttribute('aria-pressed') !== 'true';
    filter.setAttribute('aria-pressed', on);
    if (on) hiddenStatuses.delete(status);
    else hiddenStatuses.add(status);
    applyFilters();
  }
});
"""

# ======================================================================================================
# PAGE: put the components together
# ======================================================================================================
STYLES = "\n".join([CSS_TOKENS, CSS_BASE, CSS_HEADER, CSS_SEGMENTS, CSS_HERO, CSS_BOARD, CSS_BAND, CSS_TABLE, CSS_COLLAPSE])


def Page(data):
    groups = data["groups"]
    allc = [c for k in GROUPS for c in groups[k]["criteria"]]
    if not allc:
        die("no criteria to show")
    n = counts(allc)
    boards, bands, i = [], [], 0
    for index, key in enumerate(GROUPS, start=1):
        group = {**groups[key], "label": groups[key].get("label", key)}
        rows = []
        for c in group["criteria"]:
            i += 1
            rows.append(CriterionRow(i, c))
        boards.append((index, group["label"], group["criteria"]))
        bands.append(GroupBand(index, group, "".join(rows)))
    project = data.get("project", "")
    header = Header(project, data.get("rules_source", ""), data.get("evaluated_at", ""), n)
    overview = f"""
        <section class="band hero-band" id="band-0">
          <div class="overview">
            {Hero(allc, n)}
            {Scoreboard(boards)}
          </div>
        </section>
    """
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>Kedro quality check: {E(project)}</title>
  <style>{STYLES}</style>
</head>
<body>
  <main>
    {header}
    {overview}
    {"".join(bands)}
  </main>
  <script>{SCRIPT}</script>
</body>
</html>
"""


# ======================================================================================================
# DATA: load, validate, score
# ======================================================================================================
def die(msg):
    sys.exit(f"build_dashboard: {msg}")


def load(path):
    try:
        data = json.loads(Path(path).read_text())
    except (OSError, json.JSONDecodeError) as exc:
        die(f"cannot read {path}: {exc}")
    groups = data.get("groups")
    if not isinstance(groups, dict):
        die("'groups' object is missing")
    for key in GROUPS:
        if key not in groups:
            die(f"group '{key}' is missing")
        if not isinstance(groups[key].get("criteria"), list):
            die(f"group '{key}' has no 'criteria' list")
        for c in groups[key]["criteria"]:
            for field in ("id", "title", "status", "message"):
                if field not in c:
                    die(f"criterion in '{key}' is missing '{field}': {c}")
            if c["status"] not in STATUSES:
                die(f"{c['id']}: status must be one of {STATUSES}, got {c['status']!r}")
            c.setdefault("evidence", [])
            # Optional criteria never fail: below 'pass' they show as "Nice to have" and are not scored.
            c["shown"] = "optional" if c.get("optional") and c["status"] != "pass" else c["status"]
    return data


def counts(criteria):
    return {s: sum(c["shown"] == s for c in criteria) for s in (*STATUSES, "optional")}


def scored(criteria):
    return [c for c in criteria if not c.get("optional")]


def score(criteria):
    criteria = scored(criteria)
    if not criteria:
        return 0
    return round(100 * (sum(c["status"] == "pass" for c in criteria) + 0.5 * sum(c["status"] == "mixed" for c in criteria)) / len(criteria))


# ======================================================================================================
# ASSETS: icons and the Kedro logo (official kedro_logo_black.svg)
# ======================================================================================================
ICON_CHEVRON = ('<svg class="chev" viewBox="0 0 16 16" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="2" '
                'stroke-linecap="square" stroke-linejoin="miter"><path d="M6 3.5l5 4.5-5 4.5"/></svg>')
ICON_SEARCH = ('<svg class="ic" viewBox="0 0 16 16" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="1.5">'
               '<circle cx="6.5" cy="6.5" r="4.5"/><path d="M10 10l4.5 4.5"/></svg>')
LOGO = '<svg role="img" aria-label="Kedro" xmlns="http://www.w3.org/2000/svg" width="124" height="32" class="logo" viewBox="0 0 124 32" fill="none"><path d="M40.1191 27.5487V4.05957H44.295V17.9247L50.0368 11.3673H54.9956L48.373 18.7403L56.0722 27.5487H50.8524L44.295 19.4254V27.5487H40.1191Z" fill="#151515"/><path d="M64.5661 27.9402C62.9349 27.9402 61.4886 27.5922 60.2271 26.8962C58.9657 26.2002 57.9761 25.2215 57.2583 23.9601C56.5406 22.6986 56.1818 21.2414 56.1818 19.5885C56.1818 17.9138 56.5297 16.424 57.2257 15.119C57.9434 13.8141 58.9222 12.8027 60.1619 12.085C61.4233 11.3455 62.9023 10.9758 64.5987 10.9758C66.1864 10.9758 67.5892 11.3238 68.8072 12.0198C70.0251 12.7157 70.9712 13.6727 71.6454 14.8907C72.3414 16.0869 72.6894 17.4244 72.6894 18.9034C72.6894 19.1426 72.6785 19.3927 72.6568 19.6537C72.6568 19.9147 72.6459 20.1866 72.6241 20.4693H60.325C60.412 21.7308 60.847 22.7204 61.6299 23.4381C62.4346 24.1558 63.4025 24.5147 64.5334 24.5147C65.3817 24.5147 66.0885 24.3298 66.654 23.9601C67.2412 23.5686 67.6762 23.0684 67.9589 22.4594H72.2C71.8955 23.4816 71.3844 24.4168 70.6667 25.265C69.9707 26.0915 69.1008 26.744 68.0568 27.2224C67.0346 27.7009 65.871 27.9402 64.5661 27.9402ZM64.5987 14.3687C63.5765 14.3687 62.6739 14.6623 61.8909 15.2495C61.1079 15.815 60.6077 16.685 60.3902 17.8594H68.4483C68.383 16.7937 67.9916 15.9455 67.2738 15.3148C66.5561 14.684 65.6644 14.3687 64.5987 14.3687Z" fill="#151515"/><path d="M82.4979 27.9402C80.9755 27.9402 79.6162 27.5704 78.4199 26.831C77.2237 26.0915 76.2777 25.0801 75.5817 23.7969C74.8857 22.5137 74.5377 21.0566 74.5377 19.4254C74.5377 17.7942 74.8857 16.3479 75.5817 15.0864C76.2777 13.8032 77.2237 12.8027 78.4199 12.085C79.6162 11.3455 80.9755 10.9758 82.4979 10.9758C83.7159 10.9758 84.7816 11.2042 85.695 11.6609C86.6085 12.1176 87.348 12.7592 87.9135 13.5857V4.05957H92.0893V27.5487H88.3702L87.9135 25.2324C87.3915 25.9501 86.6955 26.5808 85.8255 27.1246C84.9773 27.6683 83.8681 27.9402 82.4979 27.9402ZM83.3788 24.2863C84.7272 24.2863 85.8255 23.8404 86.6738 22.9487C87.5437 22.0353 87.9787 20.8717 87.9787 19.458C87.9787 18.0443 87.5437 16.8916 86.6738 15.9999C85.8255 15.0864 84.7272 14.6297 83.3788 14.6297C82.0521 14.6297 80.9537 15.0755 80.0838 15.9672C79.2138 16.859 78.7788 18.0117 78.7788 19.4254C78.7788 20.8391 79.2138 22.0026 80.0838 22.9161C80.9537 23.8296 82.0521 24.2863 83.3788 24.2863Z" fill="#151515"/><path d="M95.6891 27.5487V11.3673H99.4082L99.7997 14.4013C100.387 13.3573 101.181 12.5309 102.181 11.9219C103.203 11.2912 104.4 10.9758 105.77 10.9758V15.38H104.595C103.682 15.38 102.866 15.5214 102.149 15.8041C101.431 16.0869 100.865 16.5762 100.452 17.2722C100.061 17.9682 99.865 18.936 99.865 20.1757V27.5487H95.6891Z" fill="#151515"/><path d="M115.083 27.9402C113.518 27.9402 112.104 27.5813 110.842 26.8636C109.603 26.1459 108.613 25.1563 107.874 23.8948C107.156 22.6116 106.797 21.1327 106.797 19.458C106.797 17.7833 107.167 16.3152 107.906 15.0538C108.646 13.7706 109.635 12.7701 110.875 12.0524C112.136 11.3347 113.55 10.9758 115.116 10.9758C116.66 10.9758 118.052 11.3347 119.292 12.0524C120.553 12.7701 121.543 13.7706 122.261 15.0538C123 16.3152 123.37 17.7833 123.37 19.458C123.37 21.1327 123 22.6116 122.261 23.8948C121.543 25.1563 120.553 26.1459 119.292 26.8636C118.03 27.5813 116.628 27.9402 115.083 27.9402ZM115.083 24.3189C116.171 24.3189 117.117 23.9166 117.922 23.1118C118.726 22.2854 119.129 21.0674 119.129 19.458C119.129 17.8485 118.726 16.6415 117.922 15.8367C117.117 15.0103 116.182 14.597 115.116 14.597C114.007 14.597 113.05 15.0103 112.245 15.8367C111.462 16.6415 111.071 17.8485 111.071 19.458C111.071 21.0674 111.462 22.2854 112.245 23.1118C113.05 23.9166 113.996 24.3189 115.083 24.3189Z" fill="#151515"/><path d="M16 0L32 16L16 32L0 16L16 0Z" fill="#151515"/></svg>'


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("results")
    ap.add_argument("output")
    ap.add_argument("--open", action="store_true", help="open the dashboard in the default browser")
    args = ap.parse_args()
    data = load(args.results)
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(Page(data))
    allc = [c for k in GROUPS for c in data["groups"][k]["criteria"]]
    print(f"wrote {out} - overall {score(allc)}% ({counts(allc)})")
    if args.open:
        if not webbrowser.open(out.resolve().as_uri()):
            print(f"could not open a browser; open {out.resolve()} manually")


if __name__ == "__main__":
    main()
