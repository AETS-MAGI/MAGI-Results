# 全体横断比較 — 統計所見レポート（Overview）

> **対象**: DeepSeek-R1 ファミリー × 3 ノード（EVE / Zorya / MI300X）
> **総レコード数**: N = 6,862
> **作成日**: 2026-03-11
> **目的**: 言語依存性・ハードウェア依存性・モデルサイズ依存性の統合的検証

---

## 1. 実験全体の設計概要

### 1.1 ノード構成

| ノード名 | ハードウェア | 総レコード数 | 主要モデル |
|---|---|---|---|
| `eve` | AMD Radeon RX 9700 AI Pro | 3,999 | 7B (q4_k_m) |
| `runpod-mi300x` | AMD Instinct MI300X（RunPod）| 2,198 | 7B (q4_k_m), 32B, Qwen3.5-9B |
| `zorya` | AMD Radeon RX 9070 XT | 665 | 7B (q4_k_m) |
| **合計** | | **6,862** | |

### 1.2 モデル・温度構成

| モデル識別子 | 略称 | 温度 | 言語 |
|---|---|---|---|
| `deepseek-r1-distill-qwen-7b-q4_k_m-t0p0:latest` | 7B T=0 | 0.0 | EN / JA |
| `deepseek-r1-distill-qwen-7b-q4_k_m-t0p1:latest` | 7B T=0.1 | 0.1 | EN / JA |
| `deepseek-r1-distill-qwen-7b-q4_k_m-t0p2:latest` | 7B T=0.2 | 0.2 | EN / JA |
| `deepseek-r1-distill-qwen-7b-q4_k_m-t0p7:latest` | 7B T=0.7 | 0.7 | EN / JA |
| `deepseek-r1:32b` | 32B | 0.0 | JA のみ |
| `qwen3.5:9b` | Qwen3.5-9B | 0.0 | JA のみ |

### 1.3 データセット

- 英語問題：100問（歴史・科学・一般知識系 4択）
- 日本語問題：95〜100問（同上の翻訳版）
- gold_canonical_answer：A/B/C/D（分布偏り: B=52%, C=27%, A=19%, D=2%）

---

## 2. 統計手法

### 2.1 Wilson 95% 信頼区間（比率推定）

$$
\mathrm{CI}_{95\%} = \left[
\frac{\hat{p} + \frac{z^2}{2n} \pm z\sqrt{\frac{\hat{p}(1-\hat{p})}{n} + \frac{z^2}{4n^2}}}{1 + \frac{z^2}{n}}
\right], \quad z = 1.959964, \quad \hat{p} = \frac{k}{n}
$$

### 2.2 Fisher 正確検定（両側）

EN vs JA の 2×2 分割表でオッズ比を算出：

$$
\mathrm{OR} = \frac{ad}{bc}
$$

$\mathrm{OR} < 1$ は「EN において陽性率が低い」ことを意味する。p 値は hypergeometric 分布に基づく。

### 2.3 Think タグ検出（3パターン）

| パターン | 形式 | 該当モデル |
|---|---|---|
| 1 | `<think>...</think>` | 7B (DeepSeek-R1-Distill) |
| 2 | `<thinking>...</thinking>` | レア亜種（一部 7B run）|
| 3 | `Thinking...\n...\n...done thinking.` | 32B, Qwen3.5-9B |

---

## 3. 主要結果①：言語効果の検証（7B, T=0）

### 3.1 Think 漏洩率の比較（ノード別）

| ノード | N (EN) | TL(EN) | Wilson CI | N (JA) | TL(JA) | Wilson CI |
|---|---|---|---|---|---|---|
| EVE | 2,091 | **19.1%** | [17.5, 20.8] | 1,854 | **75.9%** | [73.9, 77.8] |
| Zorya* | 206 | **18.4%** | [13.7, 24.3] | 186 | **73.7%** | [66.9, 79.5] |
| MI300X | 737 | **18.5%** | [15.8, 21.4] | 502 | **65.3%** | [61.1, 69.4] |

> \* Zorya は全温度合算。`stat_by_node.json` 収録値。

**全ノード合算（7B T=0）**: EN: N=3,133, TL=18.9% CI[17.6,20.3]; JA: N=2,630, TL=73.7% CI[72.0,75.4]

### 3.2 JSON 有効率の比較（ノード別）

| ノード | N (EN) | JV(EN) | Wilson CI | N (JA) | JV(JA) | Wilson CI |
|---|---|---|---|---|---|---|
| EVE | 2,091 | **70.9%** | [68.9, 72.8] | 1,854 | **9.4%** | [8.1, 10.8] |
| Zorya* | 206 | **71.8%** | [65.3, 77.5] | 186 | **10.8%** | [7.1, 16.0] |
| MI300X | 737 | **71.8%** | [68.4, 74.9] | 502 | **6.2%** | [4.4, 8.6] |

