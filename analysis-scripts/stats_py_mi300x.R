#!/usr/bin/env Rscript
# stats_py_mi300x.R
# =================
# PythonランナーおよびMI300X実験の統計検定スクリプト
#
# 検定内容:
#   1) think漏れ率 ~ 言語 (Fisher exact)
#   2) JSON有効率 ~ 言語 (Fisher exact)
#   3) 正答率 ~ 言語 (Fisher exact, 7Bのみ)
#   4) 温度 × JSON有効率の相関 (Spearman, 言語別)
#   5) think漏れ率 ~ モデルサイズ (Fisher exact: 7B vs 32B)
#   6) 95% Wilson CI for all key rates
#
# 出力先: ../data/artifacts/agg_py_mi300x/
# ──────────────────────────────────────────────────────

suppressPackageStartupMessages({
  library(dplyr)
  library(readr)
  library(broom)
  library(jsonlite)
})

OUT_DIR <- "../data/artifacts/agg_py_mi300x"
dir.create(OUT_DIR, showWarnings = FALSE, recursive = TRUE)

# ── Wilson CI ─────────────────────────────────────────────
wilson_ci <- function(k, n, conf = 0.95) {
  z <- qnorm(1 - (1 - conf) / 2)
  p_hat <- k / n
  denom <- 1 + z^2 / n
  centre <- (p_hat + z^2 / (2*n)) / denom
  half <- z * sqrt(p_hat * (1 - p_hat) / n + z^2 / (4*n^2)) / denom
  list(rate = p_hat, low = max(0, centre - half), high = min(1, centre + half))
}

# ── データ読み込み ─────────────────────────────────────────
cat("== データ読み込み ==\n")
all_path <- file.path(OUT_DIR, "all_responses.csv")
df <- read_csv(all_path, col_types = cols(
  temperature     = col_double(),
  think_leaked    = col_logical(),
  raw_json_valid  = col_logical(),
  strip_json_valid = col_logical(),
  raw_correct     = col_logical(),
  strip_correct   = col_logical(),
  think_contains_gold = col_logical()
))
cat(sprintf("  rows: %d\n\n", nrow(df)))

# 7B のみ / 32B / Qwen に分離
df_7b   <- df %>% filter(grepl("7b", model_id, ignore.case = TRUE))
df_32b  <- df %>% filter(grepl("32b", model_id, ignore.case = TRUE))
df_qwen <- df %>% filter(grepl("qwen3", model_id, ignore.case = TRUE))

# en/ja に絞る（unknownを除外）
df_7b_enja <- df_7b %>% filter(lang %in% c("en", "ja"))

results <- list()

# ──────────────────────────────────────────────────────────
# 1) think漏れ率 ~ 言語 (Fisher exact, 7B)
# ──────────────────────────────────────────────────────────
cat("== 1) think漏れ率 ~ 言語 (Fisher exact, 7B) ==\n")
tab_think_lang <- with(df_7b_enja,
  table(lang = lang, think_leaked = think_leaked))
cat("  Contingency table:\n")
print(tab_think_lang)
ft1 <- fisher.test(tab_think_lang)
cat(sprintf("  Fisher exact: p = %.4e, OR = %.4f [%.4f, %.4f]\n\n",
  ft1$p.value, ft1$estimate, ft1$conf.int[1], ft1$conf.int[2]))
results$think_leak_vs_lang <- list(
  test = "fisher",
  p_value = ft1$p.value,
  OR = as.numeric(ft1$estimate),
  CI_lo = ft1$conf.int[1],
  CI_hi = ft1$conf.int[2]
)

# ──────────────────────────────────────────────────────────
# 2) JSON有効率 ~ 言語 (Fisher exact, 7B)
# ──────────────────────────────────────────────────────────
cat("== 2) JSON有効率 ~ 言語 (Fisher exact, 7B) ==\n")
tab_json_lang <- with(df_7b_enja,
  table(lang = lang, json_valid = raw_json_valid))
cat("  Contingency table:\n")
print(tab_json_lang)
ft2 <- fisher.test(tab_json_lang)
cat(sprintf("  Fisher exact: p = %.4e, OR = %.4f [%.4f, %.4f]\n\n",
  ft2$p.value, ft2$estimate, ft2$conf.int[1], ft2$conf.int[2]))
results$json_valid_vs_lang <- list(
  test = "fisher",
  p_value = ft2$p.value,
  OR = as.numeric(ft2$estimate),
  CI_lo = ft2$conf.int[1],
  CI_hi = ft2$conf.int[2]
)

# ──────────────────────────────────────────────────────────
# 3) 正答率 ~ 言語 (Fisher exact, 7B, gold_answerあり)
# ──────────────────────────────────────────────────────────
cat("== 3) 正答率 ~ 言語 (Fisher exact, 7B) ==\n")
df_7b_scored <- df_7b_enja %>% filter(!is.na(strip_correct))
if (nrow(df_7b_scored) > 0) {
  tab_acc_lang <- with(df_7b_scored,
    table(lang = lang, correct = strip_correct))
  cat("  Contingency table:\n")
  print(tab_acc_lang)
  ft3 <- fisher.test(tab_acc_lang)
  cat(sprintf("  Fisher exact: p = %.4e, OR = %.4f [%.4f, %.4f]\n\n",
    ft3$p.value, ft3$estimate, ft3$conf.int[1], ft3$conf.int[2]))
  results$accuracy_vs_lang <- list(
    test = "fisher",
    p_value = ft3$p.value,
    OR = as.numeric(ft3$estimate),
    CI_lo = ft3$conf.int[1],
    CI_hi = ft3$conf.int[2]
  )
} else {
  cat("  スコアリング可能データなし\n\n")
}

