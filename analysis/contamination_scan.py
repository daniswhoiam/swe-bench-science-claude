"""Count-only scan of the Claude Fable 5.2 xhigh agent records for network or download attempts.

NOT RUNNABLE FROM THIS REPOSITORY ALONE: it reads the agent records inside the Pier job
folders, which are not published (see README, "Not included"). It runs against a local copy
of those job folders, for example the copy the benchmark maintainers can request.

Per trial it reads only task_*/agent/claude-code.txt (stream-JSON), or
task_*/agent/trajectory.json when that is missing. Nothing under verifier/ or tests/, and no
exception.txt, is ever opened. Output: one CSV row per run with counts and reason codes only
(analysis/out/contamination-scan.csv is the output of the run reported in
docs/network-scan.md).

The patterns, the classification and the self-test below are unchanged from the version
used for that run; they were fixed before any agent record was scanned. Only the input
handling differs: the job folder is an argument, and the author's internal task grouping
(which records the author was allowed to read) is removed, so every run is treated alike.
--context prints the matched snippets; the published run did not print any for the records
that were scanned without being read.

Usage:
  python -I analysis/contamination_scan.py --selftest
  python -I analysis/contamination_scan.py --jobs-dir <run-dir>/jobs [--csv PATH] [--context]
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import shlex
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
DEFAULT_CSV = HERE / "out" / "contamination-scan.csv"
JOB_RE = re.compile(r"^FXH-(\d{3})-s1$")

# ---------------------------------------------------------------------------------------
# Fixed patterns
# ---------------------------------------------------------------------------------------

# A. web tools
WEB_TOOL_NAMES = {"webfetch", "websearch"}

# B. shell network commands. A match must sit at a command position: start of the command
# string or after a newline, ; & | ( ` { ! or $( , optionally behind prefixes such as sudo,
# env, timeout, xargs, nohup, time, exec, then/do/else, or VAR=value assignments, and
# optionally behind a path (/opt/venv/bin/pip). Before matching, heredoc bodies are blanked
# (unless the heredoc is fed to a shell), quoted strings are blanked (unless they are the
# argument of sh -c / bash -c / eval), and # comments are blanked. Text lengths are
# preserved so offsets map back to the original command.
_CMD_POS = r"(?:^|(?<=[\n;&|(`{!]))[ \t]*"
_PREFIX = (
    r"(?:(?:sudo|exec|time|nohup|command|builtin|then|do|else|elif|nice|stdbuf|env|timeout|xargs)"
    r"(?:\s+-{1,2}\S+(?:\s+(?!-)\S+)?)*\s+(?:\d+[smhd]?\s+)?"
    r"|[A-Za-z_]\w*=\S*\s+)*"
)
_PATH = r"(?:[\w.~+-]*/)*"
_END = r"(?=\s|$|[;&|)])"
_FLAGS = r"(?:\s+-{1,2}\S+)*"

B_PATTERNS: list[tuple[str, str, re.Pattern]] = []


def _b(sub: str, body: str, kind: str = "plain") -> None:
    B_PATTERNS.append((sub, kind, re.compile(_CMD_POS + _PREFIX + _PATH + body, re.M)))


_b("download", r"(?:curl|wget)" + _END)
_b(
    "git",
    r"git(?:\s+(?:-C\s+\S+|-c\s+\S+|--[\w-]+(?:=\S+)?|-[A-Za-z]))*\s+"
    r"(?:clone|fetch|pull|ls-remote|submodule" + _FLAGS + r"\s+update)" + _END,
)
_b(
    "pip-install",
    r"(?:pip3?|python[\d.]*\s+-m\s+pip|uv\s+pip)" + _FLAGS + r"\s+install" + _END,
    "pip-install",
)
_b("pip-download", r"(?:pip3?|python[\d.]*\s+-m\s+pip)" + _FLAGS + r"\s+download" + _END)
_b("pip-install", r"uv" + _FLAGS + r"\s+add" + _END, "pip-install")
_b("pkgmgr", r"(?:conda|mamba)" + _FLAGS + r"\s+install" + _END)
_b("pkgmgr", r"npm" + _FLAGS + r"\s+install" + _END)
_b("pkgmgr", r"yarn" + _FLAGS + r"\s+add" + _END)
_b("pkgmgr", r"apt(?:-get)?" + _FLAGS + r"\s+install" + _END)
_b("pkgmgr", r"cargo" + _FLAGS + r"\s+install" + _END)
_b("pkgmgr", r"go" + _FLAGS + r"\s+get" + _END)
_b("vcs-other", r"svn" + _FLAGS + r"\s+checkout" + _END)
_b("vcs-other", r"hg" + _FLAGS + r"\s+clone" + _END)
# ssh/scp/nc/telnet followed by whitespace, and not by something that reads as an
# assignment, comparison, call or attribute (guards against Python in python -c strings).
_b(
    "remote-shell",
    r"(?:ssh|scp|nc|telnet)[ \t]+(?![ \t]*(?:[-+*/%]?=|==|[(),.:\]]))",
)
B_SUBTYPES = ["download", "git", "pip-install", "pip-download", "pkgmgr", "vcs-other", "remote-shell"]

_HEREDOC_RE = re.compile(r"(?<!<)<<(?!<)(-?)[ \t]*(['\"]?)([A-Za-z_][A-Za-z0-9_]*)\2")
_SHELL_BEFORE_HEREDOC = re.compile(r"(?:^|[\s;&|(])(?:\S*/)?(?:ba|z|da|k)?sh(?:\s+-\S+)*\s*$")
_SHELL_C_BEFORE_QUOTE = re.compile(
    r"(?:(?:^|[\s;&|(])(?:\S*/)?(?:ba|z|da|k)?sh(?:\s+-[A-Za-z]+)*\s+-[A-Za-z]*c[A-Za-z]*\s+"
    r"|(?:^|[\s;&|(])eval\s+)$"
)


def blank_heredocs(cmd: str) -> str:
    """Replace heredoc bodies with spaces (newlines kept), unless fed to a shell."""
    lines = cmd.split("\n")
    out: list[str] = []
    i = 0
    while i < len(lines):
        line = lines[i]
        out.append(line)
        i += 1
        for m in _HEREDOC_RE.finditer(line):
            keep = bool(_SHELL_BEFORE_HEREDOC.search(line[: m.start()]))
            delim = m.group(3)
            while i < len(lines):
                body = lines[i]
                i += 1
                if body.strip() == delim:
                    out.append(body)
                    break
                out.append(body if keep else " " * len(body))
    return "\n".join(out)


def blank_quotes_and_comments(s: str) -> str:
    """Blank quoted strings and # comments (same length). sh -c / eval arguments are kept."""
    out = list(s)
    n = len(s)
    i = 0
    while i < n:
        c = s[i]
        if c == "\\":
            i += 2
            continue
        if c in "'\"":
            if c == "'":
                j = s.find("'", i + 1)
            else:
                j = i + 1
                while j < n and s[j] != '"':
                    j += 2 if s[j] == "\\" else 1
                if j >= n:
                    j = -1
            if j == -1:  # unterminated: leave as literal
                i += 1
                continue
            if not _SHELL_C_BEFORE_QUOTE.search(s[max(0, i - 80) : i]):
                for k in range(i + 1, j):
                    out[k] = " "
            else:  # sh -c / eval argument: its content starts a command
                out[i] = "\n"
                out[j] = "\n"
            i = j + 1
            continue
        if c == "#" and (i == 0 or s[i - 1] in " \t\n;&|("):
            j = s.find("\n", i)
            j = n if j == -1 else j
            for k in range(i, j):
                out[k] = " "
            i = j
            continue
        i += 1
    return "".join(out)


