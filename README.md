# RelayBox

**SQLite transactional outbox with leases, retries and dead-letter recovery.**

![Python](https://img.shields.io/badge/python-3.11%2B-3776AB)
![License](https://img.shields.io/badge/license-MIT-green)

Commit a business update and its delivery event together, then recover from worker crashes and downstream failures.

An original, runnable reference implementation by Hamed Minaei. Uses only the
Python standard library. No API key, paid account or network access is needed
for the included demos and tests. Version 0.1.0 focuses on the core engineering
contract rather than a hosted production service.

## Capabilities

- Atomic entity update and outbox insertion
- Tenant-scoped immutable event IDs
- Lease tokens fence stale acknowledgments
- Bounded exponential retry scheduling and dead-letter state
- Manual dead-letter requeue and grouped state counters

## Quick start

```bash
git clone https://github.com/hamed665/event-outbox-worker.git
cd event-outbox-worker
python --version  # Python 3.11+
python -m relaybox
python -m unittest discover -s tests -v
```

Optional library installation: `python -m pip install .`

## Use as a library

```python
from relaybox.core import Outbox
q = Outbox("outbox.db")
q.write("demo", "event-1", "order-1", {"status":"paid"}, now=0)
job = q.claim(now=1)
if job: q.finish(job, now=2)
q.close()
```

## Data flow

Business write + event transaction → fenced worker lease → external handler → acknowledgment

See [relaybox/core.py](relaybox/core.py) for the implementation and [architecture notes](docs/architecture.md)
for transaction boundaries and deployment considerations.

## Verification

The test suite exercises behavioral guarantees, error paths and isolation.
SQLite projects also test competing connections with independent workers.
GitHub Actions runs the suite on Python 3.11, 3.12 and 3.13.
All fixtures are synthetic. Demo output is captured in
[examples/demo-output.txt](examples/demo-output.txt).

## Scope and limitations

At-least-once processing, never exactly-once delivery. A crash after an external side effect may deliver the same event again: consumers must deduplicate by tenant/event ID. No HTTP delivery adapter, broker or daemon is included. Time is injected for deterministic tests; use a consistent trusted clock. Database access is trusted and not an authorization boundary.

## Repository map

- `relaybox/`: importable library and runnable CLI demo
- `tests/`: regression and invariant tests
- `examples/`: synthetic inputs and captured demo output
- `docs/`: design decisions and boundaries
- `.github/workflows/ci.yml`: repeatable verification

## License

MIT. See [LICENSE](LICENSE). Contributions: [CONTRIBUTING.md](CONTRIBUTING.md).
