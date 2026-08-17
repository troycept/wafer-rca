# Ten reference cases

Real wafers from WM-811K. Figure: `reports/figures/reference_cases.png`.
Row lookup: `kb/reference_cases.csv` (`row_in_labeled_raw` indexes `labeled_raw.pkl`).

## Read this before you use anything below

The cause lists here are **scaffolding, not the knowledge base**. They are the
generic textbook answer, which is exactly the thing I told you a model produces
fluently and slightly wrong. The split is:

- **`mechanism` and `step`** are safe. Radial non-uniformity does come from spin
  coat, bake plate and plasma density. That is in May & Spanos and everyone knows it.
- **`check`, `discriminator` and `signature`** are where generic knowledge dies.
  They need real numbers, real log names, real tool behaviour, and the ordering
  a person uses when they are standing at the terminal at 2am. Below they are
  either vague or blank on purpose.

Every entry is `confidence: uncertain` until you have gone through it. The
project's value is the delta between this file and what you replace it with.

---

## C01 — Center, 25x27, 25.4% fail

Dense failing cluster at wafer center, plus scattered failures elsewhere.

| # | mechanism | step | check | discriminator |
|---|---|---|---|---|
| 1 | CMP over-polish / dishing at center | CMP | post-CMP thickness map, center vs edge | ? |
| 2 | Spin coat thickness peak at center | litho track, coat | resist thickness profile | ? |
| 3 | Plasma density peak on axis | etch or dep | chamber match, RF tuning | ? |
| 4 | Chuck temperature gradient, center hot | any thermal step | chuck temp map, last calibration | ? |

You need to fill in what separates 1 from 3. Both give a center-weighted radial
signature. A junior engineer cannot tell them apart from the map alone, and that
is the entire reason this project exists.

## C02 — Donut, 41x42, 25.6% fail

**Look at this one before you write anything.** It is labeled Donut but it is an
off-center filled blob with a partial ring, not an annulus. Either the label is
wrong or "Donut" in this dataset is looser than the name implies.

That is finding material. If the public labels are noisy, then a benchmark scored
against those labels has a ceiling, and yours scored against physical cause does not.

| # | mechanism | step | check | discriminator |
|---|---|---|---|---|
| 1 | Radial non-uniformity, mid-radius band | spin coat / bake | thickness vs radius | ? |
| 2 | Bake plate ring / proximity pin pattern | post-exposure bake | plate temp map, pin layout | ? |
| 3 | Plasma ring at fixed radius | etch | ring position vs chamber geometry | ? |

## C03 — Edge-Ring, 44x48, 15.0% fail

Continuous failing ring at the extreme periphery, clean interior. The textbook case.

Fully worked in `kb/patterns.yaml` already, from your own plan: EBR nozzle drift,
bevel etch excursion, edge clamp contact. This is the one entry where the
discriminator column is written and it is the one that reads as real. Use its
shape as the template for the other eight.

## C04 — Edge-Loc, 35x40, 15.8% fail

Failures on the edge but confined to one arc, roughly the right side, not the
full ring.

| # | mechanism | step | check | discriminator |
|---|---|---|---|---|
| 1 | Edge clamp or end-effector contact at fixed position | handling / robot | clamp position log | angular position repeats across wafers |
| 2 | Localized EBR failure, one nozzle sector | litho track | nozzle log | ? |
| 3 | Non-uniform edge exposure / focus at periphery | litho | focus map at edge | ? |

The angular-position-repeats discriminator is the useful one. Note that the raw
maps do not carry notch orientation, so you cannot compute theta reliably from
WM-811K alone. Write that down as a limitation.

## C05 — Loc, 35x31, 14.9% fail

One localized cluster, mid-radius, plus background noise.

| # | mechanism | step | check | discriminator |
|---|---|---|---|---|
| 1 | Particle drop / chamber flaking | any | particle counts, last PM | ? |
| 2 | Chuck pin or lift pin contact | any vacuum chuck step | pin layout vs cluster position | ? |
| 3 | Localized dep or etch non-uniformity | dep / etch | chamber match | ? |

Loc vs Random is your worst confusion in week 2. Predict now what you think the
threshold is between "one cluster plus noise" and "just noise," then check.

## C06 — Scratch, 41x33, 10.0% fail

Faint near-vertical line upper left. Much subtler than the class name suggests.

| # | mechanism | step | check | discriminator |
|---|---|---|---|---|
| 1 | CMP pad debris / slurry agglomerate drag | CMP | pad condition, slurry filter | ? |
| 2 | Robot handling contact | transfer | robot teach data | ? |
| 3 | Carrier or chuck contact drag | any | chuck surface inspection | ? |

## C07 — Random, 27x25, 47.9% fail

Failures everywhere with no structure, at very high density.

At 47.9% this is not really "random defectivity," it is a wafer that mostly
failed. Whether that is a distinct physical situation from Near-full or just a
labeling threshold is a question you can answer and a paper cannot.

## C08 — Near-full, 25x27, 87.8% fail

Almost the whole wafer failed.

| # | mechanism | step | check | discriminator |
|---|---|---|---|---|
| 1 | Wrong recipe / misprocessed | any | MES history for the lot | recipe ID mismatch is definitive |
| 2 | Tool crash or abort mid-process | any | alarm log at process time | ? |
| 3 | Gross contamination event | any | ? | ? |
| 4 | Test / probe card failure, not process at all | wafer sort | retest the wafer | retest passes |

Cause 4 matters and is the kind of thing that gets missed. A near-full map can be
a probe problem, not a process problem. Only 149 of these exist in the whole
labeled set and 20 are in test, so do not report per-class metrics for it.

## C09 — Center, 25x27, 35.0% fail

Same product family as C01, same class. Included deliberately.

The 25x27 family is **12.0% Center** while every other top family is 0.0 to 1.7%.
So the model can guess Center from the grid dimensions alone. Keep C01 and C09
paired in the demo and use them to make the leakage point concretely.

## C10 — none, 45x48, 5.2% fail

No spatial structure, 5.2% scattered failures. The negative control.

An RCA tool that cannot say "nothing systematic here, this is normal yield loss"
is useless in production, because 85% of real wafers look like this. Whatever you
build has to get C10 right before anything else matters.

---

## What to do with this file

1. Open `reports/figures/reference_cases.png` next to it.
2. Go case by case. Delete what is wrong. That is the important verb.
3. Fill every `?`. If you cannot fill a discriminator, the cause does not belong
   in the list.
4. Promote what survives into `kb/patterns.yaml` with `confidence: from_memory`,
   then verify against May & Spanos and mark `verified`.