def shell_view(cmd: str) -> str:
    return blank_quotes_and_comments(blank_heredocs(cmd))


# B-pip-local: install targets that are only local paths.
_PIP_VALUE_OPTS = {
    "-i", "--index-url", "--extra-index-url", "-f", "--find-links", "-t", "--target",
    "--prefix", "--root", "--src", "--python", "-p", "--upgrade-strategy", "-C",
    "--config-settings", "--global-option", "--install-option", "--platform",
    "--python-version", "--implementation", "--abi", "--only-binary", "--no-binary",
    "--progress-bar", "--log", "--cache-dir", "--trusted-host", "--proxy", "--retries",
    "--timeout", "--exists-action", "--cert", "--client-cert", "--report", "--optional",
    "--group", "--extra", "--package", "--directory", "--project",
}
_REQ_OPTS = {"-r", "--requirement", "-c", "--constraint"}
_EDITABLE_OPTS = {"-e", "--editable"}
_ARGS_END = re.compile(r"[\n;&|)]|(?:(?<=\s)\d+)?[<>]")


def _is_url(tok: str) -> bool:
    return "://" in tok or tok.startswith("git+") or bool(re.match(r"^[\w.-]+@[\w.-]+:", tok))


def _is_local_path(tok: str) -> bool:
    if "$" in tok or "`" in tok or _is_url(tok):
        return False
    if tok in (".", "..") or tok.startswith((".", "/", "~")):
        return True
    if "/" in tok:
        return True
    return tok.endswith((".whl", ".tar.gz", ".zip"))


def pip_targets_local(args: str) -> bool:
    """True if a pip/uv install's arguments name only local paths (or -r files), no URL."""
    try:
        toks = shlex.split(args, comments=False)
    except ValueError:
        toks = args.split()
    has_local = False
    i = 0
    while i < len(toks):
        tok = toks[i]
        nxt = toks[i + 1] if i + 1 < len(toks) else None
        if _is_url(tok):
            return False
        if tok in _EDITABLE_OPTS or tok in _REQ_OPTS:
            if nxt is None or not _is_local_path(nxt) and tok in _EDITABLE_OPTS:
                return False
            if _is_url(nxt):
                return False
            has_local = True
            i += 2
            continue
        if tok.startswith("--editable=") or (tok.startswith("-e") and len(tok) > 2 and not tok.startswith("--")):
            val = tok.split("=", 1)[1] if tok.startswith("--editable=") else tok[2:]
            if not _is_local_path(val):
                return False
            has_local = True
            i += 1
            continue
        if tok.startswith(("--requirement=", "--constraint=")):
            if _is_url(tok.split("=", 1)[1]):
                return False
            has_local = True
            i += 1
            continue
        if tok in _PIP_VALUE_OPTS:
            if nxt is not None and _is_url(nxt):
                return False
            i += 2
            continue
        if tok.startswith("-"):
            if "=" in tok and _is_url(tok.split("=", 1)[1]):
                return False
            i += 1
            continue
        if not _is_local_path(tok):
            return False
        has_local = True
        i += 1
    return has_local


