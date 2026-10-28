# BoardColumn

A column per stage, in order: Ready, Planning, Building, Shepherding, In review, Done. No background well and no description: the StatusIcon and name are the header, the count follows.

Stage definitions live in a tooltip on the column name and in the docs:
- Ready: approved, waiting for a slot or a dependency.
- Planning: specifying or waiting on your answer or plan approval.
- Building: plan approved, agent working, no PR yet.
- Shepherding: PR open, checks or comments being handled.
- In review: checks green, waiting for a person.
- Done: merged.

Cards are never dragged; state comes from the factory.
