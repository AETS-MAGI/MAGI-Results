#!/usr/bin/env python3
"""
aggregate_py_mi300x.py
======================
PythonランナーおよびMI300X実験のresponses.jsonlを集計する。

集計内容:
  - think漏れあり/なし での JSON有効率
  - think内テキスト vs 最終答え(JSON) の抽出
  - gold_canonical_answer との照合による正答率
  - 温度・モデル・言語・ノード別クロス集計

出力先: ../data/artifacts/agg_py_mi300x/
スクリプト: lab_note/analysis-scripts/
"""

import os
import re
import json
import csv
from pathlib import Path
from collections import defaultdict

# ── パス設定 ──────────────────────────────────────────────────
BASE = Path(__file__).parent.parent  # lab_note/
RUNS_DIRS = {
    "artifacts_py":         BASE / "data/artifacts_py/runs",
    "artifacts_python-MI300X": BASE / "data/artifacts_python-MI300X/runs",
}
OUT_DIR = BASE / "data/artifacts/agg_py_mi300x"
OUT_DIR.mkdir(parents=True, exist_ok=True)


# ── ユーティリティ ────────────────────────────────────────────
THINK_RE = re.compile(r"<think>(.*?)</think>", re.DOTALL | re.IGNORECASE)
CODE_JSON_RE = re.compile(r"```(?:json)?\s*(\{.*?\}|\[.*?\])\s*```", re.DOTALL)
BARE_JSON_RE = re.compile(r"(\{[^{}]*\})", re.DOTALL)


def extract_think(text: str) -> tuple[str, str]:
    """(think_content, text_without_think) を返す"""
    thinks = THINK_RE.findall(text)
    stripped = THINK_RE.sub("", text).strip()
    return "\n".join(thinks).strip(), stripped


def try_parse_json(text: str) -> dict | None:
    """text からJSONを抽出して辞書を返す。失敗したら None"""
    # 1) そのままパース
    try:
        return json.loads(text.strip())
    except Exception:
        pass
    # 2) ```json...``` ブロック
    m = CODE_JSON_RE.search(text)
    if m:
        try:
            return json.loads(m.group(1))
        except Exception:
            pass
    # 3) 裸のJSONオブジェクト（最長マッチ）
    candidates = BARE_JSON_RE.findall(text)
    for c in reversed(candidates):
        try:
            return json.loads(c)
        except Exception:
            pass
    return None


def normalize_answer(ans: str | None) -> str:
    """A / B / C / D を正規化（前後空白・大文字化）"""
    if ans is None:
        return ""
    return str(ans).strip().upper().split(":")[0][:1]


# ── 1 runを処理 ────────────────────────────────────────────────
def process_run(run_dir: Path, source_tag: str) -> list[dict]:
    """responses.jsonl + tasks.json + spec.json + env.json を合わせて行リストを返す"""
    rows = []

    spec_f   = run_dir / "spec.json"
    tasks_f  = run_dir / "tasks.json"
    resp_f   = run_dir / "responses.jsonl"
    env_f    = run_dir / "env.json"

    if not resp_f.exists():
        return rows

    # spec
    spec, env = {}, {}
    if spec_f.exists():
        spec = json.load(open(spec_f))
    if env_f.exists():
        env  = json.load(open(env_f))

    run_id   = spec.get("run_id", run_dir.name)
    sp       = spec.get("spec", {})
    model_id = sp.get("model_id", "unknown")
    gp       = sp.get("gen_params", {})
    temperature = gp.get("temperature", None)
    node_id  = sp.get("node_id", env.get("node_id", "unknown"))

    # tasks → gold answer マップ
    gold_map: dict[str, str] = {}
    if tasks_f.exists():
        tasks = json.load(open(tasks_f))
        for t in tasks:
            meta = t.get("meta", {})
            gold = meta.get("gold_canonical_answer", "")
            gold_map[t["item_id"]] = gold

    # responses
    with open(resp_f) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                resp = json.loads(line)
            except Exception:
                continue

            item_id  = resp.get("item_id", "")
            raw_out  = resp.get("raw_output", "")
            lang     = item_id.split(":")[-1] if ":" in item_id else "unknown"
            gold_ans = gold_map.get(item_id, "")

            # think 抽出
            think_content, stripped = extract_think(raw_out)
            think_leaked = bool(THINK_RE.search(raw_out))

            # JSON 解析 — raw
            raw_json   = try_parse_json(raw_out)
            raw_valid  = raw_json is not None

            # JSON 解析 — strip後
            strip_json  = try_parse_json(stripped)
            strip_valid = strip_json is not None

            # 正答判定
            def correct(parsed: dict | list | None, gold: str) -> bool | None:
                if parsed is None or not gold:
                    return None
                # list の場合は最初の dict 要素を使う
                if isinstance(parsed, list):
                    parsed = next((x for x in parsed if isinstance(x, dict)), None)
                if not isinstance(parsed, dict):
                    return None
                pred = normalize_answer(parsed.get("canonical_answer"))
                return pred == normalize_answer(gold)

            raw_correct   = correct(raw_json,   gold_ans)
            strip_correct = correct(strip_json,  gold_ans)

            # think内に正解があるか（参考）
            think_contains_gold = (
                normalize_answer(gold_ans) in think_content.upper()
                if gold_ans and think_content else False
            )

            rows.append({
                "source":          source_tag,
                "run_id":          run_id,
                "node_id":         node_id,
                "model_id":        model_id,
                "temperature":     temperature,
                "item_id":         item_id,
                "lang":            lang,
                "gold_answer":     gold_ans,
                # think
                "think_leaked":    think_leaked,
                "think_len":       len(think_content),
                "think_content":   think_content[:500],  # 長すぎる場合は切る
                # JSON有効性
                "raw_json_valid":  raw_valid,
                "strip_json_valid": strip_valid,
                # 正答
                "raw_correct":     raw_correct,
                "strip_correct":   strip_correct,
                "think_contains_gold": think_contains_gold,
                # 予測値
                "raw_pred":        normalize_answer((raw_json.get("canonical_answer") if isinstance(raw_json, dict) else None) if raw_json else None),
                "strip_pred":      normalize_answer((strip_json.get("canonical_answer") if isinstance(strip_json, dict) else None) if strip_json else None),
            })

    return rows


