# JP/EN 100 Pair Temp Sweep Runbook (Rust MAGI / Ollama)

## Scope

- Dataset: `pairs_ja_en_100.json` -> expanded to 200 tasks (`item_id = PNNN:ja|en`)
- Nodes: `zorya`, `eve`
- Backend: `ollama` (`accel=rocm`)
- Sweep temperatures: `0.0 / 0.1 / 0.2 / 0.7`
- Epochs: `30`, Replicates: `1`
- Non-stub rule: `MAGI_OLLAMA_STUB` must be unset

## Generated Files

- Tasks:
  - `/home/limonene/ROCm-project/ROCm-MCP_rust/tasks/generated/jp_en_100_tasks.json`
- Plans:
  - `jp_en100_zorya_t0p0_e30.json`
  - `jp_en100_zorya_t0p1_e30.json`
  - `jp_en100_zorya_t0p2_e30.json`
  - `jp_en100_zorya_t0p7_e30.json`
  - `jp_en100_eve_t0p0_e30.json`
  - `jp_en100_eve_t0p1_e30.json`
  - `jp_en100_eve_t0p2_e30.json`
  - `jp_en100_eve_t0p7_e30.json`

## Model Tag Alignment (both nodes verified)

- `deepseek-r1-distill-qwen-7b-q4_k_m-t0p0:latest`
- `deepseek-r1-distill-qwen-7b-q4_k_m-t0p1:latest`
- `deepseek-r1-distill-qwen-7b-q4_k_m-t0p2:latest`
- `deepseek-r1-distill-qwen-7b-q4_k_m-t0p7:latest`

## Preflight (per node, t0p1 first)

### zorya

```bash
ssh limonene@zorya '
set -euo pipefail
BIN=/home/limonene/magi_bin_20260305
PLAN=/home/limonene/magi_plans_20260306/jp_en100_zorya_t0p1_e30.json
export MAGI_RUNNER_BIN=$BIN/magi-runner
unset MAGI_OLLAMA_STUB

$BIN/magi-master plan validate "$PLAN" --json
$BIN/magi-master plan submit "$PLAN"
$BIN/magi-master dispatch local --plan jp_en100_zorya_t0p1_e30_20260306 --limit 1

PLAN_DIR=/home/limonene/ROCm-project/tank/artifacts/plans/jp_en100_zorya_t0p1_e30_20260306
RID=$(tail -n 1 "$PLAN_DIR/dispatch.exec.jsonl" | jq -r .run_id)
RUN_DIR=/home/limonene/ROCm-project/tank/artifacts/runs/$RID

$BIN/magi-master integrate --run "$RID"
echo "RID=$RID"
wc -l "$RUN_DIR/responses.jsonl"
head -n 2 "$RUN_DIR/responses.jsonl" | jq -r .raw_output | sed -n "1,2p"
'
```

### eve

```bash
ssh limonene@eve '
set -euo pipefail
BIN=/home/limonene/magi_bin_20260305
PLAN=/home/limonene/magi_plans_20260306/jp_en100_eve_t0p1_e30.json
export MAGI_RUNNER_BIN=$BIN/magi-runner
unset MAGI_OLLAMA_STUB

$BIN/magi-master plan validate "$PLAN" --json
$BIN/magi-master plan submit "$PLAN"
$BIN/magi-master dispatch local --plan jp_en100_eve_t0p1_e30_20260306 --limit 1

PLAN_DIR=/home/limonene/ROCm-project/tank/artifacts/plans/jp_en100_eve_t0p1_e30_20260306
RID=$(tail -n 1 "$PLAN_DIR/dispatch.exec.jsonl" | jq -r .run_id)
RUN_DIR=/home/limonene/ROCm-project/tank/artifacts/runs/$RID

$BIN/magi-master integrate --run "$RID"
echo "RID=$RID"
wc -l "$RUN_DIR/responses.jsonl"
head -n 2 "$RUN_DIR/responses.jsonl" | jq -r .raw_output | sed -n "1,2p"
'
```

## Full Sweep (after preflight non-stub passed)

### zorya plans

```bash
for P in /home/limonene/magi_plans_20260306/jp_en100_zorya_t0p{0,1,2,7}_e30.json; do
  BIN=/home/limonene/magi_bin_20260305
  PLAN_ID=$(jq -r .plan_id "$P")
  export MAGI_RUNNER_BIN=$BIN/magi-runner
  unset MAGI_OLLAMA_STUB
  $BIN/magi-master plan validate "$P" --json
  $BIN/magi-master plan submit "$P"
  $BIN/magi-master dispatch local --plan "$PLAN_ID" --limit 30
  PLAN_DIR=/home/limonene/ROCm-project/tank/artifacts/plans/$PLAN_ID
  jq -r .run_id "$PLAN_DIR/dispatch.exec.jsonl" | while read -r RID; do
    $BIN/magi-master integrate --run "$RID"
  done
  $BIN/magi-master plan aggregate --plan "$PLAN_ID" > "/tmp/${PLAN_ID}.aggregate.txt"
done
```

### eve plans

```bash
for P in /home/limonene/magi_plans_20260306/jp_en100_eve_t0p{0,1,2,7}_e30.json; do
  BIN=/home/limonene/magi_bin_20260305
  PLAN_ID=$(jq -r .plan_id "$P")
  export MAGI_RUNNER_BIN=$BIN/magi-runner
  unset MAGI_OLLAMA_STUB
  $BIN/magi-master plan validate "$P" --json
  $BIN/magi-master plan submit "$P"
  $BIN/magi-master dispatch local --plan "$PLAN_ID" --limit 30
  PLAN_DIR=/home/limonene/ROCm-project/tank/artifacts/plans/$PLAN_ID
  jq -r .run_id "$PLAN_DIR/dispatch.exec.jsonl" | while read -r RID; do
    $BIN/magi-master integrate --run "$RID"
  done
  $BIN/magi-master plan aggregate --plan "$PLAN_ID" > "/tmp/${PLAN_ID}.aggregate.txt"
done
```

## Analyzer

```bash
python3 /home/limonene/ROCm-project/ROCm-MCP_rust/analysis/analyze_pairs.py \
  --tank-root /home/limonene/ROCm-project/tank \
  --artifact-root artifacts \
  --gold /home/limonene/ROCm-project/ROCm-MCP_rust/analysis/gold_answers.json \
  --out-dir /home/limonene/ROCm-project/tank/tmp_bak/magi_out_pairs_now
```

## Hard Stop Conditions

- `responses.jsonl` first lines start with `stubbed-output:` -> STOP.
- `responses.jsonl` line count != 200 in preflight -> STOP.
- `spec.tasks` missing and `tasks.json` missing -> STOP.
