---
description: Public configuration schemas for Stagecoach projects and task plans.
footer: reference
footer_order: 2
---

# Schema reference

These schemas describe public configuration. Runtime validation also checks repository membership, dependencies, and executable evidence.

## Project connector

Host or command transport with capabilities and per-provider headless availability. No credentials.

| Field | Required | Format |
|---|---|---|
| id | yes | string |
| enabled | no | boolean |
| transport | yes | host, command |
| command | no | object |
| capabilities | yes | array |
| providers | yes | object |
| env_refs | no | array |

## Pipeline task

An approved plan with explicit repository access, executable outcomes, ordered stages, and provider routes.

| Field | Required | Format |
|---|---|---|
| schema_version | yes | constant |
| task | yes | string |
| plan_files | yes | array |
| repositories | yes | array |
| stages | yes | array |
| checks | yes | array |
| outcomes | yes | array |
| routes | no | object |
| limits | no | object |
| delivery | no | object |
| references | no | array |
| connectors | no | array |

## Project profile



| Field | Required | Format |
|---|---|---|
| schema_version | yes | constant |
| project | yes | object |
| repositories | yes | array |
| agents | no | array |
| execution | yes | object |
| planning | yes | object |
| extensions | no | object |
| pipeline | no | object |
| tracking | no | object |
| delivery | no | object |
| environments | no | object |

## Scoped project rule

Deterministic blocking checks, advisory signals, or contextual prose. Recurrence triggers review.

| Field | Required | Format |
|---|---|---|
| id | yes | string |
| guidance | yes | string |
| enforcement | yes | blocking, advisory, prose |
| paths | no | array |
| repositories | no | array |
| command | no | object |
| forbidden_pattern | no | string |
| review_after | no | integer |

## Custom stage

A project-owned extension to the ordered pipeline. Completion still requires observed checks.

| Field | Required | Format |
|---|---|---|
| id | yes | string |
| skill | no | string |
| command | no | object |
| before | no | string |
| after | no | string |
| inputs | yes | array |
| outputs | yes | array |
| checks | yes | array |