def match_b(cmd: str) -> list[tuple[str, bool, int, int]]:
    """Return [(subtype, is_pip_local, start, end)] for B matches in a Bash command."""
    view = shell_view(cmd)
    hits = []
    for sub, kind, rx in B_PATTERNS:
        for m in rx.finditer(view):
            local = False
            if kind == "pip-install":
                cut = _ARGS_END.search(view, m.end())
                rest = cmd[m.end() : cut.start()] if cut else cmd[m.end() :]
                local = pip_targets_local(rest)
            hits.append((sub, local, m.start(), m.end()))
    return hits


# C / D. network code strings
NET_CODE_STRINGS = [
    "requests.get", "requests.post", "urllib.request", "urlopen", "httpx.", "http.client",
    "socket.create_connection", "socket.socket", "aiohttp",
]
HTTP_URL_RE = re.compile(r"https?://[^\s'\"`<>]")


def match_net_code(text: str) -> list[tuple[int, int]]:
    spans = []
    for s in NET_CODE_STRINGS:
        start = 0
        while True:
            k = text.find(s, start)
            if k < 0:
                break
            spans.append((k, k + len(s)))
            start = k + 1
    spans += [(m.start(), m.end()) for m in HTTP_URL_RE.finditer(text)]
    return sorted(spans)


# E. outcome signals in tool results
E_BLOCKED = [
    "ERR_ACCESS_DENIED", "403 Forbidden", "Could not resolve host", "Name or service not known",
    "Temporary failure in name resolution", "Network is unreachable", "Connection refused",
    "ProxyError", "Max retries exceeded", "Failed to establish a new connection",
    "Could not fetch URL", "No matching distribution found", "Connection timed out",
]
E_SUCCESS = [
    "Downloading http", "Downloading https", "Saving to:", "HTTP/1.1 200", "HTTP/2 200",
    "Receiving objects:",
]
CLONE_ERRORS = E_BLOCKED + ["fatal:"]


def match_e(text: str) -> tuple[list[str], list[str]]:
    blocked = [s for s in E_BLOCKED if s in text]
    success = [s for s in E_SUCCESS if s in text]
    if "Cloning into" in text and not any(s in text for s in CLONE_ERRORS):
        success.append("Cloning into")
    return blocked, success


# F. host categories (fixed lists)
F_CATS = ["provider", "pypi", "conda", "code_hosting", "scholarly", "localhost", "other"]
_F_DOMAINS = {
    "provider": ["anthropic.com"],
    "pypi": ["pypi.org", "pythonhosted.org", "pypi.python.org"],
    "conda": ["anaconda.org", "anaconda.com", "conda-forge.org"],
    "code_hosting": [
        "github.com", "githubusercontent.com", "gitlab.com", "bitbucket.org", "codeberg.org",
        "sourceforge.net", "gitee.com", "sr.ht",
    ],
    "scholarly": [
        "doi.org", "arxiv.org", "nature.com", "science.org", "sciencemag.org",
        "sciencedirect.com", "elsevier.com", "springer.com", "springeropen.com", "wiley.com",
        "iop.org", "aps.org", "aip.org", "scitation.org", "acs.org", "rsc.org", "pnas.org",
        "cell.com", "plos.org", "frontiersin.org", "mdpi.com", "tandfonline.com", "oup.com",
        "cambridge.org", "ieee.org", "acm.org", "jstor.org", "ncbi.nlm.nih.gov", "biorxiv.org",
        "medrxiv.org", "chemrxiv.org", "semanticscholar.org", "researchgate.net", "aanda.org",
        "iucr.org", "ams.org", "siam.org", "annualreviews.org", "osti.gov", "adsabs.harvard.edu",
        "agu.org", "copernicus.org", "ametsoc.org", "sagepub.com", "degruyter.com",
        "biomedcentral.com", "nejm.org", "thelancet.com", "bmj.com",
        "royalsocietypublishing.org", "ascelibrary.org", "asme.org", "europepmc.org",
    ],
}
_URL_HOST_RE = re.compile(r"\b(?:https?|ftp|sftp|git|ssh|svn)://([^\s/'\"`<>?#)\]}\\,;|]+)")
_SCP_HOST_RE = re.compile(r"\bgit@([\w.-]+):")


def host_category(host: str) -> str:
    h = host.lower().strip(".")
    if h in ("localhost", "0.0.0.0", "::1", "[::1]") or h.startswith("127.") or h.endswith(".localhost"):
        return "localhost"
    for cat, doms in _F_DOMAINS.items():
        for d in doms:
            if h == d or h.endswith("." + d):
                return cat
    if "conda-forge" in h:
        return "conda"
    return "other"


