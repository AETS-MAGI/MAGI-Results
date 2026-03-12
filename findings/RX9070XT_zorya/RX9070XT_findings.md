# RX9070XT Zorya — 統計所見レポート

> **対象ハードウェア**: AMD Radeon RX 9070 XT
> **ノード識別子**: `zorya`
> **実験日**: 2026-03-06 〜 2026-03-11
> **作成日**: 2026-03-11
> **目的**: DeepSeek-R1-Distill-Qwen-7B (q4_k_m) における think タグ漏洩・JSON 有効率の言語依存性検証（補完的サンプル）

---

## 1. データ概要

### 1.1 分析対象レコード数

| モデル | 温度 | 言語 | N |
|---|---|---|---|
| DeepSeek-R1-Distill-Qwen-7B (q4_k_m) | T=0.0 | EN | 11 |
| DeepSeek-R1-Distill-Qwen-7B (q4_k_m) | T=0.0 | JA | 10 |
| DeepSeek-R1-Distill-Qwen-7B (q4_k_m) | T=0.1 | EN | 117 |
| DeepSeek-R1-Distill-Qwen-7B (q4_k_m) | T=0.1 | JA | 112 |
| DeepSeek-R1-Distill-Qwen-7B (q4_k_m) | T=0.2 | EN | 11 |
| DeepSeek-R1-Distill-Qwen-7B (q4_k_m) | T=0.2 | JA | 11 |
| DeepSeek-R1-Distill-Qwen-7B (q4_k_m) | T=0.7 | EN | 11 |
| DeepSeek-R1-Distill-Qwen-7B (q4_k_m) | T=0.7 | JA | 11 |
| **Zorya 合計（全温度）** | | | **294** |

> **注意**: `stat_by_node.json` の Zorya 統計は **全温度を合算**した N_EN=206, N_JA=186 を使用。T=0 単独の n=11/10 はサンプルが少なすぎるため、温度合算値を主要結果として扱う。

### 1.2 主要分析対象

`stat_by_node.json` の Zorya エントリ（全温度, 7B モデル）：

```json
{
  "n_en": 206,
  "n_ja": 186,
  "think_leak": { "en": {...}, "ja": {...}, "OR": 0.0809, "p": 3.77e-29 },
  "json_valid": { "en": {...}, "ja": {...}, "OR": 21.18, "p": 8.95e-37 }
}
```

---

## 2. 統計手法

### 2.1 Wilson 95% 信頼区間

比率 $\hat{p} = k/n$ に対する Wilson スコア区間：

$$
\mathrm{CI}_{95\%} = \left[
\frac{\hat{p} + \frac{z^2}{2n} \pm z\sqrt{\frac{\hat{p}(1-\hat{p})}{n} + \frac{z^2}{4n^2}}}{1 + \frac{z^2}{n}}
\right], \quad z = 1.959964
$$

### 2.2 Fisher 正確検定（両側）

$$
\mathrm{OR} = \frac{ad}{bc}, \quad \text{p: hypergeometric exact, two-sided}
$$

---

## 3. 主要実験結果（全温度合算, 7B）

### 3.1 Think 漏洩率

| 言語 | N | 漏洩数 | 漏洩率 | Wilson 95% CI |
|---|---|---|---|---|
| EN | 206 | 38 | **18.4%** | [13.7%, 24.3%] |
| JA | 186 | 137 | **73.7%** | [66.9%, 79.5%] |

### 3.2 JSON 有効率

| 言語 | N | 有効数 | 有効率 | Wilson 95% CI |
|---|---|---|---|---|
| EN | 206 | 148 | **71.8%** | [65.3%, 77.5%] |
| JA | 186 | 20 | **10.8%** | [7.1%, 16.0%] |

### 3.3 正答率（strip_correct, gold_answer 付き）

全温度合算（7B）：

| 言語 | N | 正答数 | 正答率 | Wilson 95% CI |
|---|---|---|---|---|
| EN | 206 | 33 | **16.0%** | [11.6%, 21.6%] |
| JA | 186 | 5 | **2.7%** | [1.2%, 6.1%] |