### 3.3 Fisher 正確検定まとめ（EN vs JA, think 漏洩）

| ノード | 分割表 [a,b;c,d] | OR | p 値 |
|---|---|---|---|
| EVE | [399,1692; 1407,447] | 0.0749 | 4.10 × 10⁻²⁹⁶ |
| Zorya | [38,168; 137,49] | 0.0809 | 3.77 × 10⁻²⁹ |
| MI300X | [136,601; 328,174] | 0.1200 | 7.53 × 10⁻⁶⁴ |

### 3.4 Fisher 正確検定まとめ（EN vs JA, JSON 有効率）

| ノード | 分割表 [a,b;c,d] | OR | p 値 |
|---|---|---|---|
| EVE | [1482,609; 174,1680] | 23.50 | ≪ 10⁻³⁰⁰ |
| Zorya | [148,58; 20,166] | 21.18 | 8.95 × 10⁻³⁷ |
| MI300X | [529,208; 31,471] | 38.64 | 3.84 × 10⁻¹³¹ |

### 3.5 ハードウェア非依存性の評価

同一モデル（7B q4_k_m, T=0）で3ノードの点推定値を比較：

- Think 漏洩 EN: EVE 19.1%、Zorya 18.4%、MI300X 18.5% → **1%以内の一致**
- Think 漏洩 JA: EVE 75.9%、Zorya 73.7%、MI300X 65.3% → MI300X がやや低い（差約10ポイント）
- JSON 有効 EN: EVE 70.9%、Zorya 71.8%、MI300X 71.8% → **1%以内の一致**
- JSON 有効 JA: EVE 9.4%、Zorya 10.8%、MI300X 6.2% → 概ね一致（差 ≤ 5ポイント）

JA の think 漏洩率で MI300X（65.3%）がやや低いが、すべての ORは0.07–0.12 の範囲に収まり、**言語効果の方向性はハードウェアに非依存**と結論できる。

---

## 4. 主要結果②：モデルサイズ効果（MI300X 上）

### 4.1 Think 漏洩率・JSON 有効率

| モデル | N | 言語 | Think 漏洩率 | JSON 有効率 |
|---|---|---|---|---|
| 7B (q4_k_m, T=0) | 737 | EN | 18.5% | 71.8% |
| 7B (q4_k_m, T=0) | 502 | JA | 65.3% | 6.2% |
| DeepSeek-R1:32B (T=0) | 600 | JA | **100.0%** | **97.3%** |
| Qwen3.5:9B (T=0) | 359 | JA | **100.0%** | **99.7%** |

### 4.2 モデルサイズ効果の解釈

| 観点 | 7B | 32B / Qwen3.5-9B |
|---|---|---|
| Think 漏洩形式 | `<think>...</think>` タグ（一部隠せる）| `Thinking...done thinking.` 常に外部出力 |
| Think 漏洩率 | 言語依存（EN≈19%, JA≈65%） | 100%（形式として固定）|
| JSON 有効率 | 言語依存（EN≈72%, JA≈6%） | 97–100%（言語非依存）|
| 正答率 | 評価可能（EN≈16-21%）| 評価不可（gold_answer なし）|

**大きな示唆**: モデルが大きいほど think が「形式的に外部化される」が、それがユーザー・アプリケーションへの意図しない情報漏洩になることは変わらない。ただし大型モデルは指示遵守（JSON フォーマット）が格段に向上している。

---

## 5. 主要結果③：正答率の概観

### 5.1 7B モデル（T=0, gold_answer 付き）

| ノード | EN 正答率 | CI (95%) | JA 正答率 | CI (95%) |
|---|---|---|---|---|
| EVE | 15.3% | [13.8, 16.9] | 2.4% | [1.8, 3.2] |
| Zorya | 16.0% | [11.6, 21.6] | 2.7% | [1.2, 6.1] |
| MI300X | 20.6% | [17.9, 23.7] | 1.6% | [0.8, 3.1] |

> **注意事項**: ランダム正答率は 25%（均等4択）。gold_answer の偏りを考慮すると B 全選択で EN 52%。現在の正答率（15–21%）は JSON 出力に成功した件数（EN 72%）よりも低く、**JSON 出力に成功しても正解するとは限らない**ことを示す。

### 5.2 JA の正答率が極めて低い原因

JA の正答率 1.6–2.7% の内訳：
1. JSON 出力失敗（JA JV率 6–11%）による採点不能が大半
2. JSON 出力成功例でも正解に至るケースが少ない

