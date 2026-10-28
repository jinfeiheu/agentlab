# RAG 评测报告

## 配置

| 项 | 值 |
|---|---|
| corpus | easy |
| judge_model | qwen3.5:4b |
| closed_book | False |

## 汇总

### 生成

| 指标 | 值 |
|---|---:|
| count | 27 |
| task_success | 1.0000 |
| answerable_success | 1.0000 |
| tool_accuracy | 1.0000 |
| refusal_rate | 1.0000 |
| avg_search_calls | 1.7826 |
| avg_correctness | 4.8148 |
| avg_faithfulness | 4.9630 |
| citation_support_rate | 1.0000 |
| avg_token_f1 | n/a |
| exact_match | n/a |
| context_precision | 0.8514 |
| context_recall | 0.9130 |
| citation_precision | 1.0000 |
| p50_latency_ms | 2849.6736 |
| p95_latency_ms | 4843.0394 |
| total_tokens | 61251 |
| total_cost | 0.1873 |

### 检索

| 指标 | 值 |
|---|---:|
| count | 23 |
| recall@3 | 0.9130 |
| mrr | 0.8623 |
| ndcg@3 | 0.8462 |
| context_precision | 0.8514 |
| context_recall | 0.9130 |

## 分层结果

### 按 difficulty

| 指标 | easy |
|---|---:|
| count | 27 |
| task_success | 1.0000 |
| answerable_success | 1.0000 |
| avg_correctness | 4.8148 |
| avg_faithfulness | 4.9630 |
| citation_support_rate | 1.0000 |
| refusal_rate | 1.0000 |
| avg_token_f1 | n/a |
| exact_match | n/a |
| context_precision | 0.8514 |
| context_recall | 0.9130 |
| citation_precision | 1.0000 |
| tool_accuracy | 1.0000 |
| avg_search_calls | 1.7826 |
| p50_latency_ms | 2849.6736 |
| p95_latency_ms | 4843.0394 |
| total_tokens | 61251 |
| total_cost | 0.1873 |

### 按 category

| 指标 | unspecified |
|---|---:|
| count | 27 |
| task_success | 1.0000 |
| answerable_success | 1.0000 |
| avg_correctness | 4.8148 |
| avg_faithfulness | 4.9630 |
| citation_support_rate | 1.0000 |
| refusal_rate | 1.0000 |
| avg_token_f1 | n/a |
| exact_match | n/a |
| context_precision | 0.8514 |
| context_recall | 0.9130 |
| citation_precision | 1.0000 |
| tool_accuracy | 1.0000 |
| avg_search_calls | 1.7826 |
| p50_latency_ms | 2849.6736 |
| p95_latency_ms | 4843.0394 |
| total_tokens | 61251 |
| total_cost | 0.1873 |

## 逐题结果

| id | difficulty | category | answerable | task_success | tool_accuracy | refused | correctness | faithfulness | citation_support | token_f1 | citation_precision | latency_ms | error |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| q01 | easy | unspecified | True | True | True | False | 5 | 5 | True |  | 1.0000 | 4843.0 |  |
| q02 | easy | unspecified | True | True | True | False | 5 | 5 | True |  | 1.0000 | 2537.4 |  |
| q03 | easy | unspecified | True | True | True | False | 5 | 5 | True |  | 1.0000 | 4480.3 |  |
| q04 | easy | unspecified | True | True | True | False | 5 | 5 | True |  | 1.0000 | 2272.0 |  |
| q05 | easy | unspecified | True | True | True | False | 5 | 5 | True |  | 1.0000 | 1755.0 |  |
| q06 | easy | unspecified | True | True | True | False | 5 | 5 | True |  | 1.0000 | 2299.1 |  |
| q07 | easy | unspecified | True | True | True | False | 5 | 5 | True |  | 1.0000 | 2811.1 |  |
| q08 | easy | unspecified | True | True | True | False | 5 | 5 | True |  | 1.0000 | 3910.7 |  |
| q09 | easy | unspecified | True | True | True | False | 5 | 5 | True |  | 1.0000 | 2383.6 |  |
| q10 | easy | unspecified | True | True | True | False | 5 | 5 | True |  | 1.0000 | 2766.6 |  |
| q11 | easy | unspecified | True | True | True | False | 5 | 5 | True |  | 1.0000 | 4262.8 |  |
| q12 | easy | unspecified | True | True | True | False | 5 | 5 | True |  | 1.0000 | 2028.4 |  |
| q13 | easy | unspecified | True | True | True | False | 5 | 5 | True |  | 1.0000 | 2909.6 |  |
| q14 | easy | unspecified | True | True | True | False | 5 | 4 | True |  | 1.0000 | 3402.0 |  |
| q15 | easy | unspecified | True | True | True | False | 5 | 5 | True |  | 1.0000 | 2849.7 |  |
| q16 | easy | unspecified | True | True | True | False | 5 | 5 | True |  | 1.0000 | 3657.7 |  |
| q17 | easy | unspecified | True | True | True | False | 5 | 5 | True |  | 1.0000 | 5357.7 |  |
| q18 | easy | unspecified | True | True | True | False | 5 | 5 | True |  | 1.0000 | 3096.9 |  |
| q19 | easy | unspecified | True | True | True | False | 5 | 5 | True |  | 1.0000 | 3560.2 |  |
| q20 | easy | unspecified | True | True | True | False | 5 | 5 | True |  | 1.0000 | 3698.4 |  |
| q25 | easy | unspecified | True | True | True | False | 5 | 5 | True |  | 1.0000 | 3583.5 |  |
| q26 | easy | unspecified | True | True | True | False | 5 | 5 | True |  | 1.0000 | 2681.5 |  |
| q27 | easy | unspecified | True | True | True | False | 5 | 5 | True |  | 1.0000 | 2505.9 |  |
| q21 | easy | unspecified | False | True | False | True | 5 | 5 | False |  | 0.0000 | 1731.8 |  |
| q22 | easy | unspecified | False | True | False | True | 5 | 5 | False |  | 0.0000 | 2476.9 |  |
| q23 | easy | unspecified | False | True | True | True | 0 | 5 | True |  | 1.0000 | 2458.6 |  |
| q24 | easy | unspecified | False | True | True | True | 5 | 5 | True |  | 1.0000 | 2898.8 |  |