### 3.4 Fisher 正確検定（EN vs JA, 全温度合算）

#### Think 漏洩率

分割表：

$$
\begin{pmatrix}
38 & 168 \\
137 & 49
\end{pmatrix}
$$

$$
\mathrm{OR} = \frac{38 \times 49}{168 \times 137} = 0.0809, \quad p = 3.77 \times 10^{-29}
$$

EN の think 漏洩オッズは JA の **約 1/12**。

#### JSON 有効率

分割表：

$$
\begin{pmatrix}
148 & 58 \\
20 & 166
\end{pmatrix}
$$

$$
\mathrm{OR} = \frac{148 \times 166}{58 \times 20} = 21.18, \quad p = 8.95 \times 10^{-37}
$$

EN の JSON 有効オッズは JA の **約 21.2 倍**。

---

## 4. 温度別詳細（参考）

Zorya は T=0.1 が最大サンプルであり、それ以外は参考値。

| T | 言語 | N | TL率 | JV率 |
|---|---|---|---|---|
| 0.0 | EN | 11 | 0.0% | 90.9% |
| 0.0 | JA | 10 | 30.0% | 40.0% |
| 0.1 | EN | 117 | 16.2% | 68.4% |
| 0.1 | JA | 112 | 70.5% | 8.0% |
| 0.2 | EN | 11 | 0.0% | 100.0% |
| 0.2 | JA | 11 | 45.5% | 27.3% |
| 0.7 | EN | 11 | 9.1% | 72.7% |
| 0.7 | JA | 11 | 81.8% | 27.3% |

T=0.1 の EN/JA（117/112件）が Zorya の実質的な主要データ。T=0.1 のみで Fisher 検定を行うと：

#### T=0.1 のみ Fisher 検定

**Think 漏洩**:
$$
\begin{pmatrix} 19 & 98 \\ 79 & 33 \end{pmatrix}, \quad \mathrm{OR} = 0.081, \quad p \approx 10^{-22}
$$

**JSON 有効率**:
$$
\begin{pmatrix} 80 & 37 \\ 9 & 103 \end{pmatrix}, \quad \mathrm{OR} = 24.7, \quad p \approx 10^{-28}
$$

T=0.1 のみでも、EVE・MI300X と一致した言語効果が確認される。

---

## 5. サンプルサイズに関する注意

Zorya は全3ノード中最小のサンプルサイズ（N=294）であり、CI 幅が他ノードに比べて広い。ただし p < 10⁻²⁹ という十分な統計的証拠があり、言語効果の有意性は確認できる。

EVE（N=3,945）との比較において、点推定値（TL: EN≈18–19%, JA≈74–76%; JV: EN≈71–72%, JA≈9–11%）は3ノード間で一致しており、ハードウェア非依存性を支持する。

---

## 6. 主要所見サマリー

1. **言語効果（Zorya, N=392）**: Think 漏洩率は EN 18.4% vs JA 73.7%（OR=0.0809, p=3.77×10⁻²⁹）。JSON 有効率は EN 71.8% vs JA 10.8%（OR=21.18, p=8.95×10⁻³⁷）。EVE・MI300X と整合的な言語効果。

2. **正答率**: EN 16.0%（CI: 11.6–21.6%）、JA 2.7%（CI: 1.2–6.1%）。EVE の値（15.3%/2.4%）と統計的に区別できない範囲内。

3. **サンプルサイズ制限**: Zorya のデータは主に T=0.1 での実験データであり、T=0 単独では n=11/10 と非常に少ない。主要検定には全温度合算値を使用。

---

## 7. 再現性情報

| 項目 | 値 |
|---|---|
| ハードウェア | AMD Radeon RX 9070 XT |
| OS | ROCm 対応 Linux |
| 統計ライブラリ | scipy.stats.fisher_exact, statsmodels.stats.proportion.proportion_confint |
| スクリプト | `extract_qa_think.py`, `stat_analysis.py` |

---

*このレポートは GitHub 公開・論文発表時の補助証拠として作成。数値はすべて `all_responses.csv`（N=6862）および `stat_by_node.json` から再現可能。*
