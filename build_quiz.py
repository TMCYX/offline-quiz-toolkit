"""build_quiz.py -- Assemble an offline quiz HTML from per-week question banks.

Part of the workflow documented in [[wiki/references/offline-quiz-html-workflow]]:

  1. Load + validate every week*.json in --data-dir (schema + safety checks).
  2. Merge all questions in week-number order.
  3. Embed the merged bank as base64 (pure ASCII) into quiz-template.html,
     replacing the __QUIZ_DATA__ placeholder.
  4. Round-trip verify the written output (decode the base64 back, count questions).

Usage (run from your vault / workspace root):

  python "wiki/references/offline-quiz-toolkit/build_quiz.py" \
    --data-dir "wiki/projects/academic/ENG4001-Revision/eng4001-quiz-data" \
    --out "wiki/projects/academic/ENG4001-Revision/eng4001-quiz.html"
    [--copy-to "<second output path, e.g. a second location>\\eng4001-quiz.html"]

Options:
  --data-dir   Folder containing week1.json, week2.json, ... (required)
  --out        Output HTML path (required)
  --template   Template HTML (default: quiz-template.html next to this script)
  --copy-to    Optional second output path (e.g. a second location)
"""
import base64
import json
import os
import re
import sys

FORBIDDEN = ("</script>", "<!--")


def validate(data, week):
    errs, warnings = [], []
    if not isinstance(data, list):
        return [f"week{week}: top-level JSON is not a list"], warnings
    if not data:
        errs.append(f"week{week}: no questions")
    seen = set()
    spread = {}
    for i, q in enumerate(data):
        tag = (q.get("id") if isinstance(q, dict) else None) or f"week{week}#{i}"
        if not isinstance(q, dict):
            errs.append(f"{tag}: not an object")
            continue
        for k in ("id", "week", "topic", "question", "options", "answer", "explanation_en", "explanation_zh"):
            if k not in q:
                errs.append(f"{tag}: missing key '{k}'")
        if q.get("id") in seen:
            errs.append(f"{tag}: duplicate id")
        seen.add(q.get("id"))
        opts = q.get("options")
        if not isinstance(opts, list) or len(opts) != 4:
            errs.append(f"{tag}: options must be a list of exactly 4")
        else:
            for j, o in enumerate(opts):
                if not isinstance(o, str) or not o.strip():
                    errs.append(f"{tag}: empty option at index {j}")
        a = q.get("answer")
        if not isinstance(a, int) or isinstance(a, bool) or not (0 <= a <= 3):
            errs.append(f"{tag}: answer must be an integer 0-3, got {a!r}")
        else:
            spread[a] = spread.get(a, 0) + 1
        for k in ("question", "explanation_en", "explanation_zh", "topic", "id"):
            v = q.get(k)
            if not isinstance(v, str) or not v.strip():
                errs.append(f"{tag}: '{k}' is empty or not a string")
        blob = json.dumps(q, ensure_ascii=False).lower()
        for bad in FORBIDDEN:
            if bad in blob:
                errs.append(f"{tag}: contains forbidden substring {bad!r}")
        expl = str(q.get("explanation_en", "")) + " " + str(q.get("explanation_zh", ""))
        if re.search(r"option\s*[abcd]\b|\bchoice\s*[abcd]\b|\([abcd]\)", expl, re.IGNORECASE):
            warnings.append(f"{tag}: explanation may reference option letters")
    print(f"week{week}: {len(data)} items, answer-index spread: {dict(sorted(spread.items()))}")
    return errs, warnings


def load_weeks(data_dir):
    names = [f for f in os.listdir(data_dir) if re.fullmatch(r"week\d+\.json", f, re.IGNORECASE)]
    if not names:
        sys.exit(f"ERROR: no week*.json files found in {data_dir}")
    names.sort(key=lambda f: int(re.search(r"\d+", f).group(0)))
    merged, errs, warnings = [], [], []
    for name in names:
        week = int(re.search(r"\d+", name).group(0))
        with open(os.path.join(data_dir, name), encoding="utf-8") as f:
            data = json.load(f)
        e, w = validate(data, week)
        errs += e
        warnings += w
        if isinstance(data, list):
            for q in data:
                if isinstance(q, dict):
                    q["week"] = week
            merged.extend(data)
    seen = {}
    for q in merged:
        key = " ".join(str(q.get("question", "")).lower().split())
        if key in seen:
            errs.append(f"duplicate question text: {q.get('id')} vs {seen[key]}")
        else:
            seen[key] = q.get("id")
    return merged, errs, warnings


def parse_args(argv):
    args = {}
    i = 0
    while i < len(argv):
        key = argv[i]
        if key.startswith("--") and i + 1 < len(argv):
            args[key] = argv[i + 1]
            i += 2
        else:
            sys.exit(f"ERROR: unexpected argument {key!r}")
    return args


def main():
    args = parse_args(sys.argv[1:])
    data_dir = args.get("--data-dir")
    out_path = args.get("--out")
    if not data_dir or not os.path.isdir(data_dir):
        sys.exit("ERROR: --data-dir <folder with week*.json> is required")
    if not out_path:
        sys.exit("ERROR: --out <output.html> is required")
    template = args.get("--template") or os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "quiz-template.html"
    )

    merged, errs, warnings = load_weeks(data_dir)
    for w in warnings:
        print("WARNING:", w)
    if errs:
        print("VALIDATION ERRORS:")
        for e in errs:
            print("  -", e)
        sys.exit(1)
    print(f"OK: {len(merged)} questions validated, no duplicates")

    if not os.path.exists(template):
        sys.exit(f"ERROR: template not found: {template}")
    with open(template, encoding="utf-8") as f:
        html = f.read()
    count = html.count("__QUIZ_DATA__")
    if count != 1:
        sys.exit(f"ERROR: template placeholder count = {count}, expected 1")

    payload_json = json.dumps(merged, ensure_ascii=False, separators=(",", ":"))
    assert "</script>" not in payload_json.lower() and "<!--" not in payload_json.lower(), "payload unsafe"
    payload = base64.b64encode(payload_json.encode("utf-8")).decode("ascii")
    assert "<" not in payload and ">" not in payload and "&" not in payload, "b64 payload unsafe"
    html = html.replace("__QUIZ_DATA__", payload)

    out_dir = os.path.dirname(os.path.abspath(out_path))
    os.makedirs(out_dir, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"WROTE {out_path} ({os.path.getsize(out_path)} bytes)")

    written = open(out_path, encoding="utf-8").read()
    m = re.search(r'<script id="quiz-data" type="application/json">([A-Za-z0-9+/=]+)</script>', written)
    assert m, "data block not found in output"
    decoded = json.loads(base64.b64decode(m.group(1)).decode("utf-8"))
    assert len(decoded) == len(merged), f"round-trip got {len(decoded)} vs {len(merged)}"
    print(f"ROUND-TRIP OK: {len(decoded)} questions embedded as base64 ASCII payload")

    copy_to = args.get("--copy-to")
    if copy_to:
        with open(copy_to, "w", encoding="utf-8") as f:
            f.write(html)
        print(f"COPIED {copy_to} ({os.path.getsize(copy_to)} bytes)")


if __name__ == "__main__":
    main()
