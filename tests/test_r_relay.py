#!/usr/bin/env python3
"""
Privacy-relay regression tests — the mask → cloud → unmask guarantee.

Functions are EXECUTED (not source-grepped). The masking engine
(lib/thmes_mask.py) is imported directly; the bin/thmes glue
(`_ollama_chat` model override, `run_mask_pipeline`) is extracted via AST and
exec'd in a stubbed namespace so no MLX / network is needed.

The non-negotiable property under test: a real sensitive value NEVER reaches the
(mocked) cloud, and the local restore is exact.

    Rr1 : MaskVault round-trip + consistency + rule detectors
    Rr2 : leak_scan guarantee (incl. disabled-category safety net)
    Rr3 : NER injection + deny-list + tolerant unmask + parse_ner
    Rr4 : _ollama_chat(model=…) override → payload uses the override, cloud omits num_ctx
    Rr5 : run_mask_pipeline → cloud receives masked text only; final is unmasked; leak → abort

Usage:
    python3 tests/test_r_relay.py
"""
import ast
import io
import json
import os
import re
import sys
import time
import types
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "lib"))


def _find_src(repo: Path) -> Path:
    override = os.environ.get("THMES_BIN")
    if override:
        return Path(override)
    for name in ("thmes",):
        p = repo / "bin" / name
        if p.exists():
            return p
    return repo / "bin" / "thmes"


SRC = _find_src(REPO)
_source = SRC.read_text(encoding="utf-8")
_lines = _source.splitlines()
_tree = ast.parse(_source)

results: list = []


def check(name: str, ok: bool, detail: str = "") -> None:
    results.append((name, ok, detail))
    status = "PASS" if ok else "FAIL"
    print(f"  [{status}] {'  ' if ok else '! '}{name}")
    if detail and not ok:
        print(f"         → {detail}")


def _seg(name: str) -> str:
    for node in _tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == name:
            return "\n".join(_lines[node.lineno - 1: node.end_lineno])
    raise ValueError(f"{name!r} not found")


def _valid_thai_id_num() -> str:
    base = "110170020345"
    s = sum(int(base[i]) * (13 - i) for i in range(12))
    return base + str((11 - (s % 11)) % 10)


from thmes_mask import MaskVault, parse_ner, _valid_thai_id, _luhn  # noqa: E402

print("Privacy relay — mask → cloud → unmask")
print("=" * 60)

# ── Rr1: MaskVault round-trip, consistency, rule detectors ───────────────────
print("\nRr1: MaskVault round-trip + detectors")
THAI = _valid_thai_id_num()
v = MaskVault()
ner = lambda t: [("Falcon", "project"), ("Acme Corp", "company"), ("John Smith", "person")]
src = (f"mail john@acme.co / jane@acme.co tel 0812345678 ip 10.2.3.4 "
       f"key sk-ABCDEFGHIJKLMNOPQRSTUVWX path /home/alice/.secret id {THAI} "
       f"password: hunter2xyz project Falcon at Acme Corp by John Smith")
masked = v.mask(src, ner_fn=ner)

check("Rr1-1 round-trip restores exactly", v.unmask(masked) == src,
      f"got {v.unmask(masked)!r}")
REALS = ["john@acme.co", "jane@acme.co", "0812345678", "10.2.3.4",
         "sk-ABCDEFGHIJKLMNOPQRSTUVWX", "/home/alice/.secret", THAI,
         "hunter2xyz", "Falcon", "Acme Corp", "John Smith"]
leaked = [r for r in REALS if r in masked]
check("Rr1-2 NO real value in masked payload", not leaked, f"leaked: {leaked}")
check("Rr1-3 two distinct emails → two tokens",
      v.stats().get("EMAIL") == 2, f"stats={v.stats()}")
check("Rr1-4 secret value masked, key name kept",
      "password:" in masked and "hunter2xyz" not in masked, masked)
check("Rr1-5 Thai-ID checksum valid / rejects junk",
      _valid_thai_id(THAI) and not _valid_thai_id("1234567890123"))
check("Rr1-6 Luhn validates card / rejects junk",
      _luhn("4111111111111111") and not _luhn("4111111111111112"))
