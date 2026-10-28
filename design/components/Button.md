# Button

Runs one action, named by the verb the person sees happen.

- `pl-btn--primary`: the one action that moves the work forward in a view or panel (Approve plan, Send answer, Save). At most one visible at a time.
- default: secondary actions next to a primary.
- `pl-btn--ghost`: toolbar and header actions; `pl-btn--icon` for icon-only, always with an `aria-label`.
- `pl-btn--danger` text only, and only inside a menu or confirmation. Never a red fill.
- Sizes: `pl-btn--sm` (`control-sm`) in headers and rows, default (`control-md`), `pl-btn--lg` (`control-lg`) in docs.

**Don't** line up more than two buttons. Put the rest in the `more` menu.
