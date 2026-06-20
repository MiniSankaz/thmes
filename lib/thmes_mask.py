"""thmes_mask — Privacy masking vault for the cloud relay.

Local model masks sensitive data → cloud sees only placeholders → local
restores the real values. The vault (real↔token map) is session-scoped and
lives only in RAM — it is NEVER written to disk and NEVER sent to the cloud.

Pipeline (see bin/thmes `run_mask_pipeline`):
    real text → MaskVault.mask() → leak_scan() guard → cloud → MaskVault.unmask()

Detection is hybrid:
  • RULE_SPECS — regex for structured secrets (email, phone, Thai ID, card,
    API keys, .env secrets, private-key blocks, IP, home paths).
  • ner_fn     — an injected callable (local LLM) that tags contextual entities
    (person / org / project names) the regexes can't see.
  • deny_list  — user-supplied exact terms always masked.

Substitution is deterministic (exact string replace, longest-first) so the
restore step can never hallucinate a value back in. Over-masking is preferred
to under-masking: when in doubt the vault masks more, never less.
"""
from __future__ import annotations
import json
import re
from typing import Callable, Iterable


# ── Category groups (the on/off toggle) → the placeholder labels they enable ──
# A user enables coarse groups ("email", "secret", "person", "net"); each maps
# to the fine-grained labels used in placeholders so vault output stays readable.
GROUP_LABELS = {
    "email":  {"EMAIL", "PHONE", "THAIID", "CARD", "ACCOUNT", "DOCID", "SSN"},
    "secret": {"PRIVKEY", "APIKEY", "SECRET"},
    "person": {"PERSON", "ORG", "PROJECT", "TERM"},   # local-model NER + deny-list
    "net":    {"IP", "PATH"},
}
DEFAULT_GROUPS = ("email", "secret", "person", "net")

# Labels leak_scan() ALWAYS checks regardless of which groups are enabled — the
# defence-in-depth net: even with `secret` turned off, an API key / private key
# must never leave the machine.
_LEAK_ALWAYS = {"EMAIL", "PHONE", "THAIID", "CARD", "ACCOUNT", "SSN", "PRIVKEY", "APIKEY", "SECRET", "IP"}


# ── Validators (cut false positives on the loose numeric patterns) ───────────
def _luhn(num: str) -> bool:
    digits = [int(c) for c in num if c.isdigit()]
    if len(digits) < 13:
        return False
    total, parity = 0, len(digits) % 2
    for i, d in enumerate(digits):
        if i % 2 == parity:
            d *= 2
            if d > 9:
                d -= 9
        total += d
    return total % 10 == 0


def _valid_thai_id(num: str) -> bool:
    d = [int(c) for c in num if c.isdigit()]
    if len(d) != 13:
        return False
    s = sum(d[i] * (13 - i) for i in range(12))
    return (11 - (s % 11)) % 10 == d[12]


# Labeled domain identifiers (medical / HR / legal). The label is matched, the
# VALUE after it (which must contain a digit) is masked. A lookbehind requires the
# label to start at a non-word position so it can't fire inside a longer word.
_DOCID_LABELS = (
    r"HN|AN|MRN|VN|OPD|IPD"                                                # medical
    r"|รหัสผู้ป่วย|รหัสคนไข้|เลข(?:ที่)?ผู้ป่วย"
    r"|รหัสพนักงาน|พนักงานเลขที่|เลขประจำตัวพนักงาน|staff\s*id|emp(?:loyee)?\.?\s*(?:id|no\.?)"  # HR
    r"|case\s*no\.?|คดีหมายเลข(?:ดำ|แดง)?ที่|คดีหมายเลข|หมายเลขคดี|เลขคดี"   # legal
)
_DOCID_RX = (r"(?i)(?<![\w฀-๿])(?:" + _DOCID_LABELS +
             r")\s*[:#.]?\s*((?=\S*\d)[A-Za-z0-9฀-๿][A-Za-z0-9฀-๿\-./]{1,20})")