# Fix C — bank account numbers (Thai dashed form + keyword-introduced), and a
# plain monetary total stays untouched (utility: money isn't PII)
va = MaskVault()
ma1 = va.mask("ชำระเข้าบัญชี 879-7-71898-6 ธนาคารกรุงเทพ วงเงิน 5,000,000 บาท", ner_fn=lambda t: [])
ma2 = va.mask("remit to account no. 567-8-90123-4 at KBank", ner_fn=lambda t: [])
check("Rr1-6b bank account masked, money figure preserved",
      "879-7-71898-6" not in ma1 and "5,000,000" in ma1 and "567-8-90123-4" not in ma2, f"{ma1} || {ma2}")
# Fix D — labeled domain IDs (medical HN/AN, HR employee id, legal case no.) masked,
# but a digit run with NO id-label (a loan amount) is left alone
vd2 = MaskVault()
md_id = vd2.mask("ผู้ป่วย HN 67-70-767 AN 6649756; Staff ID EMP-00231; Case No. 1188/2024; approved a loan 50000", ner_fn=lambda t: [])
check("Rr1-6c labeled IDs masked (HN/AN/EMP/case), unlabeled number kept",
      all(x not in md_id for x in ["67-70-767", "6649756", "EMP-00231", "1188/2024"])
      and "50000" in md_id and vd2.unmask(md_id).count("__PII_") == 0, md_id)
# Fix F — court names (Thai "ศาล…" / English "… Court"), no false positive on "court"
vc = MaskVault()
mc1 = vc.mask("ยื่นต่อ ศาลแพ่งกรุงเทพใต้ วันนี้", ner_fn=lambda t: [])
mc2 = vc.mask("filed at Bangkok South Civil Court today", ner_fn=lambda t: [])
mc3 = vc.mask("she went to court, of course", ner_fn=lambda t: [])
check("Rr1-6d court names masked (TH+EN), generic 'court' untouched",
      "ศาลแพ่งกรุงเทพใต้" not in mc1 and "Bangkok South Civil Court" not in mc2
      and mc3 == "she went to court, of course", f"{mc1} || {mc2} || {mc3}")
# Fix H — international/US phone + US SSN, without firing on dates/versions
vi = MaskVault()
mi = vi.mask("call +1 415-555-0182 / office (212) 555-7788 / SSN 123-45-6789 / "
             "released 2024-01-15 v1.2.3", ner_fn=lambda t: [])
check("Rr1-6e US/intl phone + SSN masked; date/version untouched",
      all(x not in mi for x in ["+1 415-555-0182", "(212) 555-7788", "123-45-6789"])
      and "2024-01-15" in mi and "1.2.3" in mi and vi.unmask(mi).count("__PII_") == 0, mi)

# consistency across turns: same real value → same token
m2 = v.mask("again john@acme.co", ner_fn=lambda t: [])
tok_email1 = v._real2tok["john@acme.co"]
check("Rr1-7 consistent token reuse across turns", tok_email1 in m2, m2)

# belt-and-suspenders: previously-vaulted name masked even if NER misses it now
m3 = v.mask("ping John Smith again", ner_fn=lambda t: [])
check("Rr1-8 known entity masked even without NER", "John Smith" not in m3, m3)

# sub-word vaulting: a person referred to later by first name only must NOT leak
vsw = MaskVault()
m_sw = vsw.mask("John Carter signed off; later please notify John about it",
                ner_fn=lambda t: [("John Carter", "person")])
check("Rr1-9 partial first-name masked (sub-word person vaulting)",
      "John" not in m_sw and vsw.unmask(m_sw) ==
      "John Carter signed off; later please notify John about it", m_sw)

# ── Rr2: leak_scan guarantee (defence-in-depth) ──────────────────────────────
print("\nRr2: leak_scan guarantee")
check("Rr2-1 masked payload is leak-free", v.leak_scan(masked) == [], v.leak_scan(masked))
check("Rr2-2 raw payload trips many leaks", len(v.leak_scan(src)) >= 6, str(v.leak_scan(src)))