# ── 全runを走査 ────────────────────────────────────────────────
def collect_all() -> list[dict]:
    all_rows = []
    for source_tag, runs_dir in RUNS_DIRS.items():
        if not runs_dir.exists():
            print(f"[WARN] not found: {runs_dir}")
            continue
        run_dirs = sorted(runs_dir.iterdir())
        print(f"[INFO] {source_tag}: {len(run_dirs)} runs")
        for rd in run_dirs:
            if rd.is_dir():
                rows = process_run(rd, source_tag)
                all_rows.extend(rows)
    print(f"[INFO] total rows: {len(all_rows)}")
    return all_rows


# ── CSV書き出し ────────────────────────────────────────────────
def write_csv(rows: list[dict], path: Path):
    if not rows:
        return
    fields = list(rows[0].keys())
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)
    print(f"[OUT] {path} ({len(rows)} rows)")


# ── 集計関数 ───────────────────────────────────────────────────
def agg_by(rows: list[dict], keys: list[str]) -> list[dict]:
    """keys でグループ化して正答率・JSON有効率を集計"""
    bucket = defaultdict(list)
    for r in rows:
        k = tuple(r.get(k, "") for k in keys)
        bucket[k].append(r)

    result = []
    for k, rs in sorted(bucket.items()):
        n = len(rs)
        # JSON有効率
        raw_valid_n   = sum(1 for r in rs if r["raw_json_valid"])
        strip_valid_n = sum(1 for r in rs if r["strip_json_valid"])
        # think漏れ率
        think_n = sum(1 for r in rs if r["think_leaked"])

        # 正答率（gold_answerがある行のみ）
        raw_scorable   = [r for r in rs if r["raw_correct"]   is not None]
        strip_scorable = [r for r in rs if r["strip_correct"]  is not None]

        raw_acc   = sum(1 for r in raw_scorable   if r["raw_correct"])   / len(raw_scorable)   if raw_scorable   else None
        strip_acc = sum(1 for r in strip_scorable if r["strip_correct"]) / len(strip_scorable) if strip_scorable else None

        row = dict(zip(keys, k))
        row.update({
            "n":                  n,
            "think_leak_rate":    round(think_n / n, 4),
            "raw_json_valid_n":   raw_valid_n,
            "raw_json_valid_rate": round(raw_valid_n / n, 4),
            "strip_json_valid_n": strip_valid_n,
            "strip_json_valid_rate": round(strip_valid_n / n, 4),
            "valid_gain":         round((strip_valid_n - raw_valid_n) / n, 4),
            "raw_scorable_n":     len(raw_scorable),
            "raw_acc":            round(raw_acc, 4)   if raw_acc   is not None else None,
            "strip_scorable_n":   len(strip_scorable),
            "strip_acc":          round(strip_acc, 4) if strip_acc is not None else None,
            "acc_gain":           round(strip_acc - raw_acc, 4) if (raw_acc is not None and strip_acc is not None) else None,
        })
        result.append(row)
    return result


# ── メイン ────────────────────────────────────────────────────
def main():
    all_rows = collect_all()

    # 全件 raw CSV
    write_csv(all_rows, OUT_DIR / "all_responses.csv")

    # 集計パターン
    agg_configs = [
        ("by_temp",            ["source", "model_id", "temperature"]),
        ("by_temp_lang",       ["source", "model_id", "temperature", "lang"]),
        ("by_node_temp",       ["source", "node_id",  "temperature"]),
        ("by_model",           ["source", "model_id"]),
        ("by_model_lang",      ["source", "model_id", "lang"]),
    ]

    for name, keys in agg_configs:
        agg = agg_by(all_rows, keys)
        write_csv(agg, OUT_DIR / f"agg_{name}.csv")

    # think漏れなし/ありの比較サマリ
    print("\n=== think漏れ統計 ===")
    think_total = sum(1 for r in all_rows if r["think_leaked"])
    print(f"  think_leaked: {think_total}/{len(all_rows)} ({100*think_total/len(all_rows):.1f}%)")
    print(f"  raw_json_valid:   {sum(1 for r in all_rows if r['raw_json_valid'])}/{len(all_rows)}")
    print(f"  strip_json_valid: {sum(1 for r in all_rows if r['strip_json_valid'])}/{len(all_rows)}")

    scorable = [r for r in all_rows if r["strip_correct"] is not None]
    if scorable:
        acc = sum(1 for r in scorable if r["strip_correct"]) / len(scorable)
        print(f"  strip_acc (scorable={len(scorable)}): {acc:.4f}")

    print(f"\n[DONE] 出力先: {OUT_DIR}")


if __name__ == "__main__":
    main()
