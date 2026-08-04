Done:

- **Dashboard templates**: start a board from a curated template instead of an empty
  grid, reusing the JSON import pipeline.

Planned next, in rough priority order:

- **Periodic KPI digest by email**: scheduled summary of a board's tiles and KPIs,
  computed with each recipient's own access rights.
- **Threshold alerts**: notify when an item's value crosses a configured limit.
- **Print-friendly board**: a print stylesheet that flattens the grid, plus a _Print_
  entry in the dashboard menu.

Under consideration, no commitment yet:

- **Cross filtering**: clicking a chart section filters the other items built on the
  same model.
- **Read-only public sharing**: token-based access to a board for people without an
  Odoo user. Needs a dedicated security review before it can be considered.
- **Value history**: optional snapshots of item values, to show trends and sparklines
  regardless of what the source model keeps.
- **Server-side data cache**: for boards refreshing every few seconds on a wall
  screen. The cache key has to include the user so access rights stay intact.
- **Narrative board summary**: a short written read of the current figures, generated
  from the same data the cards use.