# safety net: even with the `secret` group OFF, a key must still trip leak_scan
v_off = MaskVault(groups=["email"])
m_off = v_off.mask("token: sk-ABCDEFGHIJKLMNOPQRSTUVWX")
check("Rr2-3 secret group OFF → key NOT masked", "sk-ABCDEFGHIJKLMNOPQRSTUVWX" in m_off, m_off)
check("Rr2-4 …but leak_scan still catches it (net)",
      any("APIKEY" in l for l in v_off.leak_scan(m_off)), str(v_off.leak_scan(m_off)))

# ── Rr3: NER + deny-list + tolerant unmask + parse_ner ───────────────────────
print("\nRr3: NER + deny-list + tolerance")
vd = MaskVault(deny_list=["Project Phoenix", "InternalCorp"])
md = vd.mask("ship Project Phoenix for InternalCorp next week", ner_fn=lambda t: [])
check("Rr3-1 deny-list terms masked",
      "Project Phoenix" not in md and "InternalCorp" not in md, md)
check("Rr3-2 deny-list round-trip", vd.unmask(md) == "ship Project Phoenix for InternalCorp next week")
# Fix A — deny-list matching tolerates case / double-space / zero-width variants
# (the forms PDF-extracted or sloppily-typed confidential docs actually contain)
vv = MaskVault(deny_list=["Project Phoenix", "Falcon Initiative"])
variants = ["push Project  Phoenix now", "ship project phoenix", "Falcon​Initiative go"]
masked_v = [vv.mask(s, ner_fn=lambda t: []) for s in variants]
check("Rr3-2b deny-list catches case/space/zero-width variants",
      all("__PII_TERM" in mk for mk in masked_v)
      and all(vv.unmask(mk) == s for mk, s in zip(masked_v, variants)),
      str(masked_v))
check("Rr3-3 tolerant unmask (mangled case)",
      v.unmask("see __pii_email_1__ end") == "see john@acme.co end",
      v.unmask("see __pii_email_1__ end"))
check("Rr3-4 parse_ner tolerant of key aliases",
      parse_ner('x [{"text":"Bob","type":"person"},{"span":"X","category":"org"}] y')
      == [("Bob", "person"), ("X", "org")])
check("Rr3-5 NER bad reply → []", parse_ner("no json here") == [])
# reasoning models emit prose THEN the JSON array — must grab the last valid one
_reasoned = ('Here is my thinking: the text mentions [some brackets] and an '
             'example {"text": "x"}. Final answer:\n'
             '[{"text": "Falcon", "type": "project"}, {"text": "Acme", "type": "org"}]')
check("Rr3-6 parse_ner survives a reasoning preamble + distractor [...]",
      parse_ner(_reasoned) == [("Falcon", "project"), ("Acme", "org")],
      str(parse_ner(_reasoned)))
check("Rr3-7 empty array reply → []", parse_ner("blah\n[]") == [])

# ── Rr4: _ollama_chat(model=…) override ──────────────────────────────────────
print("\nRr4: _ollama_chat model override")
_sent: dict = {}


class _Req:
    def __init__(self, url, data=None, headers=None, method=None):
        _sent["payload"] = json.loads(data.decode()) if data else None


class _Resp(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *a):
        self.close()


def _urlopen(req, timeout=None):
    chunk = json.dumps({"message": {"content": "pong"}, "done": True,
                        "eval_count": 1, "eval_duration": 1_000_000}).encode()
    return _Resp(chunk + b"\n")


class _HTTPErr(Exception):
    pass


ons: dict = {
    "json": json, "time": time,
    "Request": _Req, "urlopen": _urlopen,
    "OLLAMA_HOST": "http://x", "_ollama_headers": lambda: {},
    "OLLAMA_TIMEOUT": 5.0, "OLLAMA_LOAD_TIMEOUT": 10.0,
    "_OLLAMA_NUM_CTX_OVERRIDE": 0, "_OLLAMA_DEFAULT_CTX": 16384,
    "_native_tool_calls_to_text": lambda tcs: "",
    "HTTPError": _HTTPErr,
    "console": type("C", (), {"print": staticmethod(lambda *a, **k: None)})(),
    "mm": types.SimpleNamespace(ollama_meta={"model": "gemma4:e4b", "ctx": 8192}),
}
exec(compile(_seg("_is_cloud_model"), str(SRC), "exec"), ons)
exec(compile(_seg("_ollama_chat"), str(SRC), "exec"), ons)
_ollama_chat = ons["_ollama_chat"]

