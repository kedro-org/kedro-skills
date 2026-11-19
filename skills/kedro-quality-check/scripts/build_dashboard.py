#!/usr/bin/env python3
"""Build a self-contained HTML dashboard from a hallmark-quality-review results.json.

Usage: build_dashboard.py RESULTS_JSON OUTPUT_HTML [--rules RULES_FILE] [--open]

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
  Evidence open/close ........................ Toggle, Collapse    (CSS_COLLAPSE)
  "View rule" side panel . RuleButton, RuleSheet (CSS_SHEET)
  Rule git history (Last change / Author) .... git_log, RULES_LOG    (read from git at build time)
  Search, filters, rule editing behaviour .... SCRIPT
  Wording of labels .......................... LABELS
"""
import argparse
from datetime import datetime, timezone
import html
import json
import re
import subprocess
import sys
import webbrowser
from urllib.parse import quote
from pathlib import Path

E = html.escape


ALL_GROUPS = ("functional_appropriateness", "performance_efficiency", "maintainability")
GROUPS = list(ALL_GROUPS)
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
  transform-origin: left;
  animation: grow .7s cubic-bezier(.2, .8, .2, 1) both;
  animation-delay: calc(var(--i, 0) * 60ms);
}

@keyframes grow {
  from {
    transform: scaleX(0);
  }
}

