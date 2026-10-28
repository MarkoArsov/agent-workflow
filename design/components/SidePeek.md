# SidePeek

Task details open in a panel pinned to the right edge of the content panel, over the board, the way Linear and GitHub Projects open an issue. The board stays where it is behind it.

**Structure**
- Bar (`pl-peek__bar`, `header-height`): StatusIcon, number, stage on the left; icon buttons on the right: Take over, More, Close.
- Body: title (`title` style) and one-line summary; a property list (`pl-props`: Stage, Agent, Pull request, Branch, Progress); at most one decision card (`pl-ask-card`) when the task needs you; then Activity.
- Width `peek-width`, full width under 720px. `shadow-peek` falls to the left over the board.

**Behaviour** opens on card click, swaps when another card is clicked, closes with Esc or the close button. Up/down arrows step through cards in the column.
**Don't** push or reflow the board, open it below the board, or add a second scroll area inside it.
