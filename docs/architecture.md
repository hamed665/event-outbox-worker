# Design notes — RelayBox

## Contract

Commit a business update and its delivery event together, then recover from worker crashes and downstream failures.

## Execution path

Business write + event transaction → fenced worker lease → external handler → acknowledgment

## Design choices

1. Atomic entity update and outbox insertion.
2. Tenant-scoped immutable event IDs.
3. Lease tokens fence stale acknowledgments.
4. Bounded exponential retry scheduling and dead-letter state.
5. Manual dead-letter requeue and grouped state counters.

## Integration boundary

At-least-once processing, never exactly-once delivery. A crash after an external side effect may deliver the same event again: consumers must deduplicate by tenant/event ID. No HTTP delivery adapter, broker or daemon is included. Time is injected for deterministic tests; use a consistent trusted clock. Database access is trusted and not an authorization boundary.

## Failure handling

Validation errors are explicit exceptions. SQLite mutations use bound SQL
parameters; multi-step mutations commit together or roll back. Library results
are data structures suitable for an adapter layer. No network calls or secrets
are embedded in the examples.

## Before deployment

Choose an authenticated adapter, add structured operational logging without raw
customer data, define backup and retention requirements, and test realistic
workloads. The local tests establish specific invariants; they do not establish
production throughput, external integration compatibility or service availability.