txt, _st = _ollama_chat([{"role": "user", "content": "hi"}], "", 1, model="glm-4.6:cloud")
check("Rr4-1 payload uses the OVERRIDE model (not mm)",
      _sent["payload"]["model"] == "glm-4.6:cloud", str(_sent.get("payload")))
check("Rr4-2 cloud path omits num_ctx",
      "num_ctx" not in _sent["payload"].get("options", {}), str(_sent["payload"].get("options")))
check("Rr4-3 returns the streamed content", txt == "pong", repr(txt))

# default (no override) → falls back to mm's loaded model
_sent.clear()
_ollama_chat([{"role": "user", "content": "hi"}], "", 1)
check("Rr4-4 no override → uses mm.ollama_meta model",
      _sent["payload"]["model"] == "gemma4:e4b", str(_sent.get("payload")))

# ── Rr5: run_mask_pipeline — cloud sees masked only; final unmasked; leak abort ─
print("\nRr5: run_mask_pipeline")
_captured: dict = {}


def _fake_generate_reply(history, system, max_tokens=512, model=None, tools=None,
                         temperature=None, think=None):
    _captured["think"] = think
    _captured["history"] = history
    _captured["system"] = system
    _captured["model"] = model
    blob = system + " " + " ".join(h.get("content", "") for h in history)
    toks = re.findall(r"__PII_[A-Z]+_\d+__", blob)
    return (f"In reply, the address {toks[0] if toks else 'n/a'} was noted.",
            {"tokens": 9})


pns: dict = {
    "generate_reply": _fake_generate_reply,
    "_RELAY_SYS": "SYSTEM: placeholders are __PII_LABEL_N__.",
    "_relay_gather_files": lambda *a, **k: [],   # no file I/O in unit tests
}
exec(compile(_seg("run_mask_pipeline"), str(SRC), "exec"), pns)
run_mask_pipeline = pns["run_mask_pipeline"]

vp = MaskVault()
hist = [{"role": "user", "content": "summarize mail from john@acme.co about ip 10.9.9.9"}]
final, meta = run_mask_pipeline(hist, cloud_model="glm-4.6:cloud", vault=vp,
                                max_tokens=256, ner_fn=lambda t: [])
sent_blob = _captured["system"] + " " + " ".join(h["content"] for h in _captured["history"])
check("Rr5-1 cloud got the override model", _captured["model"] == "glm-4.6:cloud", _captured.get("model"))
check("Rr5-2 cloud payload contains NO real value",
      "john@acme.co" not in sent_blob and "10.9.9.9" not in sent_blob, sent_blob)
check("Rr5-3 cloud payload IS masked (has placeholders)", "__PII_" in sent_blob, sent_blob)
check("Rr5-4 final answer is UNMASKED (real value restored)",
      final is not None and "john@acme.co" in final, repr(final))
check("Rr5-4b cloud REASON call sets think=False (no CoT dump)",
      _captured.get("think") is False, str(_captured.get("think")))

# leak abort: secret present but `secret` group OFF → leak_scan blocks the send
_captured.clear()
vleak = MaskVault(groups=["email"])
hist2 = [{"role": "user", "content": "deploy with token: sk-ABCDEFGHIJKLMNOPQRSTUVWX now"}]
final2, meta2 = run_mask_pipeline(hist2, cloud_model="glm-4.6:cloud", vault=vleak,
                                  max_tokens=256, ner_fn=lambda t: [])
check("Rr5-5 leak detected → pipeline aborts (None)", final2 is None and meta2.get("aborted") == "leak",
      str(meta2))
check("Rr5-6 leak abort → cloud NEVER called", "model" not in _captured, str(_captured))

# cloud failure → abort (None) so caller can fall back to local
_captured.clear()


def _boom_gen(history, system, max_tokens=512, model=None, tools=None,
              temperature=None, think=None):
    _captured["called"] = True
    return ("[ollama error] HTTP 500", {"tokens": 0})