@media (prefers-reduced-motion: reduce) {
  .seg span {
    animation: none;
  }
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
        f'<span class="{c["shown"]}" style="--i:{i}" title="{E(c["title"])}: {LABELS[c["shown"]]}"></span>'
        for i, c in enumerate(criteria)
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

.empty {
  margin: 0;
  padding: 32px 0;
  color: var(--ink2);
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
        <section class="band" id="band-{index}" data-group>
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
          <p class="empty" hidden>No criteria match your filters.</p>
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


# Links from the dashboard back to the code. Evidence like "src/pkg/nodes.py:61" or "conf/a.yml:1-60" becomes
# a link that opens that file at that line in the editor. ROOT is the project root (--root, default: the
# current directory) and SCHEME the editor's URL scheme (--editor, default: vscode).
ROOT = Path.cwd()
SCHEME = "vscode"
LOCATION = re.compile(r"^(.*?)(?::(\d+)(?:\s*[-\u2013]\s*\d+)?)?$")


def code_href(ref, line=None):
    """Editor URL for a path or path:line reference. Relative paths are taken from ROOT."""
    m = LOCATION.match(ref.strip())
    path, found = m.group(1), m.group(2)
    full = Path(path) if Path(path).is_absolute() else ROOT / path
    return f"{SCHEME}://file{quote(str(full), safe='/')}:{line or found or 1}:1"


def code_link(ref):
    return f'<a class="loc" href="{E(code_href(ref))}" title="Open in editor">{E(ref)}</a>'


def DefinedIn(data, c):
    """Small line under View rule: a link to where the rule is written in the rules file."""
    href = rule_href(data, c)
    if not href:
        return ""
    label = f'{rule_file_label(data)}:{rule_line(data, c)}'
    return f'<div class="def">Defined in <a class="loc" href="{E(href)}" title="Open the rule in the editor">{E(label)}</a></div>'


def CriterionRow(i, c, data):
    """One table row: criterion (with a View rule button), result, and finding with suggestion and evidence."""
    text = E(f'{c["title"]} {c["message"]} {c.get("suggestion", "")}'.lower())
    evidence = ""
    if c["evidence"]:
        items = "".join(f"<li>{code_link(x)}</li>" for x in c["evidence"])
        evidence = Toggle(f"e{i}", f'Evidence ({len(c["evidence"])})', small=True) + Collapse(f"e{i}", f'<ul class="ev">{items}</ul>')

    suggestion = ""
    if c.get("suggestion"):
        suggestion = f'<div class="suggest"><b>Suggestion:</b> {E(c["suggestion"])}</div>'

    return f"""
        <tr class="row {c["shown"]}" id="r{i}" data-status="{c["shown"]}" data-text="{text}">
          <td>{E(c["title"])}{RuleButton(c["id"], c["title"])}{DefinedIn(data, c)}</td>
          <td>{StatusBadge(c["shown"])}</td>
          <td>
            {E(c["message"])}
            {suggestion}
            {evidence}
          </td>
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
# Toggle + Collapse (animated open/close, used for the evidence list)
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


# ======================================================================================================
# RuleSheet: the "View rule" side panel. Read-only: severity, patterns and last change are shown, not edited.
# ======================================================================================================
CSS_SHEET = """
.rb {
  display: flex;
  align-items: center;
  gap: 6px;
  min-height: 28px;
  margin: 4px -8px -8px;
  padding: 4px 8px;
  background: none;
  border: 0;
  border-radius: var(--radius);
  color: var(--ink2);
  font: inherit;
  font-size: 12px;
  font-weight: 400;
  line-height: 1.33;
  cursor: pointer;
  transition: background-color .2s, color .2s;
}

.rb:hover {
  background: var(--hover);
  color: var(--ink);
}

.rb:focus-visible,
.sheet button:focus-visible,
.sheet textarea:focus-visible {
  outline: 2px solid var(--focus);
  outline-offset: -2px;
}

.sheet {
  position: fixed;
  inset: 0 0 0 auto;
  width: min(36rem, 100%);
  max-width: none;
  height: 100%;
  max-height: none;
  margin: 0;
  padding: 0;
  background: var(--card);
  color: var(--ink);
  border: 0;
  border-left: 1px solid var(--grid);
  overflow: hidden;
}

.sheet[open] {
  display: flex;
  flex-direction: column;
  animation: slide-in .25s cubic-bezier(.2, .8, .2, 1);
}

.sheet::backdrop {
  background: rgba(0, 0, 0, .6);
}

@keyframes slide-in {
  from {
    transform: translateX(100%);
  }
}

.sheet-body {
  position: relative;
  flex: 1;
  overflow-y: auto;
  padding: 24px 24px 32px;
}

.eyebrow {
  margin: 0 0 8px;
  font: 400 12px/1.33 "Roboto Mono", ui-monospace, monospace;
  letter-spacing: .1em;
  text-transform: uppercase;
  color: var(--focus);
}

.sheet h2 {
  margin: 0 0 12px;
  font-size: 24px;
  font-weight: 300;
  line-height: 1.25;
}

.gitlog {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr);
  gap: 4px 16px;
  margin: 0 0 16px;
  padding: 12px;
  background: var(--surface);
  border: 1px solid var(--grid);
  border-radius: var(--radius);
  font: 400 12px/1.33 "Roboto Mono", ui-monospace, monospace;
}

.gitlog dt {
  color: var(--ink2);
}

.gitlog dd {
  margin: 0;
  overflow-x: auto;
  white-space: nowrap;
}

.intent {
  margin: 0 0 24px;
  color: var(--ink2);
  font-size: 13px;
  line-height: 1.5;
}

.lbl {
  margin: 0 0 8px;
  font-size: 14px;
  font-weight: 600;
}

.sev {
  display: flex;
  gap: 8px;
  margin-bottom: 32px;
}

.sev button {
  padding: 4px 12px;
  background: none;
  border: 1px solid var(--grid);
  border-radius: 999px;
  color: var(--ink2);
  font: inherit;
  font-size: 12px;
  cursor: pointer;
  transition: color .2s, background-color .2s;
}

.sev button:hover {
  color: var(--ink);
}

.sev button[aria-checked=true] {
  color: var(--ink);
  border-color: var(--optional);
}

.sev button[aria-checked=true][data-sev=fail] {
  background: var(--fail);
  border-color: var(--fail);
  color: #fff;
}

.pl {
  margin-bottom: 32px;
  padding-left: 16px;
  border-left: 2px solid var(--pass);
}

.pl.anti {
  border-left-color: var(--fail);
}

.pl h3 {
  display: flex;
  align-items: center;
  gap: 8px;
  margin: 0 0 12px;
  font-size: 14px;
  font-weight: 600;
  color: var(--pass-t);
}

.pl.anti h3 {
  color: var(--fail-t);
}

.pl ul {
  list-style: none;
  margin: 0;
  padding: 0;
}

.pl li {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  margin-bottom: 4px;
}

.loc {
  color: inherit;
  text-decoration: underline;
  text-decoration-color: var(--grid);
  text-underline-offset: 3px;
}

.loc:hover {
  color: var(--focus);
  text-decoration-color: var(--focus);
}

.def {
  margin: 4px 0 0;
  color: var(--ink2);
  font: 400 11px/1.4 "Roboto Mono", ui-monospace, monospace;
}

.pl code {
  font: 400 12px/1.4 "Roboto Mono", ui-monospace, monospace;
  background: rgba(0,0,0,.06);
  padding: 1px 4px;
}

.pill {
  display: inline-block;
  padding: 4px 12px;
  border: 1px solid var(--optional);
  border-radius: 999px;
  font-size: 12px;
  color: var(--ink);
}

.pill[data-sev=fail] {
  background: var(--fail);
  border-color: var(--fail);
  color: #fff;
}

.sheet .x {
  position: absolute;
  top: 16px;
  right: 16px;
  display: grid;
  place-items: center;
  width: 32px;
  height: 32px;
  background: none;
  border: 1px solid var(--grid);
  border-radius: 999px;
  color: var(--ink2);
  cursor: pointer;
}

.pl li {
  display: block;
  font-size: 14px;
  line-height: 1.5;
  margin-bottom: 8px;
  color: var(--ink);
}

.pl textarea {
  flex: 1;
  min-width: 0;
  min-height: 0;
  resize: none;
  overflow: hidden;
  padding: 6px 8px;
  background: none;
  border: 1px solid transparent;
  border-radius: var(--radius);
  color: var(--ink);
  font: inherit;
  font-size: 14px;
  line-height: 1.43;
  field-sizing: content;
}

.pl textarea:hover {
  background: var(--hover);
}

.pl textarea:focus {
  border-color: var(--grid);
}

.pl .rm {
  margin-top: 6px;
  padding: 0;
  background: none;
  border: 0;
  color: var(--ink2);
  cursor: pointer;
  opacity: 0;
  transition: opacity .2s;
}

.pl li:hover .rm,
.pl .rm:focus-visible {
  opacity: 1;
}

.pl .rm:hover {
  color: var(--ink);
}

.pl .add {
  display: flex;
  align-items: center;
  gap: 4px;
  margin-top: 8px;
  padding: 0 8px;
  background: none;
  border: 0;
  color: var(--ink2);
  font: inherit;
  font-size: 12px;
  cursor: pointer;
}

.pl .add:hover {
  color: var(--ink);
}

.sheet-foot {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 16px 24px;
  border-top: 1px solid var(--grid);
  background: var(--card);
}

.sheet-foot .push {
  margin-left: auto;
  display: flex;
  gap: 8px;
}

.btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  min-height: 36px;
  padding: 0 16px;
  background: none;
  border: 1px solid var(--grid);
  border-radius: var(--radius);
  color: var(--ink);
  font: inherit;
  font-size: 14px;
  cursor: pointer;
  transition: background-color .2s, opacity .2s;
}

