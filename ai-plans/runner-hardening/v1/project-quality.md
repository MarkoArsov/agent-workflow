# Frozen project quality sources

These are the existing applicable native standards at specification time. Their
repository-relative paths are named below; originals retain authority. No new
project extension or unrelated installed workflow is introduced. The package
quality-guidance.md is separately selected in pipeline references.


## AGENTS.md

# plovi

This repository is a standalone public package. PLAN.md defines the approved scope.
Work in this checkout; do not route package development through an installed personal workflow.
Keep skills generic and resolve project behavior from its profile and extensions.
Use Python 3.11+ and the standard library for installation and runtime.
Run: python3 -m unittest discover -s tests -v
Documentation: python3 -m mkdocs build --strict
Never modify real user agent configuration during tests. Use isolated child environments.
Keep private identifiers, real credentials, and machine-specific paths out of deliverables.
Commit logical changes locally. Publishing and remote changes require an explicit request.

<!-- plovi:start -->
Read PROJECT_WORKFLOW.md for this project's workflow defaults and custom skills.
Do not apply workflow defaults from an unrelated ancestor project.
<!-- plovi:end -->
Design: anything people see (app, docs site, brand) follows design/README.md and design/DESIGN.md; use only tokens from design/tokens.json.


## PROJECT_WORKFLOW.md

<!-- plovi:start -->
# Project workflow

- agent-workflow: .; library, docs; current-checkout; participate when-changed.

Plans: ai-plans/<task>/.
Harness: Codex only.
Execution: trusted. Tracker: github.
Project skills, rules, and connectors live under .plovi/.
Resolve this project's profile before using workflow defaults. Native instructions and explicit user requests take precedence.
<!-- plovi:end -->


## design/README.md

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
| `screens/app/` | App screens: board with side panel (`Main`), schedules, inbox, settings, take over, Ask palette, empty and error states, phone, sidebar. |
| `screens/docs/` | Documentation site: home, guide page, CLI reference. |
| `screens/brand/` | The brand sheet. |

## Screens

The `*.dc.html` files are exported from the design canvas they were drawn in. Each is an HTML page plus a small `class Component` script with the sample data and interactions; the markup inside `<x-dc>` is ordinary HTML using the classes in `components.css`. They need the canvas runtime to render, so treat them as reference source: copy the structure, classes and copy, not the runtime.

- `Main.dc.html` is the board. It also defines the side panel for every task state (question, plan, breakdown, running, failed, review, with you), the Ask palette and toasts. `TakeOver` and `Palette` reuse it with a different starting state.
- `Sidebar.dc.html` is shared by every app screen.
- `Schedules.dc.html` is the Schedules tab: the list, the selected schedule with its steps and recent runs, Run now, and the New schedule dialog that starts from a plain-language description.

## Rules for agents

- Use tokens by name. Never introduce a colour, size or font that is not in `tokens.json`; add a token first if one is missing.
- `attention` (amber) is the only colour that asks a person to act. `accent` (sea) marks work in motion. Neither is a button fill.
- Cards and rows carry an ID, a title and at most one flag. Details go in the side panel.
- Write copy as the voice section of `DESIGN.md` says: lowercase "plovi", short active sentences, no emoji.
- When you change a token or component, update `tokens.json` or `components.css`, its guideline, and its preview together.

Documentation shells use `docs-header-height`, `docs-shell-width` and
`docs-home-width`; the values match the existing docs reference screens.


## design/DESIGN.md

# plovi design system

plovi is a software factory for a solo developer or a small team. It picks up GitHub issues, runs coding agents on them in isolated worktrees, shepherds the pull requests, and stops whenever a person needs to decide. The name is Macedonian for "sails"; the mark is a sailboat.

The interface is a quiet tool in the tradition of Linear, Vercel and GitHub: neutral surfaces, one accent, type doing the hierarchy, details on demand. Dark is the primary theme; light is a full equal.

## Principles