pns["generate_reply"] = _boom_gen
exec(compile(_seg("run_mask_pipeline"), str(SRC), "exec"), pns)
final3, meta3 = pns["run_mask_pipeline"]([{"role": "user", "content": "hi there"}],
                                         cloud_model="glm-4.6:cloud", vault=MaskVault(),
                                         max_tokens=64, ner_fn=lambda t: [])
check("Rr5-7 cloud error → abort with aborted=cloud", final3 is None and meta3.get("aborted") == "cloud",
      str(meta3))

# ── Rr6: agentic relay — cloud=brain, local=hands; tool args unmasked, results re-masked ─
print("\nRr6: run_relay_agent_loop (agentic)")

# Extract the three real functions under test into one shared namespace.
gns: dict = {
    "json": json,
    "TOOLS": {"write_file": {"params": {}, "desc": "write"}},
    "_RELAY_SYS": "SYS:",
    "_RELAY_TOOLS_SYS": " You may call tools.",
    "_RELAY_NER_RESULT_TOOLS": {"read_file", "grep", "list_dir", "web_fetch", "web_search"},
    "_relay_gather_files": lambda *a, **k: [],          # no file I/O in unit tests
    "_relay_ner": lambda t: [],                          # NER best-effort; stub to []
    "_ollama_tools_schema": lambda on: [{"type": "function",
                                         "function": {"name": "write_file"}}],
    "_call_fingerprint": lambda call: call.get("name", "") + "|" + json.dumps(
        call.get("arguments", {}), sort_keys=True, ensure_ascii=False),
}

# Scripted cloud: round 1 → emit a write_file call referencing the EMAIL placeholder
# (the cloud only ever saw the masked token); round 2 → plain final answer.
EMAILTOK = "__PII_EMAIL_1__"   # first (only) email → deterministic index 1
WRITE_CALL = {"name": "write_file",
              "arguments": {"path": "/tmp/relay_agent_out.txt",
                            "content": f"please email {EMAILTOK}"}}
_relay_sent: list = []
_pending_calls: list = []
_pairs = iter([
    ("(writing the file now)", [WRITE_CALL]),
    (f"Done — emailed {EMAILTOK}.", []),
])


def _agent_cloud(history, system, max_tokens=512, model=None, tools=None,
                 temperature=None, think=None):
    _relay_sent.append({"system": system, "model": model, "tools": tools,
                        "think": think, "history": [dict(h) for h in history]})
    try:
        text, calls = next(_pairs)
    except StopIteration:
        text, calls = "done", []
    _pending_calls[:] = calls
    return text, {"tokens": 7}


def _agent_parse(reply, known_tools=None):
    return list(_pending_calls), {}


_executed: list = []


def _agent_execute(call, allow_dangerous, pre_approved=False):
    # Records the call it RECEIVED (must be unmasked → real values) and returns a
    # result that itself carries a NEW sensitive value, to prove re-masking.
    _executed.append({"name": call.get("name"),
                      "arguments": dict(call.get("arguments", {}))})
    return "wrote 2 lines; file owner jane@acme.co", True


gns.update({
    "generate_reply": _agent_cloud,
    "parse_tool_calls": _agent_parse,
    "execute_tool": _agent_execute,
})
for _fn in ("_relay_unmask_args", "_relay_mask_result", "run_relay_agent_loop"):
    exec(compile(_seg(_fn), str(SRC), "exec"), gns)
run_relay_agent_loop = gns["run_relay_agent_loop"]

vault6 = MaskVault()
hist6 = [{"role": "user", "content": "email the summary to john@acme.co"}]
final6, meta6 = run_relay_agent_loop(
    hist6, cloud_model="glm-4.6:cloud", vault=vault6,
    tools_on={"write_file": {}}, allow_dangerous=set(),
    max_tokens=256, ner_fn=lambda t: [], max_iters=6)

round0 = _relay_sent[0]["system"] + " " + " ".join(
    h["content"] for h in _relay_sent[0]["history"])
check("Rr6-1 round-1 cloud payload has NO real value",
      "john@acme.co" not in round0, round0)
check("Rr6-2 round-1 cloud payload IS masked (placeholder present)",
      EMAILTOK in round0, round0)
check("Rr6-3 native tool schema + think=False sent to cloud",
      _relay_sent[0]["tools"] is not None and _relay_sent[0]["think"] is False,
      str(_relay_sent[0].get("think")))
