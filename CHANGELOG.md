# Changelog

## [main] — DAF v0.1.1 baseline

Initial research run. 30 experiments across 6 domains, run against DAF v0.1.1.

- 16 pass, 4 fail, 10 error
- See findings/ for full results per experiment
- See README.md for findings summary

### Known issues in this baseline
- HIL-001 to HIL-006: task_type 'send_email' not valid in v0.1.1 — fix in v0.1.2
- ORC-003: analyzer agent tool isolation failure — architecture fix in v0.2.0
- ORC-004: budget tracker cost wiring — fix in v0.1.2
- CST-004: loop-level budget precision — fix in v0.1.2
- REL-001: config file path error — fix in v0.1.2
