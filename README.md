# WaferRCA

Wafer bin map in. Ranked, physically grounded root causes out — with the process
step to go check and the observation that tells the candidates apart.

Classifying the pattern is solved and has been since 2015. This project is about
the next three sentences: the ones a senior process engineer says out loud and a
junior engineer does not know yet.

## Status

Week 1 of 8. Data pipeline up, knowledge base started.

## Layout

```
scripts/00_fetch_data.sh     WM-811K from the MIR Lab mirror (no Kaggle account)
scripts/01_prepare_data.py   pickle -> labeled parquet + lot-level split
scripts/02_plot_grid.py      contact sheets, one per class + imbalance chart
scripts/03_check_kb.py       structural check on the knowledge base
kb/patterns.yaml             THE knowledge base. hand-authored. the actual work.
benchmark/                   scored cases (week 6)
reports/figures/             generated
```

## Setup

```bash
uv venv --python 3.12 .venv
uv pip install pandas pyarrow numpy matplotlib scikit-learn pyyaml tqdm
bash scripts/00_fetch_data.sh
.venv/bin/python scripts/01_prepare_data.py
.venv/bin/python scripts/02_plot_grid.py
```

## Honest limitations

- Wafer maps are real (WM-811K, 811,457 maps from a real fab, ~21% labeled).
- Equipment context blocks in the benchmark are **synthetic and representative**,
  not real fab telemetry. Real telemetry does not leave a fab.
- The knowledge base is one engineer's domain experience, verified against
  published sources where possible. Every record carries a confidence field.

## Data

WM-811K / LSWMD, Wu, Jang & Chen, *IEEE Trans. Semiconductor Manufacturing*, 2015.
Mirror: http://mirlab.org/dataSet/public/MIR-WM811K.zip
