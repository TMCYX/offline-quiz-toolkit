# Offline Quiz Toolkit

Turn a set of study notes into a **single-file, offline, phone-first multiple-choice
quiz**. One HTML file, no server, no network — open it in a mobile browser and study
anywhere.

Typical flow: you keep per-week question banks as JSON, `build_quiz.py` validates and
embeds them into `quiz-template.html`, and you get one self-contained `.html` you can
carry on your phone.

```
week1.json ┐
week2.json ├─► build_quiz.py ─► quiz.html   (single file, offline, PWA-less)
week3.json ┘      (validate + base64 embed + round-trip verify)
```

## Files

| File | Purpose |
|---|---|
| `quiz-template.html` | The quiz engine: a single offline HTML with a `__QUIZ_DATA__` placeholder. Contains all CSS/JS inline (zero external requests). |
| `build_quiz.py` | Validates every `week*.json`, merges them in week order, embeds the bank as a **base64 ASCII** payload (safe against encoding corruption), and round-trip verifies the output. |
| `README.md` | This file. |

## How the quiz behaves

- Stores a bank of questions; each play **draws 10 at random** (distinct).
- Shuffles answer options per question (Fisher–Yates) and remaps the correct index.
- On a wrong answer it highlights the correct option (light green) and shows a
  bilingual explanation (English + traditional Chinese).
- Rob/robust: falls back gracefully if the pool is small; filters malformed entries;
  shows a specific load error if something is wrong; includes a `<noscript>` banner.

## Question bank schema

Create a folder with one file per week: `week1.json`, `week2.json`, …

```json
[
  {
    "id": "w1-01",
    "week": 1,
    "topic": "Topic name",
    "question": "English question?",
    "options": ["First", "Second", "Third", "Fourth"],
    "answer": 0,
    "explanation_en": "Why the correct answer is correct (2-4 sentences; do not mention option letters).",
    "explanation_zh": "2-4 句繁體中文解釋（不要提選項字母）。"
  }
]
```

Rules enforced by `build_quiz.py`:

- exactly 4 non-empty `options`; `answer` is an integer `0`–`3`;
- unique `id`s and unique question text (across all weeks);
- no `</script>` or `<!--` substrings (safety);
- explanations should **not** reference option letters (options are shuffled at runtime).

## Usage

1. Put your banks in a folder, e.g. `quiz-data/week1.json`, `quiz-data/week2.json`, …
2. Build:

```bash
python build_quiz.py --data-dir quiz-data --out quiz.html
# optional second copy (e.g. a synced folder):
python build_quiz.py --data-dir quiz-data --out quiz.html --copy-to /path/quiz.html
```

3. Open `quiz.html` in a browser (best on a phone). To edit questions, change the
   JSON and rebuild — **don't edit the HTML**, the bank is embedded as base64.

## Phone notes

- Open the file with a real browser (Safari / Chrome). In-app previewers that strip
  `<script>` won't run the quiz — a `<noscript>` banner will tell you.
- If you sync the file via a cloud folder, make sure you open the latest copy.

## Requirements

- Python 3.8+ (standard library only).

## License

MIT — see [LICENSE](LICENSE).
