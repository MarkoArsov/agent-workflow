# StatusIcon

A 14px circle that fills as a task moves through the board. One glyph per column, so a task's stage reads at a glance without a badge.

| Kind | Glyph | Colour |
|---|---|---|
| `ready` | dashed ring | `ink-subtle` |
| `planning` | quarter | `ink-muted` |
| `building` | half | `accent` |
| `shepherding` | three quarters | `accent` |
| `review` | ring with a dot | `attention` (a person is needed) |
| `done` | filled check | `success` |
| `failed` | filled cross | `danger` |
| `paused` | ring with bars | `ink-subtle` |

**Provide** the kind; add `role="img"` and an `aria-label` when no text names the state nearby. Copy the SVG from this preview; the cut-out strokes use `--surface`.
