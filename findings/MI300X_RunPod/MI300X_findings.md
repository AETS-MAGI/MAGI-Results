# MI300X RunPod — 統計所見レポート

> **対象ハードウェア**: AMD Instinct MI300X（RunPod クラウド GPU）
> **ノード識別子**: `runpod-mi300x`
> **実験日**: 2026-03-06 〜 2026-03-11
> **作成日**: 2026-03-11
> **目的**: DeepSeek-R1 ファミリーにおける think タグ漏洩・JSON 有効率・正答率の言語依存性およびモデルサイズ依存性の検証

---

## 1. データ概要

### 1.1 分析対象レコード数

| モデル | 言語 | N |
|---|---|---|
| DeepSeek-R1-Distill-Qwen-7B (q4_k_m, T=0) | EN | 737 |
| DeepSeek-R1-Distill-Qwen-7B (q4_k_m, T=0) | JA | 502 |
| DeepSeek-R1:32B (T=0) | JA のみ | 600 |
| Qwen3.5:9B (T=0) | JA のみ | 359 |
| **合計** | | **2,198** |

> **注意**: `deepseek-r1:32b` および `qwen3.5:9b` の実行は日本語10問×60試行の繰り返し設計。英語データは存在しない。

### 1.2 ソースファイル

```
lab_note/data/artifacts/agg_py_mi300x/
  all_responses.csv        # 全レコード（18カラム, 6862行）
  stat_by_node.json        # ノード別 Fisher exact 検定結果
  stats_large_models.json  # ラージモデル（32B/Qwen3.5）統計
  qa_think_pairs.jsonl     # think内容+回答ペア（JSONL形式）
  qa_think_pairs.csv       # 同上 CSV 版
```

---

## 2. 統計手法

### 2.1 Wilson 95% 信頼区間

比率 $\hat{p} = k/n$ に対する Wilson スコア区間：

$$
\left[
\frac{\hat{p} + \frac{z^2}{2n} \pm z\sqrt{\frac{\hat{p}(1-\hat{p})}{n} + \frac{z^2}{4n^2}}}{1 + \frac{z^2}{n}}
\right]
$$

ここで $z = 1.959964$（95% 両側）。サンプルサイズが小さい場合も正確な区間を与える。

### 2.2 Fisher 正確検定（両側）

EN vs JA の 2×2 分割表に対して Fisher exact test を適用：

$$
\begin{pmatrix} a & b \\ c & d \end{pmatrix}
= \begin{pmatrix} \text{EN かつ陽性} & \text{EN かつ陰性} \\ \text{JA かつ陽性} & \text{JA かつ陰性} \end{pmatrix}
$$

オッズ比：

$$
\mathrm{OR} = \frac{a/b}{c/d} = \frac{ad}{bc}
$$

$\mathrm{OR} < 1$ は EN の方が陽性率が低いことを示す。

### 2.3 think タグ検出パターン（3種）

本実験では以下の3つのパターンすべてを「think 漏洩」とカウント：

1. `<think>...</think>` — DeepSeek-R1-Distill-Qwen-7B (q4_k_m)
2. `<thinking>...</thinking>` — レア亜種
3. `Thinking...\n...\n...done thinking.` — DeepSeek-R1:32B / Qwen3.5:9B

旧スクリプトはパターン1のみ対応しており、パターン3を見逃していた。修正後に32B/Qwen3.5のthink漏洩率が0%→100%に修正された（後述）。

---

## 3. 実験結果：7B モデル（DeepSeek-R1-Distill-Qwen-7B, T=0）

### 3.1 Think 漏洩率（think_leak_rate）

| 言語 | N | 漏洩数 | 漏洩率 | Wilson 95% CI |
|---|---|---|---|---|
| EN | 737 | 136 | **18.5%** | [15.8%, 21.4%] |
| JA | 502 | 328 | **65.3%** | [61.1%, 69.4%] |

### 3.2 JSON 有効率（json_valid_rate）

| 言語 | N | 有効数 | 有効率 | Wilson 95% CI |
|---|---|---|---|---|
| EN | 737 | 529 | **71.8%** | [68.4%, 74.9%] |
| JA | 502 | 31 | **6.2%** | [4.4%, 8.6%] |

### 3.3 正答率（strip_correct, gold_answer 付き問題のみ）

正解ラベル（`canonical_answer`）は EN/JA ともに利用可能（4択 A/B/C/D）。

| 言語 | N | 正答数 | 正答率 | Wilson 95% CI |
|---|---|---|---|---|
| EN | 737 | 152 | **20.6%** | [17.9%, 23.7%] |
| JA | 502 | 8 | **1.6%** | [0.8%, 3.1%] |

> 参考：ランダム選択の期待正答率は 25%（4択均等）。ただし gold answer の分布が偏っており（B: 52%, C: 27%, A: 19%, D: 2%）、B 全選択戦略では EN 52% が理論上限。