# ── Rule specs: (label, pattern, value_group, validator) ─────────────────────
# value_group=0 → mask the whole match; >0 → mask only that capture group (e.g.
# the secret VALUE after `key = ...`, leaving the key name for cloud context).
RULE_SPECS = [
    ("PRIVKEY", r"-----BEGIN [A-Z0-9 ]*PRIVATE KEY-----[\s\S]*?-----END [A-Z0-9 ]*PRIVATE KEY-----", 0, None),
    ("EMAIL",   r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b", 0, None),
    ("APIKEY",  r"\b(?:sk-[A-Za-z0-9]{20,}|AKIA[0-9A-Z]{16}|gh[posru]_[A-Za-z0-9]{30,}|xox[baprs]-[A-Za-z0-9\-]{10,}|AIza[0-9A-Za-z_\-]{35})\b", 0, None),
    ("SECRET",  r"""(?im)\b(?:pass(?:word|wd)?|secret|token|api[_\-]?key|access[_\-]?key|client[_\-]?secret|auth(?:orization)?)\b\s*[:=]\s*["']?([^\s"']{6,})""", 1, None),
    ("THAIID",  r"\b\d(?:[\- ]?\d){12}\b", 0, _valid_thai_id),
    ("CARD",    r"\b\d(?:[\- ]?\d){12,18}\b", 0, _luhn),
    ("PHONE",   r"(?:(?<=\s)|^)(?:\+?66|0)(?:[\- ]?\d){8,9}\b", 0, None),
    # International / US phone (needs a + prefix, parens area code, or 3-3-4 form)
    ("PHONE",   r"\+\d{1,3}[\s\-.]?\(?\d{1,4}\)?(?:[\s\-.]?\d{2,4}){2,4}", 0, None),
    ("PHONE",   r"\(\d{3}\)\s?\d{3}[\s\-.]\d{4}", 0, None),
    ("PHONE",   r"\b\d{3}[\-.]\d{3}[\-.]\d{4}\b", 0, None),
    # US Social Security Number (3-2-4); distinct from the 3-3-4 phone / Thai ID
    ("SSN",     r"\b\d{3}-\d{2}-\d{4}\b", 0, None),
    # Thai bank account in the canonical dashed form xxx-x-xxxxx-x (10 digits)…
    ("ACCOUNT", r"\b\d{3}-\d-\d{5}-\d\b", 0, None),
    # …or a bare/loose account number introduced by an account keyword (mask the
    # number, keep the label for cloud context).
    ("ACCOUNT", r"(?i)(?:เลข(?:ที่)?บัญชี|บัญชี(?:เงินฝาก)?|a/c|acct\.?|account)\s*(?:no\.?|number|เลขที่)?\s*[:#]?\s*(\d[\d\- ]{6,16}\d)", 1, None),
    # Domain identifiers introduced by a label — medical HN/AN/MRN, HR employee id,
    # legal case numbers. Masks ONLY the value after the label (which must contain
    # a digit); the lookbehind stops "loAN 1" matching inside a word.
    ("DOCID",   _DOCID_RX, 1, None),
    ("IP",      r"\b(?:(?:25[0-5]|2[0-4]\d|1?\d?\d)\.){3}(?:25[0-5]|2[0-4]\d|1?\d?\d)\b", 0, None),
    ("PATH",    r"(?:/Users/|/home/|[A-Za-z]:\\Users\\)[^/\\\s\"']+(?:[/\\][^\s\"']*)?", 0, None),
    # Court names — a regular pattern the local NER consistently skips (treats as
    # generic). Thai courts start with "ศาล"; English ones end with "Court".
    ("ORG",     "ศาล[฀-๿]{2,30}", 0, None),
    ("ORG",     r"\b(?:[A-Z][A-Za-z]+\s+){1,5}Court\b", 0, None),
]
_COMPILED = [(label, re.compile(pat), vg, val) for (label, pat, vg, val) in RULE_SPECS]

# Zero-width / BOM chars that real documents (esp. PDF-extracted) sprinkle inside
# words, plus whitespace — deny-list matching tolerates any run of these between
# the characters of a confidential term so "Project  Phoenix", "project phoenix",
# and "สำนั ก งาน" all still match the listed term.
_ZW = "\u200b\u200c\u200d\ufeff"
_DENY_SEP = "[\\s\u200b\u200c\u200d\ufeff]*"

_TOK_RE = re.compile(r"__PII_([A-Z]+)_(\d+)__")
# Tolerant restore: models occasionally mangle separators/case in the token.
_TOK_TOLERANT_RE = re.compile(r"__\s*PII\s*_\s*([A-Za-z]+)\s*_\s*(\d+)\s*__", re.I)
_JSON_ARR_RE = re.compile(r"\[.*\]", re.S)


# ── Local-model NER (contextual entities the regexes can't catch) ────────────
NER_PROMPT = (
    "Extract proper-noun PII from the TEXT. Output ONLY a JSON array and nothing "
    "else — no explanation, no reasoning, no preamble, no markdown. Tag EVERY "
    "specific named PERSON, ORGANIZATION (companies, banks, hospitals, clinics, "
    "courts, schools, universities, government agencies, consulting / advisory / "
    "law firms, partners, clients, suppliers), or internal PROJECT / CODENAME. "
    "Include a name EVEN when a role word introduces it — 'advisor', "
    "'partner', 'client', 'supplier', 'counsel', 'lawyer', 'attorney', "
    "'plaintiff', 'defendant', 'ที่ปรึกษา', 'พันธมิตร', 'ลูกค้า', 'คู่ค้า', "
    "'ทนายความ', 'ทนาย', 'โจทก์', 'จำเลย', 'ผู้ป่วย', 'แพทย์' — tag the NAME "
    "(including non-Thai/Latin names inside Thai text), never the role word "
    "itself. Each item is "
    '{"text": "<verbatim span>", "type": "person|org|project"}. Exclude generic '
    "words, plain job titles, countries, and cities. If there are none, output "
    "[]. Your reply MUST start with '['. "
    'Example — TEXT: "deal led by Jane Doe, advisor Bain, partner Acme Co, '
    'codename Project X" → [{"text":"Jane Doe","type":"person"},'
    '{"text":"Bain","type":"org"},{"text":"Acme Co","type":"org"},'
    '{"text":"Project X","type":"project"}]. TEXT:\n\n'
)


def parse_ner(reply: str) -> list[tuple[str, str]]:
    """Tolerant parse of an NER model reply → list of (span, type).

    Reasoning models emit prose *then* the JSON array at the end, so prefer the
    LAST well-formed array in the reply (objects hold no `]`, so a non-greedy
    `[...]` captures a whole array cleanly)."""
    if not reply:
        return []
    arr = None
    for cand in reversed(re.findall(r"\[.*?\]", reply, re.S)):
        try:
            parsed = json.loads(cand)
        except Exception:
            continue
        if isinstance(parsed, list):
            arr = parsed
            break
    if arr is None:
        return []
    out: list[tuple[str, str]] = []
    for it in arr:
        if not isinstance(it, dict):
            continue
        t = str(it.get("text") or it.get("span") or it.get("value") or "").strip()
        c = str(it.get("type") or it.get("category") or it.get("label") or "").strip().lower()
        if t and c:
            out.append((t, c))
    return out


_NER_TYPE_TO_LABEL = {
    "person": "PERSON", "people": "PERSON", "name": "PERSON",
    "org": "ORG", "organization": "ORG", "organisation": "ORG", "company": "ORG",
    "project": "PROJECT", "codename": "PROJECT", "product": "PROJECT",
}

# Titles/honorifics to skip when vaulting individual name parts (they're not the
# identifying token, and masking them would be noise).
_NAME_STOP = {
    "mr", "mrs", "ms", "miss", "dr", "prof", "sir", "madam", "khun",
    "นาย", "นาง", "นางสาว", "คุณ", "ดร", "ผจก", "ศ", "รศ", "ผศ",
}


class MaskVault:
    """Session-scoped, in-memory real↔token map. Consistent and reversible.

    Never persisted, never serialized to the cloud. One instance per chat
    session; call clear() (or drop the instance) when the session ends.
    """

    def __init__(self, groups: Iterable[str] = DEFAULT_GROUPS,
                 deny_list: Iterable[str] = ()):
        self.groups = {g.strip() for g in groups if g and g.strip()}
        self.deny_list = [d.strip() for d in deny_list if d and d.strip()]
        self._real2tok: dict[str, str] = {}
        self._tok2real: dict[str, str] = {}
        self._counts: dict[str, int] = {}   # label → highest index issued
        self._deny_rx_cache: dict[str, "re.Pattern | None"] = {}

    # ── config ──────────────────────────────────────────────────────────
    def _enabled_labels(self) -> set[str]:
        out: set[str] = set()
        for g in self.groups:
            out |= GROUP_LABELS.get(g, set())
        return out

    # ── deny-list matching (whitespace/zero-width/case tolerant) ────────
    def _deny_rx(self, term: str):
        """Compile a confidential term into a regex that still matches when the
        document mangles it: any case, and any run of whitespace/zero-width chars
        between characters ("Project  Phoenix", "project phoenix", "สำนั ก งาน").
        Only whitespace is allowed between chars — it can never jump over letters."""
        if term in self._deny_rx_cache:
            return self._deny_rx_cache[term]
        chars = [re.escape(c) for c in term if not c.isspace() and c not in _ZW]
        rx = re.compile(_DENY_SEP.join(chars), re.IGNORECASE) if len(chars) >= 2 else None
        self._deny_rx_cache[term] = rx
        return rx

    # ── token allocation (consistent + reversible) ─────────────────────
    def _token_for(self, real: str, label: str) -> str:
        tok = self._real2tok.get(real)
        if tok:
            return tok                       # same real value → same token, always
        n = self._counts.get(label, 0) + 1
        self._counts[label] = n
        tok = f"__PII_{label}_{n}__"
        self._real2tok[real] = tok
        self._tok2real[tok] = real
        return tok

    # ── detection ───────────────────────────────────────────────────────
    def _rule_hits(self, text: str, labels: set[str]) -> list[tuple[str, str]]:
        hits: list[tuple[str, str]] = []
        for label, rx, vg, val in _COMPILED:
            if label not in labels:
                continue
            for m in rx.finditer(text):
                value = m.group(vg) if vg else m.group(0)
                if not value:
                    continue
                if val and not val(value):
                    continue
                hits.append((value, label))
        return hits

    # ── mask ────────────────────────────────────────────────────────────
    def mask(self, text: str, *, ner_fn: Callable[[str], list] | None = None) -> str:
        """Replace sensitive spans with stable placeholders. Returns masked text.

        `ner_fn(text) -> [(span, type), ...]` is the injected local-model tagger;
        pass None to skip the contextual pass (e.g. for a system prompt).
        """
        if not text:
            return text
        labels = self._enabled_labels()
        hits: list[tuple[str, str]] = list(self._rule_hits(text, labels))

        # deny-list — confidential terms, matched tolerant of case + whitespace +
        # zero-width chars; the ACTUAL matched span (whatever spacing it has) is
        # what gets masked, so a variant never slips through to the cloud.
        if "TERM" in labels and self.deny_list:
            for term in self.deny_list:
                rx = self._deny_rx(term)
                if rx is None:
                    continue
                for mt in rx.finditer(text):
                    span = mt.group(0)
                    if span.strip():
                        hits.append((span, "TERM"))

        # contextual NER (person / org / project)
        if ner_fn and ({"PERSON", "ORG", "PROJECT"} & labels):
            try:
                for span, cat in (ner_fn(text) or []):
                    label = _NER_TYPE_TO_LABEL.get((cat or "").lower())
                    span = (span or "").strip()
                    if not (label and label in labels and len(span) >= 2):
                        continue
                    hits.append((span, label))
                    # People recur in partial form later in the same document
                    # ("notify <firstname>"), so vault each significant NAME part
                    # too — else the alias slips through to the cloud. PERSON only:
                    # org/project parts are usually generic words.
                    if label == "PERSON" and " " in span:
                        for part in span.replace(".", " ").split():
                            part = part.strip()
                            if len(part) >= 2 and part.lower() not in _NAME_STOP:
                                hits.append((part, "PERSON"))
            except Exception:
                pass   # NER is best-effort; rule layer + leak_scan still apply

        # Dedup real values; mask longest-first so a value that is a substring of
        # another isn't partially clobbered. Already-vaulted values reuse tokens.
        seen: set[str] = set()
        uniq: list[tuple[str, str]] = []
        for value, label in hits:
            if value in seen:
                continue
            seen.add(value)
            uniq.append((value, label))
        uniq.sort(key=lambda x: len(x[0]), reverse=True)

        out = text
        for value, label in uniq:
            out = out.replace(value, self._token_for(value, label))

        # Belt-and-suspenders: re-apply EVERY known vault value so a name masked
        # in an earlier turn stays masked here even if detectors missed it now.
        for value in sorted(self._real2tok, key=len, reverse=True):
            if value in out:
                out = out.replace(value, self._real2tok[value])
        return out

    # ── unmask (deterministic; never uses a model) ──────────────────────
    def unmask(self, text: str) -> str:
        if not text or not self._tok2real:
            return text
        out = text
        for tok in sorted(self._tok2real, key=len, reverse=True):
            if tok in out:
                out = out.replace(tok, self._tok2real[tok])

        # Tolerant fallback for tokens the cloud mangled (case/separators).
        def _repl(m: "re.Match") -> str:
            key = f"__PII_{m.group(1).upper()}_{m.group(2)}__"
            return self._tok2real.get(key, m.group(0))

        return _TOK_TOLERANT_RE.sub(_repl, out)

    # ── leak guard (run on the about-to-be-sent payload) ────────────────
    def leak_scan(self, text: str) -> list[str]:
        """Return leak markers found in `text`. Empty = safe to send to cloud.

        (1) any real vault value appearing verbatim, and (2) any high-risk
        structured secret detectable by ANY rule — including categories the user
        disabled — so a key can't slip out just because masking was turned off.
        """
        if not text:
            return []
        leaks: list[str] = []
        for value, tok in self._real2tok.items():
            if value in text:
                leaks.append(f"vault:{tok}")
        for label, rx, vg, val in _COMPILED:
            if label not in _LEAK_ALWAYS:
                continue
            for m in rx.finditer(text):
                value = m.group(vg) if vg else m.group(0)
                # A value that is itself a placeholder means masking already
                # happened here (e.g. `password: __PII_SECRET_1__`) — not a leak.
                if not value or _TOK_RE.fullmatch(value):
                    continue
                if not val or val(value):
                    leaks.append(f"rule:{label}")
                    break
        return leaks

    # ── introspection ──────────────────────────────────────────────────
    def stats(self) -> dict[str, int]:
        """Count per label — never exposes the real values."""
        out: dict[str, int] = {}
        for tok in self._tok2real:
            m = _TOK_RE.match(tok)
            if m:
                out[m.group(1)] = out.get(m.group(1), 0) + 1
        return out

    def mapping(self) -> list[tuple[str, str]]:
        """(token, real) pairs — ONLY for an explicit, opt-in verbose view."""
        return sorted(self._tok2real.items())

    def clear(self) -> None:
        self._real2tok.clear()
        self._tok2real.clear()
        self._counts.clear()

    def __len__(self) -> int:
        return len(self._tok2real)