def url_hosts(text: str) -> list[str]:
    hosts = []
    for m in _URL_HOST_RE.finditer(text):
        hp = m.group(1).rsplit("@", 1)[-1]
        if hp.startswith("["):
            host = hp.split("]")[0] + "]"
        else:
            host = hp.split(":")[0]
        if host:
            hosts.append(host)
    hosts += [m.group(1) for m in _SCP_HOST_RE.finditer(text)]
    return hosts


# ---------------------------------------------------------------------------------------
# Record parsing
# ---------------------------------------------------------------------------------------


def _result_text(content) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for b in content:
            if isinstance(b, dict):
                if isinstance(b.get("text"), str):
                    parts.append(b["text"])
                elif isinstance(b.get("content"), (str, list)):
                    parts.append(_result_text(b["content"]))
            elif isinstance(b, str):
                parts.append(b)
        return "\n".join(parts)
    return "" if content is None else str(content)


class Record:
    def __init__(self) -> None:
        self.calls: dict[str, tuple[str, dict]] = {}  # id -> (name, input)
        self.call_order: list[str] = []
        self.results: dict[str, str] = {}
        self.server_tool_uses: list[str] = []
        self.usage_search = 0
        self.usage_fetch = 0
        self.msg_usage_web = 0
        self.model_usage_search = 0
        self.subagents_spawned = 0
        self.permission_denials = 0
        self.result_events = 0
        self.sidechain_msgs = 0
        self.events = 0
        self.unparsed = 0

    def add_call(self, cid: str, name: str, inp) -> None:
        if cid in self.calls:
            return
        if not isinstance(inp, dict):
            inp = {"_raw": inp if isinstance(inp, str) else json.dumps(inp)}
        self.calls[cid] = (name or "", inp)
        self.call_order.append(cid)

    def add_result(self, cid: str, text: str) -> None:
        if cid not in self.results:
            self.results[cid] = text


def parse_stream(lines) -> Record:
    rec = Record()
    seen_msg_usage: set[str] = set()
    anon = 0
    for line in lines:
        line = line.strip()
        if not line:
            continue
        try:
            o = json.loads(line)
        except Exception:
            rec.unparsed += 1
            continue
        if not isinstance(o, dict):
            rec.unparsed += 1
            continue
        rec.events += 1
        t = o.get("type")
        if t in ("assistant", "user"):
            if o.get("parent_tool_use_id"):
                rec.sidechain_msgs += 1
            msg = o.get("message") or {}
            content = msg.get("content")
            if isinstance(content, list):
                for b in content:
                    if not isinstance(b, dict):
                        continue
                    bt = b.get("type")
                    if bt == "tool_use":
                        cid = b.get("id") or f"anon{anon}"
                        anon += 1
                        rec.add_call(cid, b.get("name"), b.get("input"))
                    elif bt == "server_tool_use":
                        rec.server_tool_uses.append(str(b.get("name", "")))
                    elif bt == "tool_result":
                        rec.add_result(b.get("tool_use_id") or "", _result_text(b.get("content")))
            u = msg.get("usage") if t == "assistant" else None
            if isinstance(u, dict) and isinstance(u.get("server_tool_use"), dict):
                mid = msg.get("id") or f"m{rec.events}"
                if mid not in seen_msg_usage:
                    seen_msg_usage.add(mid)
                    stu = u["server_tool_use"]
                    rec.msg_usage_web += int(stu.get("web_search_requests") or 0)
                    rec.msg_usage_web += int(stu.get("web_fetch_requests") or 0)
        elif t == "result":
            rec.result_events += 1
            u = o.get("usage") or {}
            stu = u.get("server_tool_use") or {}
            rec.usage_search += int(stu.get("web_search_requests") or 0)
            rec.usage_fetch += int(stu.get("web_fetch_requests") or 0)
            for mu in (o.get("modelUsage") or {}).values():
                if isinstance(mu, dict):
                    rec.model_usage_search += int(mu.get("webSearchRequests") or 0)
            pd = o.get("permission_denials")
            if isinstance(pd, list):
                rec.permission_denials += len(pd)
            ss = o.get("subagent_stats")
            if isinstance(ss, dict):
                rec.subagents_spawned += int(ss.get("spawned") or 0)
    return rec


def parse_atif(path: Path) -> Record:
    rec = Record()
    d = json.loads(path.read_text())
    for st in d.get("steps", []) if isinstance(d, dict) else []:
        rec.events += 1
        extra = st.get("extra") or {}
        if isinstance(extra, dict) and extra.get("is_sidechain"):
            rec.sidechain_msgs += 1
        for tc in st.get("tool_calls") or []:
            rec.add_call(tc.get("tool_call_id") or f"s{rec.events}", tc.get("function_name"), tc.get("arguments"))
        obs = st.get("observation") or {}
        for r in obs.get("results") or [] if isinstance(obs, dict) else []:
            rec.add_result(r.get("source_call_id") or "", _result_text(r.get("content")))
    return rec


# ---------------------------------------------------------------------------------------
# Classification
# ---------------------------------------------------------------------------------------