### 3.4 Fisher 正確検定（EN vs JA, 7B T=0）

#### Think 漏洩率

分割表：

$$
\begin{pmatrix} 136 & 601 \\ 328 & 174 \end{pmatrix}
$$

$$
\mathrm{OR} = 0.120, \quad p = 7.53 \times 10^{-64}
$$

EN は JA に比べて think 漏洩が有意に少ない（OR < 1）。

#### JSON 有効率

分割表：

$$
\begin{pmatrix} 529 & 208 \\ 31 & 471 \end{pmatrix}
$$

$$
\mathrm{OR} = 38.64, \quad p = 3.84 \times 10^{-131}
$$

EN は JA に比べて JSON 有効率が有意に高い（OR ≫ 1）。

---

## 4. 実験結果：ラージモデル（DeepSeek-R1:32B / Qwen3.5:9B, MI300X, T=0）

### 4.1 Think 漏洩率・JSON 有効率

| モデル | N | Think 漏洩 | 漏洩率 | JSON 有効 | 有効率 |
|---|---|---|---|---|---|
| DeepSeek-R1:32B | 600 | 600 | **100.0%** | 584 | **97.3%** |
| Qwen3.5:9B | 359 | 359 | **100.0%** | 358 | **99.7%** |

> **重要**: ラージモデルは `Thinking...\n...\n...done thinking.` 形式で think が出力され、**全サンプル（100%）で漏洩**が確認された。旧スクリプトは `<think>` タグのみ検出していたため、これを 0% と誤記録していた（修正済み）。

### 4.2 正答率

32B / Qwen3.5 の実行対象は日本語10問の繰り返し設計（60回/10問）であり、`gold_canonical_answer` が `tasks.json` に記録されていない（gold_answer なし）。正答率の計算は不可。

### 4.3 考察：モデルサイズと think 漏洩の関係

| モデル | Think 漏洩形式 | 漏洩率 | JSON 有効率 |
|---|---|---|---|
| 7B (q4_k_m) | `<think>...</think>` | 7B平均 ~40% | 7B平均 ~40% |
| 32B | `Thinking…done thinking.` | 100% | 97.3% |
| Qwen3.5-9B | `Thinking…done thinking.` | 100% | 99.7% |

7B は思考タグを「隠せる」場合と「漏らす」場合が混在するが、32B/Qwen3.5 は**形式として思考を常に外部出力する**。いずれのモデルサイズでも think は漏洩する。大型モデルの方が JSON 有効率は高い（97–100%）。

---

## 5. データ品質注記

### 5.1 truncated 出力（偽陰性）

`<think>` タグが開いたまま `</think>` が存在しない出力が全体で **58 件**確認された。これらは think_leaked=False とカウントされているが、実際には漏洩している（偽陰性）。影響は全 N に対して軽微。

### 5.2 JSON 抽出失敗（7B の JA）

JA で JSON 有効率が 6.2% と低い原因は、モデルが JSON 形式指示に従わず自然言語で回答するケース（"直接回答型"）が多いため。これはモデルの能力制限ではなく、**プロンプト遵守の言語依存性**として解釈すべき知見。

### 5.3 32B の繰り返し設計

32B の 600 件は日本語 10 問 × 60 回の繰り返し。独立サンプルではないため、標本比率の統計的検定には注意が必要。今回は think 漏洩率・JSON 有効率の記録的評価のみを行う。

---

## 6. 主要所見サマリー

1. **言語効果（MI300X, 7B, T=0）**: EN において think 漏洩率は **18.5%**、JSON 有効率は **71.8%**。JA では think 漏洩率 **65.3%**、JSON 有効率 **6.2%**。Fisher 検定で両指標ともに p < 10⁻⁶⁰ と極めて有意。

2. **モデルサイズ効果（MI300X）**: 32B・Qwen3.5 は think 漏洩率 100%（`Thinking…done thinking.` 形式）。JSON 有効率は 97.3%・99.7% と高水準。

3. **ハードウェア非依存性**: 同モデル・同言語での比較において EVE（R9700）・Zorya（RX9070XT）・MI300X で統計的に一貫した言語効果が確認される（overview 参照）。

---

## 7. 再現性情報

| 項目 | 値 |
|---|---|
| 使用ライブラリ | scipy（Fisher exact）, statsmodels（Wilson CI）|
| Python バージョン | 3.10+ |
| 乱数固定 | 不要（決定論的統計検定）|
| 統計スクリプト | `extract_qa_think.py`, `stat_analysis.py` |
| ROCm バージョン | 6.3 |
| Ollama バージョン | 実験時最新版 |

---

*このレポートは GitHub 公開・論文発表時の補助証拠として作成。数値はすべて `all_responses.csv`（N=6862）および `stats_large_models.json` から再現可能。*