.btn:hover {
  background: var(--hover);
}

.btn.ghost {
  border-color: transparent;
}

.btn.primary {
  background: var(--header-bg);
  border-color: var(--header-bg);
  color: var(--header-ink);
}

.btn.primary:hover {
  opacity: .9;
}

.btn:disabled {
  opacity: .5;
  cursor: not-allowed;
}

@media (prefers-reduced-motion: reduce) {
  .sheet[open] {
    animation: none;
  }
}
"""


def RuleButton(criterion_id, title):
    return f"""
        <button class="rb" data-rule="{E(criterion_id)}" data-title="{E(title)}" aria-haspopup="dialog" aria-label="View rule: {E(title)}">
          {ICON_BOOK}View rule
        </button>
    """


def RuleSheet():
    """An empty, read-only dialog. SCRIPT fills it in for whichever criterion's View rule button was clicked."""
    return f"""
        <dialog class="sheet" id="rule-sheet" aria-labelledby="rs-title">
          <div class="sheet-body">
            <button class="x" id="rs-close" type="button" aria-label="Close">{ICON_X}</button>
            <p class="eyebrow" id="rs-eyebrow">Rule</p>
            <h2 id="rs-title"></h2>
            <dl class="gitlog" id="rs-log"></dl>
            <p class="lbl" id="rs-sev-label">Severity</p>
            <div class="sev" id="rs-sev" aria-labelledby="rs-sev-label"></div>
            <div class="pl good" id="rs-good"></div>
            <div class="pl anti" id="rs-anti"></div>
          </div>
        </dialog>
    """


