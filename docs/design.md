# Design direction

This document guides planned implementation. It is not a description of an already shipped runtime.

## Boundaries

Skills select and describe a bounded operation. Helpers perform deterministic execution or data handling. The host provides authentication, tool availability and model delegation. The parent agent retains responsibility for ambiguous requirements and substantive reasoning.

A single exact query usually needs a direct tool call. Related operations may share one worker when that reduces repeated context or coordination. The decision must account for the worker's setup, input, output and retry cost.

## Results and evidence

T01 establishes a versioned result contract. It should distinguish completed, failed, partial, blocked and uncertain results, and retain identifiers, exit codes and evidence paths where relevant.

Shortened output should preserve actionable failures, counts and a way to retrieve the original artifact. If a projection omits data, say so. Unknown formats should degrade transparently to bounded excerpts rather than invented summaries.

## Portability and configuration

Use explicit working directories, argument arrays and predictable encodings. Keep runtime dependencies small. Handle spaces, Unicode paths, missing executables and unavailable credentials without assuming the maintainer's environment.

Model and reasoning defaults belong to documented configuration or the invocation contract supported by the host. UI metadata is not a runtime model-switching API. Do not alter the parent's configuration to simulate delegation.

## Remote operations

Carry the exact target and authorized action into a worker. Only one actor should write to a given submission at a time. Read back remote state and reconcile uncertain outcomes before repeating a write. Escalation returns evidence and a question or blocker; it does not grant broader permissions.

## Evaluation

Use [measurement.md](measurement.md) to evaluate output reduction, recorded usage and task success separately. Examples and fixtures must be synthetic or properly anonymized.
