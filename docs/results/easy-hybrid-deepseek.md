# RAG 评测报告

## 配置

| 项 | 值 |
|---|---|
| corpus | easy |
| judge_model | deepseek-flash |
| closed_book | False |

## 汇总

### 生成

| 指标 | 值 |
|---|---:|
| count | 27 |
| task_success | 0.9630 |
| answerable_success | 1.0000 |
| tool_accuracy | 1.0000 |
| refusal_rate | 1.0000 |
| avg_search_calls | 1.8261 |
| avg_correctness | 4.9259 |
| avg_faithfulness | 4.9630 |
| citation_support_rate | 0.9565 |
| avg_token_f1 | n/a |
| exact_match | n/a |
| context_precision | 0.8514 |
| context_recall | 0.9130 |
| citation_precision | 0.9565 |
| p50_latency_ms | 2985.4633 |
| p95_latency_ms | 4890.7162 |
| total_tokens | 60934 |
| total_cost | 0.1858 |

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
| task_success | 0.9630 |
| answerable_success | 1.0000 |
| avg_correctness | 4.9259 |
| avg_faithfulness | 4.9630 |
| citation_support_rate | 0.9565 |
| refusal_rate | 1.0000 |
| avg_token_f1 | n/a |
| exact_match | n/a |
| context_precision | 0.8514 |
| context_recall | 0.9130 |
| citation_precision | 0.9565 |
| tool_accuracy | 1.0000 |
| avg_search_calls | 1.8261 |
| p50_latency_ms | 2985.4633 |
| p95_latency_ms | 4890.7162 |
| total_tokens | 60934 |
| total_cost | 0.1858 |

### 按 category

| 指标 | unspecified |
|---|---:|
| count | 27 |
| task_success | 0.9630 |
| answerable_success | 1.0000 |
| avg_correctness | 4.9259 |
| avg_faithfulness | 4.9630 |
| citation_support_rate | 0.9565 |
| refusal_rate | 1.0000 |
| avg_token_f1 | n/a |
| exact_match | n/a |
| context_precision | 0.8514 |
| context_recall | 0.9130 |
| citation_precision | 0.9565 |
| tool_accuracy | 1.0000 |
| avg_search_calls | 1.8261 |
| p50_latency_ms | 2985.4633 |
| p95_latency_ms | 4890.7162 |
| total_tokens | 60934 |
| total_cost | 0.1858 |

## 逐题结果

| id | difficulty | category | answerable | task_success | tool_accuracy | refused | correctness | faithfulness | citation_support | token_f1 | citation_precision | latency_ms | error |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| q01 | easy | unspecified | True | True | True | False | 5 | 5 | True |  | 1.0000 | 4215.4 |  |
| q02 | easy | unspecified | True | False | True | False | 5 | 5 | False |  | 1.0000 | 2324.8 |  |
| q03 | easy | unspecified | True | True | True | False | 5 | 5 | True |  | 1.0000 | 4204.6 |  |
| q04 | easy | unspecified | True | True | True | False | 5 | 5 | True |  | 1.0000 | 2832.9 |  |
| q05 | easy | unspecified | True | True | True | False | 5 | 5 | True |  | 0.0000 | 2285.5 |  |
| q06 | easy | unspecified | True | True | True | False | 5 | 5 | True |  | 1.0000 | 2359.2 |  |
| q07 | easy | unspecified | True | True | True | False | 5 | 5 | True |  | 1.0000 | 3296.4 |  |
| q08 | easy | unspecified | True | True | True | False | 5 | 5 | True |  | 1.0000 | 3722.1 |  |
| q09 | easy | unspecified | True | True | True | False | 5 | 5 | True |  | 1.0000 | 2781.5 |  |
| q10 | easy | unspecified | True | True | True | False | 5 | 5 | True |  | 1.0000 | 4452.1 |  |
| q11 | easy | unspecified | True | True | True | False | 5 | 5 | True |  | 1.0000 | 4890.7 |  |
| q12 | easy | unspecified | True | True | True | False | 5 | 5 | True |  | 1.0000 | 2214.9 |  |
| q13 | easy | unspecified | True | True | True | False | 5 | 5 | True |  | 1.0000 | 3343.1 |  |
| q14 | easy | unspecified | True | True | True | False | 4 | 5 | True |  | 1.0000 | 3717.7 |  |
| q15 | easy | unspecified | True | True | True | False | 5 | 5 | True |  | 1.0000 | 1890.2 |  |
| q16 | easy | unspecified | True | True | True | False | 5 | 5 | True |  | 1.0000 | 3748.6 |  |
| q17 | easy | unspecified | True | True | True | False | 4 | 5 | True |  | 1.0000 | 5471.4 |  |
| q18 | easy | unspecified | True | True | True | False | 5 | 5 | True |  | 1.0000 | 3369.2 |  |
| q19 | easy | unspecified | True | True | True | False | 5 | 5 | True |  | 1.0000 | 2985.5 |  |
| q20 | easy | unspecified | True | True | True | False | 5 | 5 | True |  | 1.0000 | 3817.8 |  |
| q25 | easy | unspecified | True | True | True | False | 5 | 5 | True |  | 1.0000 | 4707.5 |  |
| q26 | easy | unspecified | True | True | True | False | 5 | 5 | True |  | 1.0000 | 2315.2 |  |
| q27 | easy | unspecified | True | True | True | False | 5 | 5 | True |  | 1.0000 | 2457.8 |  |
| q21 | easy | unspecified | False | True | False | True | 5 | 5 | False |  | 0.0000 | 1375.5 |  |
| q22 | easy | unspecified | False | True | False | True | 5 | 4 | False |  | 0.0000 | 2085.7 |  |
| q23 | easy | unspecified | False | True | True | True | 5 | 5 | True |  | 1.0000 | 2310.3 |  |
| q24 | easy | unspecified | False | True | True | True | 5 | 5 | False |  | 0.0000 | 2693.2 |  |