COLS = (
    ["A_web_tool_uses", "A_server_tool_uses", "A_usage_web_search_requests",
     "A_usage_web_fetch_requests", "A_msg_usage_web_requests", "A_modelusage_web_search"]
    + ["B", "B_pip_local"] + [f"B_{s.replace('-', '_')}" for s in B_SUBTYPES]
    + ["C", "D", "E_blocked", "E_success", "E_blocked_paired", "E_success_paired"]
    + ["B_result_blocked", "B_result_success", "B_result_no_signal",
       "C_result_blocked", "C_result_success", "C_result_no_signal"]
    + [f"F_{c}" for c in F_CATS]
)
COVERAGE_COLS = [
    "record", "events", "unparsed_lines", "result_events", "tool_uses", "bash_calls",
    "write_edit_calls", "tool_results", "subagent_tool_uses", "subagents_spawned",
    "sidechain_msgs", "permission_denials",
]


def _snip(text: str, a: int, b: int, w: int = 160) -> str:
    s = text[max(0, a - w) : min(len(text), b + w)]
    return s.replace("\n", "\\n")


def classify(rec: Record, want_snippets: bool) -> tuple[Counter, list[tuple[str, str]]]:
    c: Counter = Counter()
    snips: list[tuple[str, str]] = []
    net_calls: set[str] = set()
    b_calls: list[str] = []
    c_calls: list[str] = []
    c["tool_uses"] = len(rec.calls)
    c["tool_results"] = len(rec.results)
    for cid in rec.call_order:
        name, inp = rec.calls[cid]
        lname = name.lower()
        if lname in ("task", "agent"):
            c["subagent_tool_uses"] += 1
        # A
        if lname in WEB_TOOL_NAMES:
            c["A_web_tool_uses"] += 1
            net_calls.add(cid)
            if want_snippets:
                snips.append(("A", f"{name}: {json.dumps(inp)[:400]}"))
        # B / C / F
        if lname == "bash":
            c["bash_calls"] += 1
            cmd = inp.get("command") if isinstance(inp.get("command"), str) else json.dumps(inp)
            bh = match_b(cmd)
            ch = match_net_code(cmd)
            if bh:
                net_calls.add(cid)
                nonlocal_hits = [h for h in bh if not h[1]]
                if nonlocal_hits:
                    c["B"] += 1
                    b_calls.append(cid)
                    for sub in sorted({h[0] for h in nonlocal_hits}):
                        c[f"B_{sub.replace('-', '_')}"] += 1
                else:
                    c["B_pip_local"] += 1
                if want_snippets:
                    for sub, local, a, b in bh:
                        snips.append((f"B{'-pip-local' if local else ''}:{sub}", _snip(cmd, a, b)))
            if ch:
                c["C"] += 1
                c_calls.append(cid)
                net_calls.add(cid)
                if want_snippets:
                    for a, b in ch[:3]:
                        snips.append(("C", _snip(cmd, a, b)))
            if bh or ch:
                cats = {host_category(h) for h in url_hosts(cmd)}
                for cat in cats:
                    c[f"F_{cat}"] += 1
                if want_snippets and cats:
                    snips.append(("F", ", ".join(f"{h}->{host_category(h)}" for h in url_hosts(cmd))))
        # D
        if lname in ("write", "edit", "multiedit"):
            c["write_edit_calls"] += 1
            text = "\n".join(_strings(inp))
            dh = match_net_code(text)
            if dh:
                c["D"] += 1
                if want_snippets:
                    a, b = dh[0]
                    snips.append(("D", f"{inp.get('file_path', '')}: {_snip(text, a, b, 100)}"))
    c["A_server_tool_uses"] = sum(1 for n in rec.server_tool_uses if n.lower().startswith("web"))
    c["A_usage_web_search_requests"] = rec.usage_search
    c["A_usage_web_fetch_requests"] = rec.usage_fetch
    c["A_msg_usage_web_requests"] = rec.msg_usage_web
    c["A_modelusage_web_search"] = rec.model_usage_search
    # E
    for cid, text in rec.results.items():
        blocked, success = match_e(text)
        if blocked:
            c["E_blocked"] += 1
            if cid in net_calls:
                c["E_blocked_paired"] += 1
        if success:
            c["E_success"] += 1
            if cid in net_calls:
                c["E_success_paired"] += 1
        if want_snippets and (blocked or success):
            name = rec.calls.get(cid, ("?", {}))[0]
            key = (blocked + success)[0]
            k = text.find(key)
            snips.append((
                f"E-{'blocked' if blocked else 'success'}({name}{', paired' if cid in net_calls else ''})",
                f"{blocked + success}: {_snip(text, k, k + len(key), 200)}",
            ))
    # outcome of each B / C call, read from that call's own result (reporting cross-tab)
    for prefix, ids in (("B", b_calls), ("C", c_calls)):
        for cid in ids:
            blocked, success = match_e(rec.results.get(cid, ""))
            if blocked:
                c[f"{prefix}_result_blocked"] += 1
            if success:
                c[f"{prefix}_result_success"] += 1
            if not blocked and not success:
                c[f"{prefix}_result_no_signal"] += 1
    c["events"] = rec.events
    c["unparsed_lines"] = rec.unparsed
    c["result_events"] = rec.result_events
    c["subagents_spawned"] = rec.subagents_spawned
    c["sidechain_msgs"] = rec.sidechain_msgs
    c["permission_denials"] = rec.permission_denials
    return c, snips