1. **Calm by default.** A screen shows the work, not the machinery. No badges, progress bars or counters unless they change what the person does next.
2. **Amber means you.** `attention` is the only colour that asks for action. Scan a screen for amber and you have found everything that needs you.
3. **Details on demand.** Cards and rows carry a number, a title and at most one flag. Everything else lives in the side peek, opened with a click and closed with Esc.
4. **Content first, chrome last.** One sidebar, one header line per view, no toolbars full of buttons. Secondary actions go in the `more` menu.
5. **Keyboard first.** Every action is reachable from the command palette (⌘K). Arrow keys move between cards; Enter opens; Esc closes.
6. **One review for every change.** Settings changed from the app, the CLI or the palette all pass the same Review and save step.

## Voice

- Write the name in lowercase everywhere, including at the start of a sentence: "plovi opened PR #87".
- Name things by what people recognise: task, plan, review, pull request. Keep internal names (ledger, tick, slot) out of the app.
- Short, active sentences. A button says what happens ("Approve plan"); the toast repeats it ("Plan approved").
- Say who acts: "You merge." "plovi marks PRs ready when checks pass."
- Errors say what went wrong and the fix: "GitHub rejected the push: the branch needs a review. Ask a reviewer or switch autonomy to Mark ready."
- Real numbers: "2 tests failed", "3/4 running", "2h".
- No emoji, no exclamation marks, no "magic" or "seamless".
- Work that changes how people use plovi ends with a "What changes for your workflow" callout.

## Colour

- Window: `bg` behind the sidebar and around the content panel. Content: `surface`, inset 8px with `radius-xl` and a `border` edge. Cards: `surface-raised` with `border` and `shadow-card`.
- Text: `ink` primary, `ink-muted` secondary, `ink-subtle` for numbers, times and placeholders.
- One primary button per view in `primary` / `on-primary`.
- `accent` (sea) marks work in motion: Building and Shepherding icons, the open card's edge, links, focus. Never a fill for buttons or large areas.
- `attention` (amber): needs a person. `danger`: failed. `success`: done. Each always sits next to its icon or a word.

## Type

- Geist for all text, Geist Mono for issue and PR numbers, counts, times and code. Both are variable fonts in `fonts/` (SIL Open Font License).
- The app runs at 13px (`body`, `body-strong`); metadata at 12px (`small`). Titles in the side peek and inbox use `title`; settings groups use `heading`.
- Docs prose is `body-lg` at `docs-measure`; page titles `display`; the landing hero `display-xl`.
- Sentence case everywhere. Uppercase only for the rare `label`.

## Layout

- App: sidebar (`sidebar-width`) on `bg`, content panel to its right. Each view has a single `header-height` header holding breadcrumbs on the left and at most two ghost actions on the right.
- Board: six columns of `column-width`, 16px apart, scrolling sideways inside the panel. Columns have no background.
- Side peek: pinned to the right edge of the content panel at `peek-width`, full height, over the board, never below it. Full width under 720px.
- Inbox: a list on the left (360px) and the selected decision on the right.
- Schedules: a list of ScheduleRows; the selected schedule opens in the side panel with its steps, guard and executions. "New schedule" opens a dialog that starts with a plain-language box ("every weekday at 8, run test-on-staging") and falls back to a form.
- Settings: one centred column, 640px, settings grouped in bordered lists; a SaveBar floats at the bottom when something changed.
- Spacing: `space-2` between cards, `space-3` inside cards, `space-4` around the board, `space-6` inside the peek.

## Shape, depth and motion

- Radii: `radius-md` controls and rows, `radius-lg` cards and groups, `radius-xl` the content panel, palette and dialogs.
- Only floating layers cast real shadows: `shadow-peek` for the side peek, `shadow-pop` for the palette, menus and toasts.
- Motion: 120 ms colour changes; the peek slides in over 180 ms ease-out and out over 140 ms; the palette fades and scales from 98%. Under `prefers-reduced-motion`, nothing moves.

## Iconography

- Lucide (lucide.dev, ISC licence) at 16px, 1.75 stroke, in `currentColor`.
- Stage glyphs are plovi's own StatusIcon set at 14px: a circle that fills as a task moves from Ready to Done. Copy them from the StatusIcon preview.
- Agents are initials in an Avatar, never vendor logos. No emoji.

