# Contributing to SABER

Welcome.

This is **SABER** — a CLI tool to benchmark Pulsar endpoint reliability.
If you wanna help out: fixes, features, docs, tests — cool. Let’s keep it tidy.

## How to contribute

1. Fork the repo

2. Clone **your** fork:

   ```bash
   git clone https://github.com/<your-username>/saber.git
   cd saber
   ```

3. Set up your environment:

   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install -e .[dev]
   ```

4. Make a branch **off `dev`**:

   ```bash
   git checkout -b <cool-feature-name> dev
   ```

5. Do the thing

## Coding style

* python ≥ 3.10
* formatter: **black**
* linter: **ruff**
* imports: sorted with **isort**
* docstrings: **Google style**

Make sure to pass the following checks:

```bash
ruff check .
ruff format .
```

## PR rules

* Always **to `dev`**, never straight to `main`
* PR from your fork → `dev`

## Example of google-style docstring

```python
def hello_world(name: str) -> str:
    """Returns a Hello World.

    Args:
        name (str): who is saying hi.

    Returns:
        str: the actual greeting.
    """
    print(f"Hello World, from {name}")
```
