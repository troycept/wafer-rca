# How to write a discriminator

A discriminator is not exotic knowledge. It is commonality analysis, which you
have run hundreds of times. The formal question is:

> Two causes would produce the same picture. What **other** observation separates them?

There are only about six such observations in a fab. Nearly every discriminator
you will ever write is one of these six with specifics filled in.

## D1 — Tool commonality

Does the signature follow a tool, chamber, module or head?

Split affected and unaffected wafers by tool at each step. If 90% of the bad
wafers went through chamber B and the good ones did not, you are done.

> "Pattern follows tool ID across lots" — separates a tool problem from an
> incoming-material or lot problem.

## D2 — Time behaviour

Step change or gradual drift?

- **Step change** means something was changed: PM, part swap, recipe edit, new
  consumable lot. Look at the change log for that timestamp.
- **Gradual drift** means something is wearing: pad, focus ring, chamber
  seasoning, nozzle deposit.
- **Periodic** means it tracks the PM cycle. Worst just before PM, resets after.

> "Gradual onset over days, resets at ring change" — separates consumable wear
> from a discrete event.

## D3 — Fixed spatial position

Does the feature sit at the same physical place on every wafer?

Mechanical contact repeats at a fixed position: clamps, lift pins, end effector,
chuck. Process non-uniformity is rotationally symmetric or follows gas flow, and
does not care about wafer orientation.

> "Repeats at fixed theta across wafers in the lot" — separates handling damage
> from a process excursion.

**Caveat for this project:** WM-811K carries no notch orientation, so you cannot
actually compute theta from these maps. Say so in the README. It is a real
limitation and naming it is better than hoping nobody notices.

## D4 — Metrology correlation

Is there a direct measurement that turns the hypothesis into a fact?

Thickness map, CD, overlay, particle count, sheet resistance, film stress. This
is the strongest discriminator type because it stops being inference.

> "EBR width out of spec confirms it" — this is a D4, and it is why that entry
> reads as real.

## D5 — Slot and sequence position

Does it depend on where the wafer sat?

First-wafer and last-wafer effects, furnace boat position, slot-dependent
handling, batch edge effects. `waferIndex` in this dataset is exactly this, and
almost nobody uses it.

> "Only wafers 1 and 25 affected" — separates a batch thermal edge effect from
> a whole-lot problem.

## D6 — Test versus process

Did the die actually fail, or did the test say it failed?

Retest, probe card condition, contact resistance, specific bin codes, correlation
with prober or test head.

> "Retest passes" — separates a probe problem from a real defect. This one gets
> missed constantly and it belongs on every Near-full and Random entry.

---

## How to use this

For any cause you write, ask in order: **can I tell this one apart by tool (D1),
by time (D2), by position (D3), by a measurement (D4), by slot (D5), or by
retest (D6)?**

Pick the one that actually separates it from the *other causes in that same list*.
If a check would come back the same for two causes on your list, it is a check,
not a discriminator.

Tag each entry with `discriminator_type` so the benchmark can report which kinds
of reasoning a model gets right. Nobody has done that, and it is a real result.