def _strings(x) -> list[str]:
    if isinstance(x, str):
        return [x]
    if isinstance(x, dict):
        return [s for v in x.values() for s in _strings(v)]
    if isinstance(x, list):
        return [s for v in x for s in _strings(v)]
    return []


def is_flagged(c: Counter) -> list[str]:
    reasons = []
    if any(c[k] for k in COLS if k.startswith("A_")):
        reasons.append("A")
    if c["B"]:
        reasons.append("B")
    if c["C"]:
        reasons.append("C")
    if c["E_success"]:
        reasons.append("E-success")
    if any(c[f"F_{cat}"] for cat in F_CATS if cat != "provider"):
        reasons.append("F-nonprovider")
    return reasons


# ---------------------------------------------------------------------------------------
# Self-test on synthetic strings
# ---------------------------------------------------------------------------------------


def selftest() -> int:
    fails = []

    def b_subs(cmd):
        return sorted({(s, loc) for s, loc, _, _ in match_b(cmd)})

    b_pos = {
        "curl -sSL https://example.com/x": ("download", False),
        "cd /app && wget http://x/y.tar.gz": ("download", False),
        "timeout 30 curl -I https://pypi.org": ("download", False),
        "x=$(curl -s https://a.b/c)": ("download", False),
        "for u in a b; do curl $u; done": ("download", False),
        "env A=1 curl x": ("download", False),
        "sudo -E wget x": ("download", False),
        "ls | xargs -n 1 curl -O": ("download", False),
        "bash -c 'curl https://x'": ("download", False),
        "bash <<'EOF'\ncurl https://x\nEOF": ("download", False),
        "git clone https://github.com/a/b.git": ("git", False),
        "git clone /local/repo dest": ("git", False),
        "git -C repo fetch origin": ("git", False),
        "cd x; git pull": ("git", False),
        "git ls-remote https://github.com/a/b": ("git", False),
        "git submodule update --init": ("git", False),
        "pip install numpy==1.26": ("pip-install", False),
        "python -m pip install requests": ("pip-install", False),
        "/opt/venv/bin/pip install -U scipy": ("pip-install", False),
        "pip3 install foo": ("pip-install", False),
        "pip download foo": ("pip-download", False),
        "pip download -d /tmp .": ("pip-download", False),
        "uv pip install foo": ("pip-install", False),
        "uv add foo": ("pip-install", False),
        "pip install -e . numpy": ("pip-install", False),
        "pip install -r https://x/req.txt": ("pip-install", False),
        "pip install --index-url https://x/simple y": ("pip-install", False),
        "pip install git+https://github.com/a/b": ("pip-install", False),
        "pip install -e git+https://github.com/a/b#egg=b": ("pip-install", False),
        "pip install $PKG": ("pip-install", False),
        "pip install -q": ("pip-install", False),
        "conda install -y numpy": ("pkgmgr", False),
        "mamba install x": ("pkgmgr", False),
        "npm install": ("pkgmgr", False),
        "yarn add x": ("pkgmgr", False),
        "apt-get install -y x": ("pkgmgr", False),
        "sudo apt install x": ("pkgmgr", False),
        "cargo install x": ("pkgmgr", False),
        "go get x": ("pkgmgr", False),
        "svn checkout x": ("vcs-other", False),
        "hg clone x": ("vcs-other", False),
        "ssh user@host ls": ("remote-shell", False),
        "scp a host:b": ("remote-shell", False),
        "echo hi | nc host 80": ("remote-shell", False),
        "telnet host 80": ("remote-shell", False),
        "pip install -e .": ("pip-install", True),
        "pip install .": ("pip-install", True),
        "pip install ./pkg": ("pip-install", True),
        "pip install /tmp/x.whl": ("pip-install", True),
        "pip install -r requirements.txt": ("pip-install", True),
        "pip install -e '.[test]' --no-deps": ("pip-install", True),
        "uv pip install -e .": ("pip-install", True),
        "cd /app && python -m pip install --no-build-isolation -e /app/source 2>&1 | tail": ("pip-install", True),
        "pip install --no-index --find-links /wheels -e .": ("pip-install", True),
    }
    for cmd, want in b_pos.items():
        got = b_subs(cmd)
        if got != [want]:
            fails.append(f"B pos {cmd!r}: got {got}, want {[want]}")
    b_neg = [
        "grep -rn 'curl' .", 'grep -E "curl|wget" f', "echo curl is missing", "ls ~/.ssh",
        "python3 - <<'EOF'\nimport os\nnc = 3\nprint(nc)\nssh = 1\ncurl -s x\nEOF",
        'python -c "\nnc = 3\nprint(nc)\ncurl x\n"', "cat > f.sh <<EOF\ncurl https://x\nEOF",
        "# curl later\nls", "curly braces", "git log", "git status", "pip list", "pip show x",
        "conda list", "npm test", "func x", "sync", "scpx a", "python run.py --curl",
        "git diff -- src/fetch.py", "echo 'git clone x'", "make install", "pip --version",
        "rg -n 'urlopen|wget' src", "ls nc_files/", "cat ssh_config",
    ]
    for cmd in b_neg:
        got = b_subs(cmd)
        if got:
            fails.append(f"B neg {cmd!r}: got {got}")

    c_pos = [
        "python -c 'import urllib.request; urllib.request.urlopen(\"http://x\")'",
        "python - <<EOF\nimport requests\nrequests.get(u)\nEOF", "curl https://x",
        "python -c 'import httpx; httpx.get(u)'", "python -c 'import socket; socket.socket()'",
        "python -c 'import aiohttp'", "python -c 'import http.client'",
        "python -c 'requests.post(u)'", "python -c 'socket.create_connection((h, 80))'",
        "echo http://localhost:8000",
    ]
    for t in c_pos:
        if not match_net_code(t):
            fails.append(f"C pos {t!r}")
    c_neg = ["python run.py", "echo http", "grep -rn requests .", "ls https", "pip show httpx",
             "cat docs/http_notes.txt", "echo https:// "]
    for t in c_neg:
        if match_net_code(t):
            fails.append(f"C neg {t!r}: {match_net_code(t)}")

    e_cases = {
        "curl: (6) Could not resolve host: x": (True, False),
        "ERROR: No matching distribution found for foo": (True, False),
        "HTTP/1.1 403 Forbidden": (True, False),
        "ProxyError('Cannot connect to proxy.')": (True, False),
        "squid: ERR_ACCESS_DENIED": (True, False),
        "all good": (False, False),
        "  Downloading https://files.pythonhosted.org/x.whl (1 MB)": (False, True),
        "Saving to: 'x.tar.gz'": (False, True),
        "HTTP/2 200 \ncontent-type: x": (False, True),
        "Receiving objects: 100% (10/10)": (False, True),
        "Cloning into 'x'...\ndone.": (False, True),
        "Cloning into 'x'...\nfatal: unable to access 'https://x/': Could not resolve host: x": (True, False),
        "Cloning into 'x'...\nfatal: repository not found": (False, False),
    }
    for t, (wb, ws) in e_cases.items():
        b, s = match_e(t)
        if bool(b) != wb or bool(s) != ws:
            fails.append(f"E {t!r}: blocked={b} success={s}")

    f_cases = {
        "https://api.anthropic.com/v1/messages": "provider",
        "https://files.pythonhosted.org/p/x.whl": "pypi",
        "https://pypi.org/simple/x": "pypi",
        "https://conda.anaconda.org/conda-forge": "conda",
        "https://raw.githubusercontent.com/a/b/c": "code_hosting",
        "https://user:tok@github.com/a/b.git": "code_hosting",
        "git@github.com:a/b.git": "code_hosting",
        "https://doi.org/10.1/x": "scholarly",
        "https://www.nature.com/articles/x": "scholarly",
        "https://export.arxiv.org/abs/1": "scholarly",
        "http://localhost:8000/x": "localhost",
        "http://127.0.0.1:5000": "localhost",
        "http://0.0.0.0:80": "localhost",
        "https://example.com": "other",
        "https://evilgithub.com/x": "other",
        "https://github.com.evil.net/x": "other",
    }
    for t, want in f_cases.items():
        hs = url_hosts(t)
        got = [host_category(h) for h in hs]
        if got != [want]:
            fails.append(f"F {t!r}: got {got} want {want}")

    # end-to-end on a synthetic stream
    lines = [
        "[claude-code:warning] not json",
        json.dumps({"type": "assistant", "message": {"id": "m1", "content": [
            {"type": "tool_use", "id": "t1", "name": "WebFetch", "input": {"url": "https://x"}},
            {"type": "tool_use", "id": "t2", "name": "Bash", "input": {"command": "curl https://github.com/a"}},
            {"type": "tool_use", "id": "t3", "name": "Bash", "input": {"command": "pip install -e ."}},
            {"type": "tool_use", "id": "t4", "name": "Write", "input": {"file_path": "/a.py", "content": "# see https://doi.org/x"}},
            {"type": "tool_use", "id": "t5", "name": "websearch", "input": {"query": "q"}},
            {"type": "server_tool_use", "id": "s1", "name": "web_search", "input": {}},
            {"type": "tool_use", "id": "t6", "name": "Bash", "input": {"command": "ls"}},
        ], "usage": {"server_tool_use": {"web_search_requests": 1, "web_fetch_requests": 0}}}}),
        json.dumps({"type": "assistant", "message": {"id": "m1", "content": [
            {"type": "tool_use", "id": "t2", "name": "Bash", "input": {"command": "curl https://github.com/a"}},
        ], "usage": {"server_tool_use": {"web_search_requests": 1, "web_fetch_requests": 0}}}}),
        json.dumps({"type": "user", "message": {"content": [
            {"type": "tool_result", "tool_use_id": "t2", "content": "curl: (56) CONNECT tunnel failed, response 403\nERR_ACCESS_DENIED"},
            {"type": "tool_result", "tool_use_id": "t3", "content": [{"type": "text", "text": "Successfully installed x"}]},
            {"type": "tool_result", "tool_use_id": "t6", "content": "Saving to: 'notes'"},
        ]}}),
        json.dumps({"type": "result", "usage": {"server_tool_use": {"web_search_requests": 2, "web_fetch_requests": 1}},
                    "modelUsage": {"m": {"webSearchRequests": 2}}, "permission_denials": [],
                    "subagent_stats": {"spawned": 0}}),
    ]
    rec = parse_stream(lines)
    c, _ = classify(rec, False)
    want = {"A_web_tool_uses": 2, "A_server_tool_uses": 1, "A_usage_web_search_requests": 2,
            "A_usage_web_fetch_requests": 1, "A_msg_usage_web_requests": 1,
            "A_modelusage_web_search": 2, "B": 1, "B_pip_local": 1, "B_download": 1, "C": 1,
            "D": 1, "E_blocked": 1, "E_success": 1, "E_blocked_paired": 1,
            "E_success_paired": 0, "B_result_blocked": 1, "B_result_no_signal": 0,
            "C_result_blocked": 1, "F_code_hosting": 1, "F_provider": 0, "unparsed_lines": 1,
            "tool_uses": 6, "bash_calls": 3, "write_edit_calls": 1}
    for k, v in want.items():
        if c[k] != v:
            fails.append(f"stream {k}: got {c[k]} want {v}")
    if is_flagged(c) != ["A", "B", "C", "E-success", "F-nonprovider"]:
        fails.append(f"flag: {is_flagged(c)}")

    n = len(b_pos) + len(b_neg) + len(c_pos) + len(c_neg) + len(e_cases) + len(f_cases) + len(want) + 1
    if fails:
        print(f"SELFTEST FAILED ({len(fails)} of {n} checks):")
        for f in fails:
            print("  " + f)
        return 1
    print(f"selftest ok: {n} synthetic checks passed")
    return 0