def as_list(value):
    """The rule text as a list of lines. results.json may hold one sentence (str) or a list of them."""
    if not value:
        return []
    if isinstance(value, str):
        return [value]
    return [str(x) for x in value]


def rule_line(data, c):
    """Line of the criterion's "## title" heading in the rules file, or None."""
    return data.get("rule_lines", {}).get(c["title"])


def rule_file_label(data):
    """The rules file as shown to the reader: relative to the project root when possible, else its name."""
    path = Path(data.get("rules_path") or data.get("rules_source") or "")
    try:
        return str(path.resolve().relative_to(ROOT))
    except ValueError:
        return path.name


def rule_ref(data, c):
    line = rule_line(data, c)
    return f'{rule_file_label(data)}:{line}' if line else ""


def rule_href(data, c):
    line = rule_line(data, c)
    target = data.get("rules_path") or data.get("rules_source")
    return code_href(str(target), line) if line and target else ""


def RulesData(data):
    """Default rules and git history as JSON for SCRIPT. Defaults come from results.json, local edits are layered on top in the browser."""
    rules = {}
    for k in GROUPS:
        for c in data["groups"][k]["criteria"]:
            # Patterns come from the rules file itself. results.json may override them with a "rule" object.
            r = c.get("rule") if isinstance(c.get("rule"), dict) else {}
            text = data.get("rule_text", {}).get(c["title"], {})
            rules[c["id"]] = {
                "good": as_list(r.get("good")) or text.get("good", []),
                "anti": as_list(r.get("anti")) or text.get("anti", []),
                "source": c.get("source", ""),
                "severity": "nice" if c.get("optional") else "fail",
            }
    payload = {"project": data.get("project", ""), "rules": rules, "log": data["rules_log"]}
    # "</" would end the script element early.
    return json.dumps(payload).replace("</", "<\\/")


def git_log(rules_file):
    """Last commits that touched the rules file, newest first (git log -10).

    Falls back to the template version in .copier-answers.yml (with the file's modified time) when the
    project has no git history for the rules file yet. Empty when neither is available.
    """
    if not rules_file:
        return []
    path = Path(rules_file)
    if not path.is_file():
        return []
    log = []
    try:
        out = subprocess.run(
            ["git", "-c", "safe.directory=*", "log", "-10", "--format=%H%x1f%an%x1f%cI%x1f%s", "--", path.name],
            cwd=path.resolve().parent, capture_output=True, text=True, check=True, timeout=10,
        ).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        out = ""
    for line in out.splitlines():
        h, author, date, subject = (line.split("\x1f") + ["", "", "", ""])[:4]
        log.append({"hash": h, "author": author, "date": date, "subject": subject})
    return log or copier_version(path)


def copier_version(path):
    """One log entry for the template version the rules came from, read from .copier-answers.yml."""
    for base in path.resolve().parents:
        answers = base / ".copier-answers.yml"
        if answers.is_file():
            match = re.search(r"^_commit:\s*(\S+)", answers.read_text(), re.M)
            if match:
                modified = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc).isoformat()
                return [{"hash": match.group(1), "author": "", "date": modified, "subject": "template version"}]
            return []
    return []


