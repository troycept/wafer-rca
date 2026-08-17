# Week 1 notes — looking at the data

## Dataset as landed

Source: MIR Lab mirror, `WM811K.pkl` (not the Kaggle `LSWMD.pkl`; same data,
cleaner schema — `failureType` is a plain string, `trainTestLabel` spelled right).

- 811,457 wafers total, **172,950 labeled (21.3%)**
- `none` is 85.2% of the labeled set
- Splits are by `lotName` across 10,762 lots: 120,726 train / 17,043 val / 35,181 test

Class counts:

| label | n | % of labeled |
|---|---:|---:|
| none | 147,431 | 85.2 |
| Edge-Ring | 9,680 | 5.6 |
| Edge-Loc | 5,189 | 3.0 |
| Center | 4,294 | 2.5 |
| Loc | 3,593 | 2.1 |
| Scratch | 1,193 | 0.7 |
| Random | 866 | 0.5 |
| Donut | 555 | 0.3 |
| Near-full | 149 | 0.09 |

Near-full has **20 wafers in test**. Any accuracy figure quoted for that class is
noise. Say so rather than reporting it as if it means something.

## Finding 1: map dimensions are a product fingerprint, and they leak

Map size is not continuous. It clusters into discrete product families — 25x27,
26x26, 30x34, 29x26, 27x25, 39x37, 33x29, 42x44 — because die size sets the grid.
The top 8 families are 54% of the labeled data.

Class mix is wildly different per family:

| family | Center % | defect rate % |
|---|---:|---:|
| **25x27** | **12.0** | 15.4 |
| 39x37 | 1.7 | 10.0 |
| 26x26 | 0.6 | 6.1 |
| 30x34 | 0.5 | 5.7 |
| 29x26 | 0.4 | 4.7 |
| 27x25 | 0.2 | 2.4 |
| 33x29 | 0.2 | 4.9 |
| 42x44 | 0.0 | 2.5 |

One product family carries **12% Center** while the rest sit at 0.0–1.7%. That is
a 20x+ enrichment.

Why it matters: a CNN fed resized maps still sees the aspect ratio and the die
grid texture. It can learn "this is the 25x27 product, guess Center" and score
well without ever learning what a center pattern looks like. The lot-level split
does not protect against this, because product family spans lots.

To check in week 2: train on all families, evaluate per family, and separately
train on one family and test on a held-out family. If cross-family performance
collapses, the headline number was product identity, not physics.

Physically this is not surprising — center-clustered failure tracks with process
sensitivity that scales with die size and layout. But it means the benchmark is
measuring something other than what it claims.

## Finding 2: aspect ratio spans 0.32 to 5.00

Sizes run 15x3 to 212x204. Median aspect is 1.00, but the tails are extreme.
A 15x3 map has no spatial signal worth classifying.

Round wafers appear as ellipses in die-index space because die are rectangular.
Resizing to a square 64x64 changes that geometry by a different amount for every
product, so "resize to 64x64" is not the neutral preprocessing step it looks like.

## Your turn — the session the plan says not to skip

Open `reports/figures/class_*.png` and write below:

- Which two classes would *you* confuse, and why:
- Does the defect sit at a fixed angular position or does it rotate wafer to wafer:
- How many of the 100 look mislabeled to you (per class):
- Anything in `none` that should not be there:
- What does the 107x150 family look like versus the small families:
