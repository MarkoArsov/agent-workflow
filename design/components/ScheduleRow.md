# ScheduleRow

One schedule in the Schedules list: on/off, name and what it does, when it runs in plain words, the last result, and the next run.

**Provide** a `pl-switch` (on/off, saved as a reviewed change), the schedule name and a one-line description, timing in words ("Weekdays at 08:00", never raw cron here), the last execution as a StatusIcon plus a short result ("Picked #160", "2 failures") and its time, and the next run (`pl-num`). Set `data-off="true"` when the schedule is off; the next-run cell then reads "Off". The row is a button that opens the schedule in the side panel; the open one gets `aria-current="true"`.

**Don't** show steps, cron expressions or costs in the row; they belong in the side panel.