これは JA においてモデルが JSON 形式に従わない（直接日本語で回答する）という**指示遵守の言語依存性**が主因と考えられる。

---

## 6. データ品質・制限事項の一覧

| 問題 | 件数 | 影響 | 対処 |
|---|---|---|---|
| Truncated think 出力（`</think>` なし）| 58件 | 偽陰性（think_leak 過小推定）| 影響軽微、記録のみ |
| JSON 抽出失敗（JA の直接回答型）| 約3,286件 | JA JV率の低下 | 研究知見として記録 |
| 32B/Qwen3.5 gold_answer なし | 959件 | 正答率評価不可 | JA 10問×繰り返し設計のため |
| Zorya T=0 のサンプル不足 | 各 n=10–11 | 単温度での検定困難 | 全温度合算で対処 |
| gold_answer 分布偏り | B=52% | 正答率の解釈に注意 | 偏り補正は未実施 |

---

## 7. 主要所見の統合

### 発見①：言語効果はハードウェア非依存

**EN ≈ 19% / JA ≈ 70% の think 漏洩率差**は EVE・Zorya・MI300X の3ノードすべてで一貫して観測された。Fisher 検定では OR=0.07–0.12（p < 10⁻²⁸）と極めて有意。これはモデル重みに内在する言語依存性であり、GPU 差（RDNA4 vs CDNA3）・ドライバ差（ROCm 環境差）に起因しない。

### 発見②：ラージモデルも think は必ず漏れる

32B / Qwen3.5-9B は `Thinking...done thinking.` 形式で思考プロセスを**常に出力**する。漏洩率 100% という意味ではなく、これが**そのモデルの正常な出力形式**である。システムプロンプトによる抑制を設計上考慮する必要がある。

### 発見③：JSON 有効率と正答率の解離

EN の JSON 有効率（~72%）と正答率（15–21%）の乖離は、**JSON 形式には従えていても内容が正しくない**ことを示す。4択問題においてモデルが正解を選べていない。JA ではさらに JSON 遵守率自体が低く（6–11%）、評価のボトルネックとなっている。

---

## 8. スライド対応数値（公開版）

IEICE 発表スライド `MI300X_results_slide.pptx` に使用した数値の対照表：

| 指標 | スライド表示値 | ソース |
|---|---|---|
| EVE(en) Think漏れ率 | 19.1% | stat_by_node.json |
| EVE(ja) Think漏れ率 | 75.9% | stat_by_node.json |
| Zorya(en) Think漏れ率 | 18.4% | stat_by_node.json |
| Zorya(ja) Think漏れ率 | 73.7% | stat_by_node.json |
| MI300X(en) Think漏れ率 | 18.5% | stat_by_node.json |
| MI300X(ja) Think漏れ率 | 65.3% | stat_by_node.json |
| EVE(en) JSON有効率 | 70.9% | stat_by_node.json |
| EVE(ja) JSON有効率 | 9.4% | stat_by_node.json |
| Zorya(en) JSON有効率 | 71.8% | stat_by_node.json |
| Zorya(ja) JSON有効率 | 10.8% | stat_by_node.json |
| MI300X(en) JSON有効率 | 71.8% | stat_by_node.json |
| MI300X(ja) JSON有効率 | 6.2% | stat_by_node.json |
| 32B Think漏れ率 | 100% | stats_large_models.json |
| Qwen3.5-9B Think漏れ率 | 100% | stats_large_models.json |
| 32B JSON有効率 | 97.3% | stats_large_models.json |
| Qwen3.5-9B JSON有効率 | 99.7% | stats_large_models.json |

フッター統計（Fisher OR・p値）：

```
Wilson 95% CI | Fisher exact (two-sided)
Think漏れ×lang (7B):
  EVE OR=0.075 / Zorya OR=0.081 / MI300X OR=0.120 (all p<0.001)
JSON×lang:
  EVE OR=23.5 / Zorya OR=21.2 / MI300X OR=38.6 (all p<0.001)
32B/Qwen3.5: think 100%漏出（Thinking…done thinking. 形式）
ROCm 6.3 / Ollama
```

---

## 9. 再現性情報

| 項目 | 値 |
|---|---|
| 総サンプル数 | N = 6,862 |
| 統計ライブラリ | scipy (Fisher exact), statsmodels (Wilson CI) |
| スクリプト | `extract_qa_think.py`, `stat_analysis.py` |
| 主要データファイル | `all_responses.csv`, `stat_by_node.json`, `stats_large_models.json` |
| Python | 3.10+ |
| ROCm | 6.3 |

---

*このレポートは GitHub 公開・IEICE 論文発表時の補助証拠として作成。全数値は `lab_note/data/artifacts/agg_py_mi300x/` 以下のファイルから再現可能。*
