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
- Board: TaskCard, BoardColumn. Panels: SidePeek, Activity.
- Navigation: SidebarNav, CommandPalette. Inbox: InboxRow.
- Settings: SettingRow, SaveBar. Feedback: Toast.
- Docs: Callout, CodeBlock.
