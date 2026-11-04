# RelayBox — Transactional Outbox Worker

**SQLite transactional outbox with leases, retries and dead-letter recovery.**

![Python](https://img.shields.io/badge/python-3.11%2B-3776AB)
![License](https://img.shields.io/badge/license-MIT-green)

Commit a business update and its delivery event together, then recover from worker crashes and downstream failures.

**Maintainer:** [Hamed Minaei](https://github.com/hamed665) · **Runtime:** Python 3.11+ · **Edition:** local library and CLI, v0.1.0.

The included demos and tests use only the Python standard library and synthetic data. No package installation, API key or network connection is required.

## Use case and behavior

Services that must persist business changes and delivery intent in one transaction.

| Stage | Contract |
| --- | --- |
| Write | Commit the entity update and immutable tenant/event ID together. |
| Claim | A worker obtains a bounded lease; the lease token fences stale acknowledgments. |
| Complete or retry | The host performs the external effect, then acknowledges; failures can retry or reach dead-letter state. |

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

## Walkthrough

Inspect the demo state counters, then follow the retry and dead-letter cases in the tests. A successful acknowledgment records local completion; it does not prove exactly-once execution in a downstream service.

See [the captured demo output](examples/demo-output.txt) for the bundled scenario.

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

The [behavioral tests](tests/) cover the decision rules and failure paths described above. The [CI workflow](.github/workflows/ci.yml) defines the repeatable verification matrix.
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

## Security and integration

Read [SECURITY.md](SECURITY.md) before adapting this component to application data. [Architecture notes](docs/architecture.md) explain the integration boundary. Report reproducible issues through [GitHub Issues](https://github.com/hamed665/event-outbox-worker/issues), with sanitized inputs and the command used.

## License

MIT. See [LICENSE](LICENSE). Contributions: [CONTRIBUTING.md](CONTRIBUTING.md).