check("Rr6-4 tool EXECUTED locally with UNMASKED real args",
      _executed and _executed[0]["arguments"].get("content") == "please email john@acme.co",
      str(_executed))
# The tool result (carrying jane@acme.co) is fed back to the cloud on round 2 — it
# must be re-masked: a NEW placeholder for jane, never her raw address.
round1 = " ".join(h["content"] for h in _relay_sent[1]["history"])
check("Rr6-5 tool result re-masked before returning to cloud (no raw value)",
      "jane@acme.co" not in round1 and "__PII_EMAIL_" in round1, round1)
check("Rr6-6 final answer UNMASKED for the user", final6 == "Done — emailed john@acme.co.",
      repr(final6))
check("Rr6-7 meta counts: 1 tool call across 2 iters",
      meta6.get("tool_calls") == 1 and meta6.get("iters") == 2, str(meta6))

# _relay_unmask_args restores placeholders nested in lists/dicts
_relay_unmask_args = gns["_relay_unmask_args"]
vua = MaskVault()
_m = vua.mask("ping 10.0.0.7 / mail a@b.co")        # seeds IP + EMAIL tokens
iptok = next(t for t, r in vua.mapping() if r == "10.0.0.7")
args_in = {"cmd": f"curl {iptok}", "hosts": [iptok], "meta": {"to": EMAILTOK}}
# EMAILTOK here maps to a@b.co only if it is index 1 in THIS vault — make it so:
emailtok2 = next(t for t, r in vua.mapping() if r == "a@b.co")
args_in["meta"]["to"] = emailtok2
out_args = _relay_unmask_args(args_in, vua)
check("Rr6-8 _relay_unmask_args restores nested placeholders",
      out_args["cmd"] == "curl 10.0.0.7" and out_args["hosts"] == ["10.0.0.7"]
      and out_args["meta"]["to"] == "a@b.co", str(out_args))

# _relay_mask_result redacts when an unmaskable secret survives (group disabled but
# leak_scan ALWAYS checks high-risk labels → defence in depth)
_relay_mask_result = gns["_relay_mask_result"]
vred = MaskVault(groups=["person"])               # email/secret/net OFF
safe_r, was_red = _relay_mask_result(
    "deploy key sk-ABCDEFGHIJKLMNOPQRSTUVWX now", vred, run_ner=False)
check("Rr6-9 unmaskable secret in tool result → REDACTED (not sent)",
      was_red and "sk-ABCDEFGHIJKLMNOPQRSTUVWX" not in safe_r, repr(safe_r))
safe_ok, red_ok = _relay_mask_result("all clean here, nothing sensitive", vred, run_ner=False)
check("Rr6-10 clean tool result passes through un-redacted",
      not red_ok and "clean" in safe_ok, repr(safe_ok))

# Rr6-11: an empty cloud turn mid-chain (small-model stall) must NUDGE, not abort —
# regression for the bug where the loop treated "" as a cloud failure and bailed.
_stall_sent: list = []
_stall_seq = iter([("", []), ("All done — no tool needed.", [])])


def _stall_cloud(history, system, max_tokens=512, model=None, tools=None,
                 temperature=None, think=None):
    _stall_sent.append([dict(h) for h in history])
    try:
        text, calls = next(_stall_seq)
    except StopIteration:
        text, calls = "fallback", []
    _pending_calls[:] = calls
    return text, {"tokens": 3}


gns["generate_reply"] = _stall_cloud      # loop resolves generate_reply from gns at call-time
vault_s = MaskVault()
final_s, meta_s = run_relay_agent_loop(
    [{"role": "user", "content": "hello there"}],
    cloud_model="glm-4.6:cloud", vault=vault_s,
    tools_on={"write_file": {}}, allow_dangerous=set(),
    max_tokens=64, ner_fn=lambda t: [], max_iters=5)
check("Rr6-11 empty stall → nudged + continued, NOT aborted",
      final_s == "All done — no tool needed." and meta_s.get("aborted") is None,
      f"final={final_s!r} meta={meta_s}")
