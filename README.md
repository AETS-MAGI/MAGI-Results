# MAGI Evidence Dataset

*Evidence artifacts for reproducible Japanese LLM evaluation*

このリポジトリは、LLM評価の再現性を検証するための基盤「MAGI (Managed Artifact Generation and Integrity)」を用いて収集された、**LLM評価の証拠データ（artifacts）**を公開するものです。

2026年 IEICE総合大会（九州産業大学）で発表した研究 **「日本語LLM評価のための再現可能な検証基盤設計」** における実験結果一式を格納しています。

---

## データセットの構成

本リポジトリは、単なる評価スコアだけでなく、評価の過程で生成された生データ（推論結果、環境情報、実行仕様）を網羅しています。

### 1. artifacts/ (生データ)

実験ごとに生成された証拠データを環境別に格納しています。各実験ディレクトリ（run_id）には、`spec.json`（実験設定）、`env.json`（ハードウェア/OS情報）、およびモデルの全出力が含まれます。

- **`artifacts_python/`**: ローカルのAMD ROCm環境（R9700 AI Pro, RX9070XT）で実施した計100+回の実行結果。
- **`artifacts_python-MI300X/`**: クラウド環境（RunPod MI300X）で実施した実行結果。

### 2. results/ (集計データ)

`artifacts/` 配下の膨大な生データを集計・加工した中間データです。

- **`agg_py_mi300x/`**: MI300X環境での日本語/英語プロンプト比較実験をパース・集計した結果（CSV/JSON形式）。

### 3. datasets/ (評価用タスク)

実験に使用したデータセット（設問セット）です。

- **`jp_en_100_temp_sweep/`**: 言語依存性・温度依存性を検証するための日本語/英語100問ペアセット。
- **`jp_en_10_fix/`**: 少数の特定課題を用いた検証セット。

### 4. analysis-scripts/ (解析スクリプト)

論文およびスライドに記載された統計解析・グラフ生成に使用したコードです。

- **`stats_py_mi300x.R`**: R言語による統計解析と可視化。
- **`stats_py_mi300x.py` / `aggregate_py_mi300x.py`**: Pythonによるデータクレンジングと基本集計。

### 5. findings/ (知見と可視化)

解析の結果得られた主要なプロット図や、ハードウェアごとの特筆すべき観察事項をまとめています。

- **`MI300X_RunPod/`**, **`R9700_AI_Pro_eve/`**, **`RX9070XT_zorya/`**: 各ハードウェア環境での出力傾向の比較。

---

## データの利用方法

各実験の詳細は、`artifacts/` 配下の `result.json`（または `tasks.json` / `responses.jsonl`）を参照してください。

```json
{
  "run_id": "20260306-015239-a59605a0",
  "spec": { "model_id": "deepseek-r1-...", "temperature": 0.1, ... },
  "env": { "gpu": "AMD Radeon RX 9070 XT", "rocm": "6.3.0", ... },
  "responses": [ ... ]
}
```

これらのデータを `analysis-scripts/` のコードで処理することで、論文中の統計結果を再現することが可能です。

---

## 関連リポジトリ

- [MAGI-oss_python](https://github.com/limonene/MAGI-oss_python): Control Plane および推論Runnerの実装。

---

## 引用

本データセットを利用する場合は、以下の論文を引用してください。

> 伊藤 ほか, "日本語LLM評価のための再現可能な検証基盤設計," 2026年電子情報通信学会総合大会, 2026.