## Logo

- Use the sailboat mark from `brand/` as supplied. Never redraw, rotate or recolour it outside the provided files.
- `-light` files (white ink) on dark grounds, `-dark` files (`#18181b`) on light grounds; `plovi-mark-sea` on light grounds where the brand colour should show.
- The lockup is the mark plus the lowercase wordmark in Geist SemiBold. In the app, use the mark alone in the project switcher; use the lockup in docs headers.
- Clear space around the mark: half its height.

## Components

Plain HTML and CSS: load `tokens.css`, then `components.css`, and use the `pl-` classes shown in each `components/<Name>.html` preview. There is no JavaScript bundle; the app rebuilds these in its own framework with the same class names and tokens.

- Actions: Button. Status: StatusIcon, Avatar.
- Board: TaskCard (with a `pl-tag` naming the schedule that started it), BoardColumn. Panels: SidePeek, Activity.
- Schedules: ScheduleRow; the selected schedule opens in the SidePeek.
- Navigation: SidebarNav, CommandPalette. Inbox: InboxRow.
- Settings: SettingRow, SaveBar. Feedback: Toast.
- Docs: Callout, CodeBlock.


## design/tokens.json

{
  "name": "plovi",
  "version": 2,
  "color": {
    "themes": [
      {"id": "dark", "name": "Dark"},
      {"id": "light", "name": "Light"}
    ],
    "tokens": [
      {"name": "bg", "value": {"dark": "#0e0f11", "light": "#f4f4f5"}, "usage": "Window ground: behind the sidebar and around the inset content panel. Docs page background in dark."},
      {"name": "surface", "value": {"dark": "#141518", "light": "#ffffff"}, "usage": "The inset content panel that holds every view, the side peek, dialogs. Docs page background in light."},
      {"name": "surface-raised", "value": {"dark": "#1a1b1f", "light": "#ffffff"}, "usage": "Task cards and menus. In light, cards separate from `surface` by `border`, not by shade."},
      {"name": "surface-sunken", "value": {"dark": "#0b0c0e", "light": "#f6f6f7"}, "usage": "Inputs and code blocks."},
      {"name": "surface-hover", "value": {"dark": "#1f2024", "light": "#f0f0f2"}, "usage": "Hover and selected fill for nav items, list rows and ghost buttons."},
      {"name": "border", "value": {"dark": "#222327", "light": "#e7e7ea"}, "usage": "1px hairlines: panel edge, card edge, row dividers. Decorative only."},
      {"name": "border-strong", "value": {"dark": "#2c2e33", "light": "#d9d9de"}, "usage": "Card hover edge, secondary button edge."},
      {"name": "border-control", "value": {"dark": "#686b73", "light": "#8d8d96"}, "usage": "Edges of inputs, selects, checkboxes, radios and switches. At least 3:1 on `surface`, `surface-raised` and `surface-sunken`."},
      {"name": "ink", "value": {"dark": "#ececee", "light": "#17171a"}, "usage": "Primary text and icons on every surface token."},
      {"name": "ink-muted", "value": {"dark": "#9b9da4", "light": "#54545c"}, "usage": "Secondary text: descriptions, property labels, inactive nav. Legible on every surface token."},
      {"name": "ink-subtle", "value": {"dark": "#85878f", "light": "#6a6a73"}, "usage": "Tertiary text: IDs, timestamps, counts, placeholders. 4.5:1 on every surface token."},
      {"name": "primary", "value": {"dark": "#f2f2f3", "light": "#17171a"}, "usage": "Fill of the one primary button in a view: white in dark, near-black in light."},
      {"name": "primary-hover", "value": {"dark": "#ffffff", "light": "#2c2c31"}, "usage": "Primary button hover."},
      {"name": "on-primary", "value": {"dark": "#0e0f11", "light": "#fafafa"}, "usage": "Text on `primary`."},
      {"name": "accent", "value": {"dark": "#5ab4d6", "light": "#0b6a8a"}, "usage": "Sea. Work in motion: Building and Shepherding status icons, links, focus ring, the selected card edge. Never a button fill. Text-safe on every surface."},
      {"name": "accent-soft", "value": {"dark": "#5ab4d61f", "light": "#0b6a8a14"}, "usage": "Selected docs nav item; the faint fill behind a selected task card."},
      {"name": "on-accent", "value": {"dark": "#06202a", "light": "#ffffff"}, "usage": "Text on a solid `accent` fill (switch knob, sea app icon)."},
      {"name": "focus-ring", "value": {"dark": "{accent}", "light": "{accent}"}, "usage": "Keyboard focus: 2px solid ring, 2px offset."},
      {"name": "attention", "value": {"dark": "#e5ac45", "light": "#8a5700"}, "usage": "Needs you: a question, a plan to approve, a review. The In review status icon and the 'Needs you' flag. The only colour that asks a person to act."},
      {"name": "danger", "value": {"dark": "#ef7a5c", "light": "#b4361c"}, "usage": "Failed or cancelled status icon, error text, the Cancel task menu item."},
      {"name": "danger-soft", "value": {"dark": "#ef7a5c1a", "light": "#b4361c12"}, "usage": "Fill behind an error banner."},
      {"name": "success", "value": {"dark": "#6dc48d", "light": "#1d7a40"}, "usage": "Done status icon and passing checks. Always with its icon; never told apart from `danger` by hue alone."},
      {"name": "overlay", "value": {"dark": "#00000099", "light": "#17171a40"}, "usage": "Scrim behind the command palette and dialogs."}
    ]
  },
  "type": {
    "fonts": [
      {"family": "Geist", "file": "fonts/Geist-Variable.woff2", "weight": "100 900", "style": "normal"},
      {"family": "Geist Mono", "file": "fonts/GeistMono-Variable.woff2", "weight": "100 900", "style": "normal"}
    ],
    "families": {
      "sans": "\"Geist\", ui-sans-serif, system-ui, -apple-system, \"Segoe UI\", sans-serif",
      "mono": "\"Geist Mono\", ui-monospace, \"SF Mono\", Menlo, Consolas, monospace"
    },
    "groups": [
      {"name": "Display", "family": "sans", "styles": [
        {"name": "display-xl", "fontSize": "56px", "lineHeight": "60px", "fontWeight": 600, "letterSpacing": "-0.035em", "sample": "Hand off the work.", "usage": "Docs landing hero only."},
        {"name": "display", "fontSize": "36px", "lineHeight": "42px", "fontWeight": 600, "letterSpacing": "-0.03em", "sample": "Your first task", "usage": "Docs page titles."},
        {"name": "title", "fontSize": "20px", "lineHeight": "28px", "fontWeight": 600, "letterSpacing": "-0.015em", "sample": "Add retry to the GitHub sync", "usage": "The task title in the side peek; the inbox detail title; docs h2."},
        {"name": "heading", "fontSize": "15px", "lineHeight": "22px", "fontWeight": 600, "letterSpacing": "-0.005em", "sample": "Limits", "usage": "Settings group titles, the page title in the panel header area when one is shown."}
      ]},
      {"name": "Text", "family": "sans", "styles": [
        {"name": "body-lg", "fontSize": "16px", "lineHeight": "26px", "fontWeight": 400, "sample": "plovi runs each task in its own worktree and stops when it needs you.", "usage": "Docs prose and lead text."},
        {"name": "body", "fontSize": "13px", "lineHeight": "20px", "fontWeight": 400, "sample": "Checks green, comments handled. Waiting for a person.", "usage": "Default app text."},
        {"name": "body-strong", "fontSize": "13px", "lineHeight": "20px", "fontWeight": 500, "sample": "Add retry to the GitHub sync", "usage": "Card titles, nav labels, button labels, list row titles."},
        {"name": "small", "fontSize": "12px", "lineHeight": "16px", "fontWeight": 400, "sample": "agent-workflow · 2 h", "usage": "Metadata, helper text, activity timestamps."},
        {"name": "label", "fontSize": "11px", "lineHeight": "14px", "fontWeight": 500, "letterSpacing": "0.04em", "sample": "ACTIVITY", "usage": "Rare uppercase section labels inside the side peek. Set uppercase with CSS."}
      ]},
      {"name": "Mono", "family": "mono", "styles": [
        {"name": "mono", "fontSize": "13px", "lineHeight": "20px", "fontWeight": 400, "sample": "plovi take-over 153", "usage": "Commands and code in docs."},
        {"name": "mono-sm", "fontSize": "12px", "lineHeight": "16px", "fontWeight": 400, "sample": "#146 · PR #87 · 3/4", "usage": "Issue numbers, PR numbers, counts and keyboard hints. Tabular."}
      ]}
    ]
  },
  "spacing": {
    "tokens": [
      {"name": "space-1", "value": "4px", "usage": "Icon to label."},
      {"name": "space-2", "value": "8px", "usage": "Gap between cards, between buttons, inside chips."},
      {"name": "space-3", "value": "12px", "usage": "Card padding, list row padding."},
      {"name": "space-4", "value": "16px", "usage": "Panel header padding, board padding."},
      {"name": "space-6", "value": "24px", "usage": "Side peek padding, gap between peek sections."},
      {"name": "space-8", "value": "32px", "usage": "Gap between settings groups."},
      {"name": "space-12", "value": "48px", "usage": "Docs section spacing."},
      {"name": "space-16", "value": "64px", "usage": "Docs landing bands."}
    ]
  },
  "radius": {
    "tokens": [
      {"name": "radius-sm", "value": "4px", "usage": "Keyboard hints, checkboxes."},
      {"name": "radius-md", "value": "6px", "usage": "Buttons, inputs, nav items, list rows."},
      {"name": "radius-lg", "value": "8px", "usage": "Task cards, menus, code blocks, settings groups."},
      {"name": "radius-xl", "value": "12px", "usage": "The inset content panel, the command palette, dialogs."},
      {"name": "radius-full", "value": "9999px", "usage": "Avatars, status dots, switches."}
    ]
  },
  "shadow": {
    "note": "Flat by default. Only layers that float over content cast a shadow.",
    "tokens": [
      {"name": "shadow-card", "value": {"dark": "0 1px 0 rgba(0,0,0,0.25)", "light": "0 1px 2px rgba(23,23,26,0.06)"}, "usage": "Task cards: just enough to lift them off the panel."},
      {"name": "shadow-peek", "value": {"dark": "-16px 0 48px rgba(0,0,0,0.45)", "light": "-16px 0 48px rgba(23,23,26,0.10)"}, "usage": "The side peek, cast to its left over the board."},
      {"name": "shadow-pop", "value": {"dark": "0 16px 48px rgba(0,0,0,0.55), 0 0 0 1px rgba(255,255,255,0.06)", "light": "0 16px 48px rgba(23,23,26,0.14), 0 0 0 1px rgba(23,23,26,0.06)"}, "usage": "Command palette, menus, dialogs, toasts."}
    ]
  },
  "size": {
    "note": "Fixed dimensions the layout depends on.",
    "tokens": [
      {"name": "control-sm", "value": "26px", "usage": "Icon buttons in headers, small buttons in rows."},
      {"name": "control-md", "value": "30px", "usage": "Default button, input and select height."},
      {"name": "control-lg", "value": "38px", "usage": "Docs CTAs; minimum touch target on phones is 44px regardless."},
      {"name": "sidebar-width", "value": "232px", "usage": "App sidebar."},
      {"name": "header-height", "value": "44px", "usage": "Content panel header."},
      {"name": "column-width", "value": "280px", "usage": "Board column."},
      {"name": "peek-width", "value": "520px", "usage": "Side peek on desktop; full width below 720px."},
      {"name": "docs-measure", "value": "680px", "usage": "Docs content column."},
      {"name": "docs-header-height", "value": "60px", "usage": "Documentation header."},
      {"name": "docs-shell-width", "value": "1280px", "usage": "Documentation navigation and content shell."},
      {"name": "docs-home-width", "value": "1120px", "usage": "Documentation landing content and static product preview."}
    ]
  }
}