# ──────────────────────────────────────────────────────────
# 4) 温度 × JSON有効率の相関 (Spearman, 言語別, 7B)
# ──────────────────────────────────────────────────────────
cat("== 4) 温度 × JSON有効率 Spearman (7B, 言語別) ==\n")
temp_corr_rows <- list()
for (lng in c("en", "ja")) {
  sub <- df_7b_enja %>%
    filter(lang == lng, !is.na(temperature)) %>%
    mutate(json_valid_int = as.integer(raw_json_valid))
  if (nrow(sub) < 5) next
  sp <- cor.test(sub$temperature, sub$json_valid_int, method = "spearman")
  ci_w <- wilson_ci(sum(sub$raw_json_valid), nrow(sub))
  cat(sprintf("  lang=%s: rho = %.4f, p = %.4e, n = %d, json_valid_rate = %.3f [%.3f, %.3f]\n",
    lng, sp$estimate, sp$p.value, nrow(sub), ci_w$rate, ci_w$low, ci_w$high))
  temp_corr_rows[[lng]] <- list(
    lang = lng,
    n = nrow(sub),
    spearman_rho = as.numeric(sp$estimate),
    p_value = sp$p.value,
    json_valid_rate = ci_w$rate,
    json_valid_ci_lo = ci_w$low,
    json_valid_ci_hi = ci_w$high
  )
}
cat("\n")
results$temp_vs_json_spearman <- temp_corr_rows

# ──────────────────────────────────────────────────────────
# 5) think漏れ率 ~ モデルサイズ (Fisher exact: 7B vs 32B)
# ──────────────────────────────────────────────────────────
cat("== 5) think漏れ率 ~ モデルサイズ (7B vs 32B) ==\n")
df_size <- bind_rows(
  df_7b  %>% mutate(size = "7B"),
  df_32b %>% mutate(size = "32B")
)
if (nrow(df_size) > 0) {
  tab_size <- with(df_size, table(size = size, think_leaked = think_leaked))
  cat("  Contingency table:\n")
  print(tab_size)
  ft5 <- fisher.test(tab_size)
  cat(sprintf("  Fisher exact: p = %.4e, OR = %.4f [%.4f, %.4f]\n\n",
    ft5$p.value, ft5$estimate, ft5$conf.int[1], ft5$conf.int[2]))
  results$think_leak_vs_model_size <- list(
    test = "fisher",
    p_value = ft5$p.value,
    OR = as.numeric(ft5$estimate),
    CI_lo = ft5$conf.int[1],
    CI_hi = ft5$conf.int[2]
  )
}

# ──────────────────────────────────────────────────────────
# 6) 95% Wilson CI 一覧 (主要指標)
# ──────────────────────────────────────────────────────────
cat("== 6) 主要指標 95% Wilson CI ==\n")
ci_rows <- list()

make_ci_row <- function(label, sub, col) {
  k <- sum(sub[[col]], na.rm = TRUE)
  n <- sum(!is.na(sub[[col]]))
  if (n == 0) return(NULL)
  ci <- wilson_ci(k, n)
  cat(sprintf("  %-45s  n=%d  rate=%.4f [%.4f, %.4f]\n",
    label, n, ci$rate, ci$low, ci$high))
  list(label = label, n = n, k = k, rate = ci$rate,
       ci_lo = ci$low, ci_hi = ci$high)
}

ci_rows <- c(ci_rows, list(
  make_ci_row("7B en: think_leak",       df_7b_enja %>% filter(lang=="en"), "think_leaked"),
  make_ci_row("7B ja: think_leak",       df_7b_enja %>% filter(lang=="ja"), "think_leaked"),
  make_ci_row("7B en: json_valid",       df_7b_enja %>% filter(lang=="en"), "raw_json_valid"),
  make_ci_row("7B ja: json_valid",       df_7b_enja %>% filter(lang=="ja"), "raw_json_valid"),
  make_ci_row("7B en: strip_json_valid", df_7b_enja %>% filter(lang=="en"), "strip_json_valid"),
  make_ci_row("7B ja: strip_json_valid", df_7b_enja %>% filter(lang=="ja"), "strip_json_valid"),
  make_ci_row("7B en: accuracy",         df_7b_scored %>% filter(lang=="en"), "strip_correct"),
  make_ci_row("7B ja: accuracy",         df_7b_scored %>% filter(lang=="ja"), "strip_correct"),
  make_ci_row("32B: think_leak",         df_32b, "think_leaked"),
  make_ci_row("32B: json_valid",         df_32b, "raw_json_valid"),
  make_ci_row("Qwen3.5 9B: think_leak", df_qwen, "think_leaked"),
  make_ci_row("Qwen3.5 9B: json_valid", df_qwen, "raw_json_valid")
))
ci_rows <- Filter(Negate(is.null), ci_rows)

# CSV として書き出し
ci_df <- bind_rows(lapply(ci_rows, as.data.frame))
write_csv(ci_df, file.path(OUT_DIR, "wilson_ci_summary.csv"))
cat(sprintf("\n  → 保存: %s/wilson_ci_summary.csv\n\n", OUT_DIR))

# ── 検定結果を JSON で保存 ─────────────────────────────────
write_json(results, file.path(OUT_DIR, "stat_tests.json"),
           pretty = TRUE, auto_unbox = TRUE)
cat(sprintf("  → 保存: %s/stat_tests.json\n", OUT_DIR))

cat("\n[DONE]\n")
