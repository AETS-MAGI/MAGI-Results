#!/usr/bin/env python3
"""
stats_py_mi300x.py
==================
R版と等価な統計検定をPythonで実行（scipy / statsmodels使用）。
Rが使える環境では stats_py_mi300x.R を推奨。

検定内容:
  1) think漏れ率 ~ 言語 (Fisher exact)
  2) JSON有効率 ~ 言語 (Fisher exact)
  3) 正答率 ~ 言語 (Fisher exact, 7B)
  4) 温度 × JSON有効率 Spearman相関 (言語別)
  5) think漏れ率 ~ モデルサイズ (7B vs 32B, Fisher exact)
  6) 95% Wilson CI 一覧

出力先: ../data/artifacts/agg_py_mi300x/
"""

import csv
import json
import math
from pathlib import Path
from collections import defaultdict

import numpy as np
from scipy import stats
from scipy.stats import fisher_exact, spearmanr

OUT_DIR = Path(__file__).parent.parent / "data/artifacts/agg_py_mi300x"
OUT_DIR.mkdir(parents=True, exist_ok=True)

# ── Wilson CI ────────────────────────────────────────────
def wilson_ci(k: int, n: int, conf: float = 0.95) -> dict:
    if n == 0:
        return {"rate": None, "low": None, "high": None}
    z = stats.norm.ppf(1 - (1 - conf) / 2)
    p_hat = k / n
    denom = 1 + z**2 / n
    centre = (p_hat + z**2 / (2*n)) / denom
    half = z * math.sqrt(p_hat * (1 - p_hat) / n + z**2 / (4*n**2)) / denom
    return {
        "rate":  round(p_hat, 6),
        "low":   round(max(0.0, centre - half), 6),
        "high":  round(min(1.0, centre + half), 6),
    }

# ── データ読み込み ─────────────────────────────────────────
print("== データ読み込み ==")
all_path = OUT_DIR / "all_responses.csv"

def parse_bool(v: str) -> bool | None:
    if v.lower() in ("true", "1"):  return True
    if v.lower() in ("false", "0"): return False
    return None

def parse_float(v: str) -> float | None:
    try: return float(v)
    except: return None

rows = []
with open(all_path) as f:
    reader = csv.DictReader(f)
    for r in reader:
        rows.append({
            "source":          r["source"],
            "model_id":        r["model_id"],
            "node_id":         r["node_id"],
            "temperature":     parse_float(r["temperature"]),
            "item_id":         r["item_id"],
            "lang":            r["lang"],
            "gold_answer":     r["gold_answer"],
            "think_leaked":    parse_bool(r["think_leaked"]),
            "raw_json_valid":  parse_bool(r["raw_json_valid"]),
            "strip_json_valid": parse_bool(r["strip_json_valid"]),
            "raw_correct":     parse_bool(r["raw_correct"]),
            "strip_correct":   parse_bool(r["strip_correct"]),
        })
print(f"  rows: {len(rows)}\n")

def subset(rows, **kwargs):
    result = rows
    for k, v in kwargs.items():
        if callable(v):
            result = [r for r in result if v(r[k])]
        elif isinstance(v, (list, set, tuple)):
            result = [r for r in result if r[k] in v]
        else:
            result = [r for r in result if r[k] == v]
    return result

is_7b   = lambda m: "7b"   in m.lower()
is_32b  = lambda m: "32b"  in m.lower()
is_qwen = lambda m: "qwen3" in m.lower()

df_7b        = subset(rows, model_id=is_7b)
df_32b       = subset(rows, model_id=is_32b)
df_qwen      = subset(rows, model_id=is_qwen)
df_7b_enja   = subset(df_7b, lang=["en","ja"])
df_7b_scored = subset(df_7b_enja, strip_correct=lambda v: v is not None)

def contingency_2x2(sub, col):
    """col が True/False の2×2 → (TT, TF, FT, FF)"""
    # [[True, False], [True, False]] だと混乱するので
    # [[col=True, col=False], [col=True, col=False]] — Fisher用に手で作る
    pass

def fisher_2x2(sub_a, sub_b, col):
    """サブセットa, bでcol=True/Falseの2×2テーブルを作りFisher検定"""
    a_t = sum(1 for r in sub_a if r[col] is True)
    a_f = sum(1 for r in sub_a if r[col] is False)
    b_t = sum(1 for r in sub_b if r[col] is True)
    b_f = sum(1 for r in sub_b if r[col] is False)
    table = [[a_t, a_f], [b_t, b_f]]
    # scipy.stats.fisher_exact returns (oddsratio, pvalue)
    or_, p_val = fisher_exact(table, alternative="two-sided")
    return {"table": table, "p_value": p_val, "OR": float(or_)}

stat_results = {}

# ──────────────────────────────────────────────────────────
# 1) think漏れ率 ~ 言語
# ──────────────────────────────────────────────────────────
print("== 1) think漏れ率 ~ 言語 (Fisher exact, 7B) ==")
en_rows = subset(df_7b_enja, lang="en")
ja_rows = subset(df_7b_enja, lang="ja")
res1 = fisher_2x2(en_rows, ja_rows, "think_leaked")
print(f"  table (en/ja × leak_T/F): {res1['table']}")
print(f"  p = {res1['p_value']:.4e},  OR = {res1['OR']:.4f}\n")
stat_results["think_leak_vs_lang"] = res1