check("Rr6-12 a (continue) nudge was injected after the stall",
      any("(continue)" in h.get("content", "")
          for hist in _stall_sent for h in hist), str(_stall_sent[-1]))

# ── Rr7: self-heal — verify → LOCAL triage → re-ask cloud ────────────────────
print("\nRr7: run_relay_selfheal (verify + triage loop)")
import subprocess as _sub

hns = {"subprocess": _sub}
exec(compile(_seg("_relay_run_verify"), str(SRC), "exec"), hns)
_relay_run_verify = hns["_relay_run_verify"]
ok_pass, out_pass = _relay_run_verify("python3 -c \"print('VOK')\"")
ok_fail, out_fail = _relay_run_verify(
    "python3 -c \"import sys; sys.stderr.write('boom'); sys.exit(1)\"")
check("Rr7-1 verify passes on exit 0 + captures stdout", ok_pass and "VOK" in out_pass, repr(out_pass))
check("Rr7-2 verify fails on non-zero + captures stderr", (not ok_fail) and "boom" in out_fail, repr(out_fail))

hp_ns = {}
exec(compile(_seg("_relay_heal_prompt"), str(SRC), "exec"), hp_ns)
hp = hp_ns["_relay_heal_prompt"]("TypeError: boom", "remove the path arg")
check("Rr7-3 heal prompt carries raw error + diagnosis-as-hint",
      "TypeError: boom" in hp and "remove the path arg" in hp and "HINT" in hp.upper(), hp[:140])

# full loop: attempt 1 fails verify → triage → attempt 2 passes
_attempts_hist = []
def _fake_loop(history, **kw):
    _attempts_hist.append([dict(h) for h in history])
    return (f"answer-v{len(_attempts_hist)}", {"tool_calls": 1, "iters": 2})
_vseq = iter([(False, "AssertionError: x"), (True, "VERIFY PASS")])
sh_ns = {
    "run_relay_agent_loop": _fake_loop,
    "_relay_run_verify": lambda cmd, timeout=90: next(_vseq),
    "_relay_triage": lambda raw: "use float() not int()",
    "_relay_heal_prompt": hp_ns["_relay_heal_prompt"],
}
exec(compile(_seg("run_relay_selfheal"), str(SRC), "exec"), sh_ns)
fin, meta = sh_ns["run_relay_selfheal"](
    [{"role": "user", "content": "build it"}], cloud_model="x", vault=MaskVault(),
    tools_on={"write_file": {}}, allow_dangerous=set(), max_tokens=64,
    ner_fn=lambda t: [], verify_cmd="pytest", heal_attempts=3)
check("Rr7-4 heals → returns the FIXED attempt's answer", fin == "answer-v2", repr(fin))
check("Rr7-5 meta records attempt=2 + verify_ok", meta.get("attempt") == 2 and meta.get("verify_ok") is True, str(meta))
check("Rr7-6 attempt-2 history carries error + local diagnosis (heal turn)",
      len(_attempts_hist) == 2
      and any("AssertionError" in h.get("content", "") for h in _attempts_hist[1])
      and any("float()" in h.get("content", "") for h in _attempts_hist[1]), str(_attempts_hist[-1])[-200:])

# verify passes first try → single attempt, no triage
_attempts_hist.clear()
sh_ns["_relay_run_verify"] = lambda cmd, timeout=90: (True, "VERIFY PASS")
exec(compile(_seg("run_relay_selfheal"), str(SRC), "exec"), sh_ns)
fin2, meta2 = sh_ns["run_relay_selfheal"](
    [{"role": "user", "content": "build"}], cloud_model="x", vault=MaskVault(),
    tools_on={"write_file": {}}, allow_dangerous=set(), max_tokens=64,
    ner_fn=lambda t: [], verify_cmd="pytest", heal_attempts=3)
check("Rr7-7 verify passes first try → single attempt", meta2.get("attempt") == 1 and meta2.get("verify_ok") is True, str(meta2))

# ── Summary ──────────────────────────────────────────────────────────────────
print("\n" + "=" * 60)
passed = sum(1 for _, ok, _ in results if ok)
total = len(results)
print(f"Total: {total}  PASS: {passed}  FAIL: {total - passed}")
print("=" * 60)
sys.exit(0 if passed == total else 1)
