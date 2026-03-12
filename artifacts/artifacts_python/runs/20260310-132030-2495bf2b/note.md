# RunPod Sweep (MI300X) 実行結果・障害調査メモ

## 事象
Python版の Sweep 実験 (`<INSTALL_DIR>/batch_script/STAGE01/3-run_plan.py`) を RunPod の MI300X ノード (`root@YOUR_RUNPOD_IP`) で実行したところ、以下の事象が発生した。
- GPUの稼働率 (`rocm-smi`) は 0% となりアイドル状態に見える。
- しかし、バッチスクリプト側は処理が終わらず、`responses.jsonl` がローカルに同期されないままプロセスがスタックしている（ように見えた）。

## 調査の足跡

### 1. リモート上の動作ディレクトリとログの確認
リモート上では `fallback_tmp` モードで動作しており、 `/tmp/magi_runs/20260310-132030-2495bf2b/` に結果ファイルが生成されていた。
```bash
> ssh -o StrictHostKeyChecking=no root@YOUR_RUNPOD_IP -p 13771 -i ~/.ssh/YOUR_KEY "ls -lat /tmp/magi_runs/*/ | head -n 20"
```
結果として、リモート上には以下のファイルがすでに生成されていることが確認できた。
- `compute.exit.json` (6,957 bytes)
- `compute.stderr.log` (1,506,248 bytes)
- `responses.jsonl` (484,419 bytes)

### 2. 失敗原因の特定 (`compute.exit.json`)
結果ファイルの生成自体は完了していたため、なぜ失敗 (`exit 1`) になり、結果として SCP （ローカルへの同期）が行われなかったのか確認した。
```bash
> ssh -o StrictHostKeyChecking=no root@YOUR_RUNPOD_IP -p 13771 -i ~/.ssh/YOUR_KEY "cat /tmp/magi_runs/*/compute.exit.json"
```
これを見ると、`timeout_sec_per_task=120`（120秒）の制限に引っ掛かるタスクが多発していることが判明した。
以下のように、全200タスク中、49タスクが120秒を経過（`elapsed_ms=120011`）して強制終了されていた。
```json
{
  "kind": "semantic",
  "path": "/runner/inference",
  "message": "item_id=P100:ja type=timeout elapsed_ms=120013 exit=n/a"
}
```

### 3. スクリプトの挙動とエラーの詳細 (`compute.stderr.log`)
ローカルへ rsync が入っておらず `scp` にて回収し、標準エラーの内容を確認した。
```bash
> scp -P 13771 -i ~/.ssh/YOUR_KEY root@YOUR_RUNPOD_IP:/tmp/magi_runs/20260310-132030-2495bf2b/compute.* <TANK_DIR>/artifacts_py/runs/20260310-132030-2495bf2b/
> scp -P 13771 -i ~/.ssh/YOUR_KEY root@YOUR_RUNPOD_IP:/tmp/magi_runs/20260310-132030-2495bf2b/responses.jsonl <TANK_DIR>/artifacts_py/runs/20260310-132030-2495bf2b/

> tail -n 30 <TANK_DIR>/artifacts_py/runs/20260310-132030-2495bf2b/compute.stderr.log
```
出力（抜粋）：
```text
[P098:en] cmd='ollama run deepseek-r1-distill-qwen-7b-q4_k_m-t0p0:latest <prompt>' exit=timeout elapsed_ms=120012 stub_mode=off
[P099:ja] cmd='ollama run deepseek-r1-distill-qwen-7b-q4_k_m-t0p0:latest <prompt>' exit=0 elapsed_ms=4700 stub_mode=off
```
成功しているタスク（`P099:ja`）は 4.7秒 ほどで完了しているのに対し、タイムアウトしているタスク（`P098:en`）は正確に120秒で強制終了させられている。

## 結論と考察
- 発生事象の原因はシステム（RunPod側）のハングなどではなく、**LLMモデル（DeepSeek-R1-Distill-Qwen-7B）の思考（`<think>`）ループ発生による明確なタスクタイムアウト**である。
- プランの設定である `timeout_sec_per_task=120` が短いわけではなく、120秒以上考え込んでいるケースは無限ループや反復に陥っているケースがほとんどであると予想される。
- 1Epoch中に49件も120秒のタイムアウト待ちが発生したため、トータルで膨大な処理時間がかかっている。（今現在もローカルの `zorya`, `eve` で同様に120秒待ちが大量発生している可能性が高い）
- **対策:** 今後別の実験や本番で回す際は、この「無駄なタイムアウト待ち」を切り上げるために `timeout_sec_per_task=60` などに切り詰めるか、出力モデル側からの応答長（`max_new_tokens`）を調整してループを未然に防ぐなどのプランニングが必要である。