# ---------------------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------------------


def find_record(trial: Path) -> tuple[str, Path | None]:
    cc = trial / "agent" / "claude-code.txt"
    if cc.is_file() and cc.stat().st_size > 0:
        return "claude-code.txt", cc
    tj = trial / "agent" / "trajectory.json"
    if tj.is_file() and tj.stat().st_size > 0:
        return "trajectory.json", tj
    return "none", None


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--selftest", action="store_true", help="run synthetic pattern checks and exit")
    ap.add_argument("--jobs-dir", type=Path, help="folder with the FXH-<task>-s1 job folders (not published)")
    ap.add_argument("--context", action="store_true", help="also print matched snippets")
    ap.add_argument("--csv", type=Path, default=DEFAULT_CSV)
    args = ap.parse_args()

    if args.selftest:
        return selftest()
    if args.jobs_dir is None:
        ap.error("--jobs-dir is required (the job folders are not part of this repository)")
    if selftest() != 0:
        return 1

    rows = []
    records_used: Counter = Counter()
    snippets: dict[str, list[tuple[str, str]]] = {}
    errors = []
    for job in sorted(args.jobs_dir.iterdir()):
        m = JOB_RE.match(job.name)
        if not m or not job.is_dir():
            continue
        task = m.group(1)
        trials = sorted(p for p in job.glob("task_*") if p.is_dir())
        for trial in trials:
            kind, path = find_record(trial)
            records_used[kind] += 1
            c: Counter = Counter()
            snips: list = []
            if path is not None:
                try:
                    if kind == "claude-code.txt":
                        with path.open(encoding="utf-8", errors="replace") as fh:
                            rec = parse_stream(fh)
                    else:
                        rec = parse_atif(path)
                    c, snips = classify(rec, want_snippets=args.context)
                except Exception as e:  # never echo content
                    errors.append((task, type(e).__name__))
            row = {"task_id": task}
            row.update({k: c[k] for k in COVERAGE_COLS if k != "record"})
            row.update({k: c[k] for k in COLS})
            row["flag_reasons"] = "+".join(is_flagged(c))
            rows.append(row)
            if snips:
                snippets[task] = snips

    args.csv.parent.mkdir(parents=True, exist_ok=True)
    fields = ["task_id"] + [k for k in COVERAGE_COLS if k != "record"] + COLS + ["flag_reasons"]
    with args.csv.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields, lineterminator="\n")
        w.writeheader()
        w.writerows(rows)

    # ---- console: counts and task IDs only (snippets only with --context) ----
    print(f"\nscanned {len(rows)} trials; csv -> {args.csv}")
    print("records used:", dict(records_used))
    if errors:
        print("parse errors:", errors)
    print(f"\n{'category':32s} {'sum':>8s} {'trials>0':>9s}")
    for k in COLS + ["unparsed_lines", "subagent_tool_uses", "subagents_spawned",
                     "sidechain_msgs", "permission_denials"]:
        s = sum(int(r[k]) for r in rows)
        n = sum(1 for r in rows if int(r[k]) > 0)
        print(f"{k:32s} {s:8d} {n:9d}")
    flagged = [(r["task_id"], r["flag_reasons"]) for r in rows if r["flag_reasons"]]
    print(f"\nflagged runs ({len(flagged)}):")
    for t, why in flagged:
        print(f"  {t}  {why}")
    if args.context:
        print("\n---- matched context ----")
        for task, snips in sorted(snippets.items()):
            print(f"\n### {task}")
            for cat, s in snips:
                print(f"  [{cat}] {s[:700]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
