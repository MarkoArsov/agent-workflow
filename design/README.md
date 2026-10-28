# Design

The design language for plovi: the app, the documentation site and the brand. Read this folder before building or changing anything people see.

## Start here

1. [`DESIGN.md`](DESIGN.md): principles, voice, colour, type, layout, motion, iconography and logo rules.
2. [`tokens.css`](tokens.css): every colour, size, radius, shadow and font as CSS custom properties. Dark is the default; set `data-theme="light"` on any element for the light theme.
3. [`components.css`](components.css) and [`components/`](components/): each component has a guideline (`<Name>.md`) and a static preview (`<Name>.html`) you can open in a browser.
4. [`screens/`](screens/): the reference screens.

## Folder map

| Path | What |
| --- | --- |
| `DESIGN.md` | The brand book and usage rules. |
| `tokens.json` | Source of truth for tokens (colour per theme, type scale, spacing, radius, shadow, size). |
| `tokens.css` | Tokens compiled to CSS variables and type-style classes. Generated from `tokens.json`; keep them in sync. |
| `components.css` | The `pl-` component classes. Uses tokens only; declares no values of its own. |
| `components/` | Guideline and preview per component. |
| `brand/` | Logo mark, wordmark, lockups, app icons and the social card. `source-sailboat.svg` is the original mark. |
| `fonts/` | Geist and Geist Mono variable fonts, with their licence (SIL Open Font License 1.1). |
| `screens/app/` | App screens: board with side panel (`Main`), inbox, settings, take over, Ask palette, empty and error states, phone, sidebar. |
| `screens/docs/` | Documentation site: home, guide page, CLI reference. |
| `screens/brand/` | The brand sheet. |

## Screens

The `*.dc.html` files are exported from the design canvas they were drawn in. Each is an HTML page plus a small `class Component` script with the sample data and interactions; the markup inside `<x-dc>` is ordinary HTML using the classes in `components.css`. They need the canvas runtime to render, so treat them as reference source: copy the structure, classes and copy, not the runtime.

- `Main.dc.html` is the board. It also defines the side panel for every task state (question, plan, breakdown, running, failed, review, with you), the Ask palette and toasts. `TakeOver` and `Palette` reuse it with a different starting state.
- `Sidebar.dc.html` is shared by every app screen.

## Rules for agents

- Use tokens by name. Never introduce a colour, size or font that is not in `tokens.json`; add a token first if one is missing.
- `attention` (amber) is the only colour that asks a person to act. `accent` (sea) marks work in motion. Neither is a button fill.
- Cards and rows carry an ID, a title and at most one flag. Details go in the side panel.
- Write copy as the voice section of `DESIGN.md` says: lowercase "plovi", short active sentences, no emoji.
- When you change a token or component, update `tokens.json` or `components.css`, its guideline, and its preview together.
