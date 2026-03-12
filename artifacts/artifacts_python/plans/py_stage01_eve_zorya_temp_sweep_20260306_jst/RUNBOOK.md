# RUNBOOK: Python lane staged sweep (`py_stage01_eve_zorya_temp_sweep_20260306_jst`)

## Scope
- Python lane only:
  - `<INSTALL_DIR>/batch_script/STAGE01`
  - `<TANK_DIR>/artifacts_py`
- Do not write to Rust artifacts (`<TANK_DIR>/artifacts`).

## Environment
```bash
source <ROCM_PROJECT_DIR>/.venv/bin/activate
PLAN=<INSTALL_DIR>/batch_script/STAGE01/plan.stage01.20260306_jst_prod30.json
PLAN_ID=$(jq -r .plan_id "$PLAN")
PLAN_DIR=<TANK_DIR>/artifacts_py/plans/$PLAN_ID
```

## Stage Commands

### S0 preflight gate (node x temp)
Requirements:
- `epochs=1`
- `limit_units=1`
- `limit_tasks=2`
- `timeout=60`
- `preflight retries=2`
- `sleep=5`

Example (single pair):
```bash
python3 <INSTALL_DIR>/batch_script/STAGE01/3-run_plan.py \
  --plan "$PLAN" \
  --only-temp t0p1 --only-node zorya \
  --epochs 1 --limit-units 1 --limit-tasks 2 \
  --timeout-sec-per-task 60 \
  --preflight-timeout-sec 60 --preflight-retries 2 --sleep-between-retries 5 \
  --max-parallel-per-node 1
```

### S1 short run (passed pairs only)
```bash
python3 <INSTALL_DIR>/batch_script/STAGE01/3-run_plan.py \
  --plan "$PLAN" \
  --only-temp t0p1 --only-node zorya \
  --epochs 1 --limit-units 1 --limit-tasks 20 \
  --timeout-sec-per-task 120 \
  --preflight-timeout-sec 60 --preflight-retries 2 --sleep-between-retries 5 \
  --max-parallel-per-node 1
```
Success condition:
- `responses.jsonl` line count = 20
- invalid JSON lines = 0

### S2 full tasks single epoch (passed pairs only)
```bash
python3 <INSTALL_DIR>/batch_script/STAGE01/3-run_plan.py \
  --plan "$PLAN" \
  --only-temp t0p1 --only-node zorya \
  --epochs 1 --limit-units 1 --limit-tasks 200 \
  --timeout-sec-per-task 180 \
  --preflight-timeout-sec 60 --preflight-retries 2 --sleep-between-retries 5 \
  --max-parallel-per-node 1
```
Success condition:
- `responses.jsonl` line count = 200

### S3 production (temp rollout order)
Rollout order must be:
1. `t0p1`
2. `t0p2`
3. `t0p0`
4. `t0p7`

Per temp, execute both nodes (only passed pairs) with:
```bash
python3 <INSTALL_DIR>/batch_script/STAGE01/3-run_plan.py \
  --plan "$PLAN" \
  --only-temp t0p1 \
  --epochs 30 --limit-units 30 --limit-tasks 200 \
  --timeout-sec-per-task 180 \
  --preflight-timeout-sec 60 --preflight-retries 2 --sleep-between-retries 5 \
  --max-parallel-per-node 1
```
If repeated timeout occurs for a temp, isolate that temp and move to next temp.

## Progress Monitoring

### dispatch events live
```bash
tail -f "$PLAN_DIR/dispatch.exec.jsonl"
```

### status counters
```bash
jq -r '.status' "$PLAN_DIR/dispatch.exec.jsonl" | sort | uniq -c
jq -c 'select(.phase=="end") | {run_id,node_id,temp_label,status,exit_code,ended_at}' "$PLAN_DIR/dispatch.exec.jsonl"
```

### responses line count for latest run
```bash
RID=$(tail -n 1 "$PLAN_DIR/dispatch.exec.jsonl" | jq -r .run_id)
RUN_DIR=<TANK_DIR>/artifacts_py/runs/$RID
wc -l "$RUN_DIR/responses.jsonl"
```

### failed / ok filter
```bash
jq -c 'select(.phase=="end" and .status=="failed")' "$PLAN_DIR/dispatch.exec.jsonl"
jq -c 'select(.phase=="end" and .status=="ok")' "$PLAN_DIR/dispatch.exec.jsonl"
```

## Hang Detection
- Hang suspect: `phase=start` exists but no matching `phase=end` for > 15 minutes.

Check:
```bash
jq -c 'select(.phase=="start") | {run_id,node_id,temp_label,started_at}' "$PLAN_DIR/dispatch.exec.jsonl"
jq -c 'select(.phase=="end") | {run_id,ended_at,status,exit_code}' "$PLAN_DIR/dispatch.exec.jsonl"
```

## Stop / Safe Resume

### stop local launcher
```bash
pkill -TERM -f '<INSTALL_DIR>/batch_script/STAGE01/3-run_plan.py'
```

### stop remote stuck execution
```bash
ssh YOUR_USER@YOUR_HOST_ZORYA "pkill -TERM -f 'ollama run|magi_runs|artifacts_py/runs'"
ssh YOUR_USER@YOUR_HOST_EVE   "pkill -TERM -f 'ollama run|magi_runs|artifacts_py/runs'"
```

### resume
- Isolate failed pair in `step_results.json`.
- Re-run next pair with same stage command.

## Analyzer (S2 minimum)
Use read-only analyzer source from Rust repo, output to `artifacts_py`:
```bash
OUT_DIR="$PLAN_DIR/analysis_out"
mkdir -p "$OUT_DIR"
python3 <RUST_REPO_DIR>/analysis/analyze_pairs.py \
  --runs-root <TANK_DIR>/artifacts_py/runs \
  --out-dir "$OUT_DIR"
```
Expected artifacts:
- `$OUT_DIR/report.md`
- `$OUT_DIR/summary.csv`
