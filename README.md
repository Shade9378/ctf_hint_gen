# ctf_hint_gen

## Development setup

Create and activate a virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Install the project in editable mode:

```bash
pip install -e .
```

## Running the fake model smoke test

From the repository root:

```bash
python tests/llm_sys.py
```
