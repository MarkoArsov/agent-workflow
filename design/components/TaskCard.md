# TaskCard

A task on the board: number, agent and title. Nothing else unless something needs attention.

**Provide** the issue number, the agent avatar and the title. The column already says the stage, so the card carries no status icon. Add one `pl-card__foot` flag only when it changes what the person does next:
- `pl-flag--attention`: Question for you, Plan to approve, Ready for review.
- `pl-flag--danger`: Failed at Verify.
- plain metadata such as `PR #87` with `pl-flag--plain`.

The whole card is a button that opens the side peek; the open card gets `aria-current="true"`.

**Don't** add progress bars, labels, timestamps or more than one flag. Details belong in the peek.
