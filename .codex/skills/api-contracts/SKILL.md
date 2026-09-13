---
name: api-contracts
description: "Coordinate HealthSphere API schema, metric semantics and producer-consumer compatibility changes."
---

# Api Contracts

Read the active approved ticket and relevant repository instructions first. This skill does not expand authorization.

- [Contracts](../../../docs/api/CONTRACTS.md)

## Workflow

Identify producer, consumers and current contract revision before changing fields. Resolve units, timestamps, omitted/null behavior, errors, authentication and provenance with owners. Keep unresolved choices visibly proposed; obtain the required ticket decision before implementation. Update fixtures/contract tests, producer and consumers in a compatible sequence. Check absent/ineligible/unavailable AI results and Agent safety states are not turned into fabricated success. Record linked PRs and the compatibility/rollout evidence.