def heading_lines(rules_file):
    """Map each "## title" in the rules file to its line number, so a rule can link to where it is written."""
    if not rules_file or not Path(rules_file).is_file():
        return {}
    lines = Path(rules_file).read_text().splitlines()
    return {line[3:].strip(): n for n, line in enumerate(lines, start=1) if line.startswith("## ")}


def rule_sections(rules_file):
    """Good and anti-pattern bullets of each "## title" section in the rules file, read at build time."""
    if not rules_file or not Path(rules_file).is_file():
        return {}
    sections, title, kind = {}, None, None
    for raw in Path(rules_file).read_text().splitlines():
        line = raw.strip()
        if raw.startswith("## "):
            title, kind = raw[3:].strip(), None
            sections[title] = {"good": [], "anti": []}
        elif title is None:
            continue
        elif line.lower().strip("*: ").startswith("good pattern"):
            kind = "good"
        elif line.lower().strip("*: ").startswith("anti-pattern") or line.lower().strip("*: ").startswith("anti pattern"):
            kind = "anti"
        elif kind and line.startswith(("- ", "* ")):
            sections[title][kind].append(line[2:].strip())
        elif kind and line and sections[title][kind]:
            sections[title][kind][-1] += " " + line  # wrapped bullet
    return sections


def find_rules_file(data, results_path, explicit):
    """--rules wins. Otherwise try rules_source from results.json next to the results file, then up the tree."""
    if explicit:
        return Path(explicit)
    source = data.get("rules_source")
    if not source:
        return None
    here = Path(results_path).resolve().parent
    for base in (Path.cwd(), here, *here.parents):
        if (base / source).is_file():
            return base / source
    return None


