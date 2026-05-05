# logsnap

> Lightweight log aggregator that tails multiple files and filters by pattern in real time.

---

## Installation

```bash
pip install logsnap
```

Or install from source:

```bash
git clone https://github.com/youruser/logsnap.git && cd logsnap && pip install .
```

---

## Usage

Tail multiple log files and filter output by a regex pattern:

```bash
logsnap --files /var/log/app.log /var/log/nginx/access.log --pattern "ERROR|WARN"
```

Use it as a Python library:

```python
from logsnap import LogSnap

snap = LogSnap(
    files=["/var/log/app.log", "/var/log/nginx/access.log"],
    pattern="ERROR|WARN"
)

snap.start()
```

### Options

| Flag | Description |
|------|-------------|
| `--files` | One or more log file paths to tail |
| `--pattern` | Regex pattern to filter log lines |
| `--interval` | Polling interval in seconds (default: `0.5`) |
| `--no-color` | Disable colorized output |

---

## Requirements

- Python 3.8+

---

## License

This project is licensed under the [MIT License](LICENSE).