# ──────────────────────────────────────────────────────────
# 2) JSON有効率 ~ 言語
# ──────────────────────────────────────────────────────────
print("== 2) JSON有効率 ~ 言語 (Fisher exact, 7B) ==")
res2 = fisher_2x2(en_rows, ja_rows, "raw_json_valid")
print(f"  table (en/ja × valid_T/F): {res2['table']}")
print(f"  p = {res2['p_value']:.4e},  OR = {res2['OR']:.4f}\n")
stat_results["json_valid_vs_lang"] = res2

# ──────────────────────────────────────────────────────────
# 3) 正答率 ~ 言語 (7B)
# ──────────────────────────────────────────────────────────
print("== 3) 正答率 ~ 言語 (Fisher exact, 7B) ==")
en_scored = subset(df_7b_scored, lang="en")
ja_scored = subset(df_7b_scored, lang="ja")
if en_scored and ja_scored:
    res3 = fisher_2x2(en_scored, ja_scored, "strip_correct")
    print(f"  table (en/ja × correct_T/F): {res3['table']}")
    print(f"  p = {res3['p_value']:.4e},  OR = {res3['OR']:.4f}\n")
    stat_results["accuracy_vs_lang"] = res3
else:
    print("  スコアリング可能データなし\n")

# ──────────────────────────────────────────────────────────
# 4) 温度 × JSON有効率 Spearman (言語別, 7B)
# ──────────────────────────────────────────────────────────
print("== 4) 温度 × JSON有効率 Spearman (7B, 言語別) ==")
temp_corr = {}
for lng in ["en","ja"]:
    sub = [r for r in df_7b_enja if r["lang"]==lng and r["temperature"] is not None]
    if len(sub) < 5: continue
    temps  = [r["temperature"] for r in sub]
    valids = [1 if r["raw_json_valid"] else 0 for r in sub]
    rho, p_val = spearmanr(temps, valids)
    ci = wilson_ci(sum(valids), len(valids))
    print(f"  lang={lng}: rho={rho:.4f}, p={p_val:.4e}, n={len(sub)}, "
          f"json_valid_rate={ci['rate']:.4f} [{ci['low']:.4f}, {ci['high']:.4f}]")
    temp_corr[lng] = {
        "lang": lng, "n": len(sub),
        "spearman_rho": round(rho, 6),
        "p_value": round(p_val, 8),
        "json_valid_rate": ci["rate"],
        "json_valid_ci_lo": ci["low"],
        "json_valid_ci_hi": ci["high"],
    }
print()
stat_results["temp_vs_json_spearman"] = temp_corr

# ──────────────────────────────────────────────────────────
# 5) think漏れ率 ~ モデルサイズ (7B vs 32B)
# ──────────────────────────────────────────────────────────
print("== 5) think漏れ率 ~ モデルサイズ (7B vs 32B) ==")
if df_32b:
    res5 = fisher_2x2(df_7b, df_32b, "think_leaked")
    print(f"  table (7B/32B × leak_T/F): {res5['table']}")
    print(f"  p = {res5['p_value']:.4e},  OR = {res5['OR']:.4f}\n")
    stat_results["think_leak_vs_model_size"] = res5

# ──────────────────────────────────────────────────────────
# 6) 95% Wilson CI 一覧
# ──────────────────────────────────────────────────────────
print("== 6) 95% Wilson CI ==")
ci_table = []

def ci_row(label, sub, col):
    valid = [r for r in sub if r[col] is not None]
    if not valid: return None
    k = sum(1 for r in valid if r[col] is True)
    n = len(valid)
    ci = wilson_ci(k, n)
    print(f"  {label:<45}  n={n:5d}  rate={ci['rate']:.4f} [{ci['low']:.4f}, {ci['high']:.4f}]")
    return {"label": label, "n": n, "k": k, **ci}

for row in [
    ci_row("7B en: think_leak",         en_rows,      "think_leaked"),
    ci_row("7B ja: think_leak",         ja_rows,      "think_leaked"),
    ci_row("7B en: json_valid",         en_rows,      "raw_json_valid"),
    ci_row("7B ja: json_valid",         ja_rows,      "raw_json_valid"),
    ci_row("7B en: strip_json_valid",   en_rows,      "strip_json_valid"),
    ci_row("7B ja: strip_json_valid",   ja_rows,      "strip_json_valid"),
    ci_row("7B en: accuracy",           en_scored,    "strip_correct"),
    ci_row("7B ja: accuracy",           ja_scored,    "strip_correct"),
    ci_row("32B: think_leak",           df_32b,       "think_leaked"),
    ci_row("32B: json_valid",           df_32b,       "raw_json_valid"),
    ci_row("Qwen3.5-9B: think_leak",   df_qwen,      "think_leaked"),
    ci_row("Qwen3.5-9B: json_valid",   df_qwen,      "raw_json_valid"),
]:
    if row:
        ci_table.append(row)

# CSV保存
with open(OUT_DIR / "wilson_ci_summary.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=["label","n","k","rate","low","high"])
    w.writeheader()
    w.writerows(ci_table)
print(f"\n  → 保存: {OUT_DIR}/wilson_ci_summary.csv")

# JSON保存
with open(OUT_DIR / "stat_tests.json", "w") as f:
    json.dump(stat_results, f, indent=2, default=str)
print(f"  → 保存: {OUT_DIR}/stat_tests.json")

print("\n[DONE]")