# ======================================================================================================
# SCRIPT: search, status filters, open/close. Hooks: #q, [data-filter], .tg[aria-controls], [data-status]
# ======================================================================================================
SCRIPT = """
const search = document.getElementById('q');
const hiddenStatuses = new Set();
const DATA = JSON.parse(document.getElementById('rules-data').textContent);

// ---- Search, status filters, open/close --------------------------------------------------------------

// Open or close the panel a toggle button points at.
function setOpen(button, open) {
  button.setAttribute('aria-expanded', open);
  document.getElementById(button.getAttribute('aria-controls')).classList.toggle('open', open);
}

// Show a row only if its status is not filtered out and it matches the search text.
function applyFilters() {
  const text = search.value.trim().toLowerCase();
  document.querySelectorAll('tr[data-status]').forEach((row) => {
    row.hidden = hiddenStatuses.has(row.dataset.status) || (text && !row.dataset.text.includes(text));
  });
  // A group with no visible rows says so instead of showing an empty table.
  document.querySelectorAll('section[data-group]').forEach((band) => {
    const any = band.querySelector('tr[data-status]:not([hidden])');
    band.querySelector('.empty').hidden = !!any;
    band.querySelector('.tw').hidden = !any;
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

  const open = event.target.closest('[data-rule]');
  if (open) openRule(open.dataset.rule);
});

// ---- Rule panel: read-only -----------------------------------------------------------------------------

const SEVERITY_LABEL = { fail: 'Fail', nice: 'Nice to have' };
const sheet = document.getElementById('rule-sheet');
const $ = (id) => document.getElementById(id);
const EMPTY = { good: [], anti: [], source: '', severity: 'fail' };

// Mimics git's default date format: "Wed Nov 18 21:22:20 2026 +0000"
function gitDate(iso) {
  const d = new Date(iso);
  if (isNaN(d)) return 'unknown';
  const p = (n) => String(n).padStart(2, '0');
  const off = -d.getTimezoneOffset();
  const tz = (off >= 0 ? '+' : '-') + p(Math.floor(Math.abs(off) / 60)) + p(Math.abs(off) % 60);
  return d.toLocaleDateString('en-US', { weekday: 'short' }) + ' ' + d.toLocaleDateString('en-US', { month: 'short' }) + ' ' +
    d.getDate() + ' ' + p(d.getHours()) + ':' + p(d.getMinutes()) + ':' + p(d.getSeconds()) + ' ' + d.getFullYear() + ' ' + tz;
}

function el(tag, props, children) {
  const node = Object.assign(document.createElement(tag), props || {});
  (children || []).forEach((c) => node.append(c));
  return node;
}

function icon(svg) {
  const t = document.createElement('template');
  t.innerHTML = svg;
  return t.content.firstElementChild;
}

// Last change = commit number (short hash) and subject, then author and date.
function renderLog() {
  const last = DATA.log[0];
  const commit = last ? last.hash.slice(0, 7) + (last.subject ? '  ' + last.subject : '') : 'No history';
  const log = $('rs-log');
  log.replaceChildren(
    el('dt', { textContent: 'Last change' }), el('dd', { textContent: commit, title: commit }),
    el('dt', { textContent: 'Author' }), el('dd', { textContent: last && last.author ? last.author : 'unknown' }),
    el('dt', { textContent: 'Date' }), el('dd', { textContent: last && last.date ? gitDate(last.date) : 'unknown' }),
  );
}

// Only the severity the rule already has. It cannot be changed here.
function renderSeverity(rule) {
  const pill = el('span', { textContent: SEVERITY_LABEL[rule.severity] || rule.severity, className: 'pill' });
  pill.dataset.sev = rule.severity;
  $('rs-sev').replaceChildren(pill);
}

function renderPatterns(kind, rule) {
  const good = kind === 'good';
  const list = el('ul');
  (rule[kind] || []).forEach((text) => {
    // `code` spans in the rule text become <code>; everything else stays plain text.
    const parts = text.split('`').map((t, i) => (i % 2 ? el('code', { textContent: t }) : t));
    list.append(el('li', {}, parts));
  });
  $('rs-' + kind).replaceChildren(el('h3', {}, [icon(good ? ICON_CHECK : ICON_X), good ? 'Good pattern' : 'Anti-pattern']), list);
}

function openRule(id) {
  const rule = DATA.rules[id] || EMPTY;
  $('rs-title').textContent = document.querySelector('[data-rule="' + id + '"]').dataset.title;
  renderLog();
  renderSeverity(rule);
  renderPatterns('good', rule);
  renderPatterns('anti', rule);
  sheet.showModal();
}

$('rs-close').addEventListener('click', () => sheet.close());
// Clicking the dimmed area outside the panel closes it. Esc is handled by the dialog itself.
sheet.addEventListener('click', (event) => { if (event.target === sheet) sheet.close(); });

applyFilters();
"""

# ======================================================================================================
# PAGE: put the components together
# ======================================================================================================
STYLES = "\n".join([CSS_TOKENS, CSS_BASE, CSS_HEADER, CSS_SEGMENTS, CSS_HERO, CSS_BOARD, CSS_BAND, CSS_TABLE, CSS_COLLAPSE, CSS_SHEET])


def script_icons():
    """The few icons SCRIPT draws itself, as JS constants."""
    icons = {"ICON_X": ICON_X, "ICON_CHECK": ICON_CHECK}
    return "".join(f"const {name} = {json.dumps(svg)};\n" for name, svg in icons.items()).replace("</", "<\\/")


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
            rows.append(CriterionRow(i, c, data))
        boards.append((index, group["label"], group["criteria"]))
        bands.append(GroupBand(index, group, "".join(rows)))
    project = data.get("project", "")
    n_all = len(allc)
    description = f"Hallmark quality review of {project}: {score(allc)}% overall across {n_all} criteria."
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
  <title>Hallmark quality review: {E(project)}</title>
  <meta name="description" content="{E(description)}">
  <meta property="og:title" content="Hallmark quality review: {E(project)}">
  <meta property="og:description" content="{E(description)}">
  <meta property="og:type" content="website">
  <style>{STYLES}</style>
</head>
<body>
  <main>
    {header}
    {overview}
    {"".join(bands)}
  </main>
  {RuleSheet()}
  <script type="application/json" id="rules-data">{RulesData(data)}</script>
  <script>{script_icons()}{SCRIPT}</script>
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
    GROUPS[:] = [k for k in ALL_GROUPS if k in groups]
    if not GROUPS:
        die(f"no known group found; expected one of {ALL_GROUPS}")
    for key in GROUPS:
        if not isinstance(groups[key].get("criteria"), list):
            die(f"group '{key}' has no 'criteria' list")
        for c in groups[key]["criteria"]:
            for field in ("id", "title", "status", "message"):
                if field not in c:
                    die(f"criterion in '{key}' is missing '{field}': {c}")
            if c["status"] not in STATUSES:
                die(f"{c['id']}: status must be one of {STATUSES}, got {c['status']!r}")
            c.setdefault("evidence", [])
            if c.get("severity") not in (None, "fail", "nice_to_have"):
                die(f"{c['id']}: severity must be 'fail' or 'nice_to_have', got {c['severity']!r}")
            # Severity comes from the rules file. nice_to_have means optional: never scored, never failing.
            if c.get("severity") == "nice_to_have":
                c["optional"] = True
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
# ASSETS: icons and the Hallmark wordmark
# ======================================================================================================
ICON_CHEVRON = ('<svg class="chev" viewBox="0 0 16 16" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="2" '
                'stroke-linecap="square" stroke-linejoin="miter"><path d="M6 3.5l5 4.5-5 4.5"/></svg>')
ICON_BOOK = ('<svg class="ic" style="width:14px;height:14px" viewBox="0 0 16 16" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="1.5">'
             '<path d="M2.5 2.5h4a1.5 1.5 0 0 1 1.5 1.5v9.5a1 1 0 0 0-1-1h-4.5zM13.5 2.5h-4A1.5 1.5 0 0 0 8 4v9.5a1 1 0 0 1 1-1h4.5z"/></svg>')
ICON_CHECK = ('<svg class="ic" viewBox="0 0 16 16" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="2" '
              'stroke-linecap="square">' + ICONS["pass"] + '</svg>')
ICON_X = ('<svg class="ic" viewBox="0 0 16 16" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="2" '
          'stroke-linecap="square">' + ICONS["fail"] + '</svg>')
ICON_PLUS = ('<svg class="ic" style="width:14px;height:14px" viewBox="0 0 16 16" aria-hidden="true" fill="none" stroke="currentColor" '
             'stroke-width="1.5"><path d="M8 3v10M3 8h10"/></svg>')
ICON_RESET = ('<svg class="ic" viewBox="0 0 16 16" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="1.5">'
              '<path d="M2.5 8a5.5 5.5 0 1 0 1.8-4.1M2.5 2.5v3h3"/></svg>')
ICON_SEARCH = ('<svg class="ic" viewBox="0 0 16 16" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="1.5">'
               '<circle cx="6.5" cy="6.5" r="4.5"/><path d="M10 10l4.5 4.5"/></svg>')
LOGO = '<span class="logo" role="img" aria-label="Hallmark" style="font-size:22px;font-weight:600;letter-spacing:-.01em">Hallmark</span>'


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("results")
    ap.add_argument("output")
    ap.add_argument("--rules", help="rules file whose git history is shown in the rule panel (default: rules_source from the results)")
    ap.add_argument("--root", default=".", help="project root that evidence paths are relative to (default: current directory)")
    ap.add_argument("--editor", default="vscode", help="editor URL scheme for file links, e.g. vscode, cursor, idea (default: vscode)")
    ap.add_argument("--open", action="store_true", help="open the dashboard in the default browser")
    args = ap.parse_args()
    data = load(args.results)
    global ROOT, SCHEME
    ROOT, SCHEME = Path(args.root).resolve(), args.editor
    rules_path = find_rules_file(data, args.results, args.rules)
    data["rules_log"] = git_log(rules_path)
    data["rule_lines"] = heading_lines(rules_path)
    data["rule_text"] = rule_sections(rules_path)
    if rules_path:
        data["rules_path"] = str(rules_path.resolve())
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
