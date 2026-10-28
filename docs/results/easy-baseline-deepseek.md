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
| task_success | 1.0000 |
| answerable_success | 1.0000 |
| tool_accuracy | 1.0000 |
| refusal_rate | 1.0000 |
| avg_search_calls | 1.8696 |
| avg_correctness | 5.0000 |
| avg_faithfulness | 5.0000 |
| citation_support_rate | 1.0000 |
| avg_token_f1 | n/a |
| exact_match | n/a |
| context_precision | 0.8188 |
| context_recall | 0.8696 |
| citation_precision | 1.0000 |
| p50_latency_ms | 3038.2222 |
| p95_latency_ms | 4723.3184 |
| total_tokens | 61963 |
| total_cost | 0.1879 |

### 检索

| 指标 | 值 |
|---|---:|
| count | 23 |
| recall@3 | 0.8696 |
| mrr | 0.8188 |
| ndcg@3 | 0.8081 |
| context_precision | 0.8188 |
| context_recall | 0.8696 |

## 分层结果

### 按 difficulty

| 指标 | easy |
|---|---:|
| count | 27 |
| task_success | 1.0000 |
| answerable_success | 1.0000 |
| avg_correctness | 5.0000 |
| avg_faithfulness | 5.0000 |
| citation_support_rate | 1.0000 |
| refusal_rate | 1.0000 |
| avg_token_f1 | n/a |
| exact_match | n/a |
| context_precision | 0.8188 |
| context_recall | 0.8696 |
| citation_precision | 1.0000 |
| tool_accuracy | 1.0000 |
| avg_search_calls | 1.8696 |
| p50_latency_ms | 3038.2222 |
| p95_latency_ms | 4723.3184 |
| total_tokens | 61963 |
| total_cost | 0.1879 |

### 按 category

| 指标 | unspecified |
|---|---:|
| count | 27 |
| task_success | 1.0000 |
| answerable_success | 1.0000 |
| avg_correctness | 5.0000 |
| avg_faithfulness | 5.0000 |
| citation_support_rate | 1.0000 |
| refusal_rate | 1.0000 |
| avg_token_f1 | n/a |
| exact_match | n/a |
| context_precision | 0.8188 |
| context_recall | 0.8696 |
| citation_precision | 1.0000 |
| tool_accuracy | 1.0000 |
| avg_search_calls | 1.8696 |
| p50_latency_ms | 3038.2222 |
| p95_latency_ms | 4723.3184 |
| total_tokens | 61963 |
| total_cost | 0.1879 |

## 逐题结果

| id | difficulty | category | answerable | task_success | tool_accuracy | refused | correctness | faithfulness | citation_support | token_f1 | citation_precision | latency_ms | error |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| q01 | easy | unspecified | True | True | True | False | 5 | 5 | True |  | 1.0000 | 4723.3 |  |
| q02 | easy | unspecified | True | True | True | False | 5 | 5 | True |  | 1.0000 | 2204.7 |  |
| q03 | easy | unspecified | True | True | True | False | 5 | 5 | True |  | 1.0000 | 4686.1 |  |
| q04 | easy | unspecified | True | True | True | False | 5 | 5 | True |  | 1.0000 | 1994.5 |  |
| q05 | easy | unspecified | True | True | True | False | 5 | 5 | True |  | 1.0000 | 1764.4 |  |
| q06 | easy | unspecified | True | True | True | False | 5 | 5 | True |  | 1.0000 | 2054.0 |  |
| q07 | easy | unspecified | True | True | True | False | 5 | 5 | True |  | 1.0000 | 2820.6 |  |
| q08 | easy | unspecified | True | True | True | False | 5 | 5 | True |  | 1.0000 | 3514.1 |  |
| q09 | easy | unspecified | True | True | True | False | 5 | 5 | True |  | 1.0000 | 3419.9 |  |
| q10 | easy | unspecified | True | True | True | False | 5 | 5 | True |  | 1.0000 | 3126.4 |  |
| q11 | easy | unspecified | True | True | True | False | 5 | 5 | True |  | 1.0000 | 3497.7 |  |
| q12 | easy | unspecified | True | True | True | False | 5 | 5 | True |  | 1.0000 | 2889.8 |  |
| q13 | easy | unspecified | True | True | True | False | 5 | 5 | True |  | 1.0000 | 2660.1 |  |
| q14 | easy | unspecified | True | True | True | False | 5 | 5 | True |  | 1.0000 | 3157.8 |  |
| q15 | easy | unspecified | True | True | True | False | 5 | 5 | True |  | 1.0000 | 2690.2 |  |
| q16 | easy | unspecified | True | True | True | False | 5 | 5 | True |  | 1.0000 | 3153.4 |  |
| q17 | easy | unspecified | True | True | True | False | 5 | 5 | True |  | 1.0000 | 4922.1 |  |
| q18 | easy | unspecified | True | True | True | False | 5 | 5 | True |  | 1.0000 | 3109.5 |  |
| q19 | easy | unspecified | True | True | True | False | 5 | 5 | True |  | 1.0000 | 3044.2 |  |
| q20 | easy | unspecified | True | True | True | False | 5 | 5 | True |  | 1.0000 | 4226.6 |  |
| q25 | easy | unspecified | True | True | True | False | 5 | 5 | True |  | 1.0000 | 3123.5 |  |
| q26 | easy | unspecified | True | True | True | False | 5 | 5 | True |  | 1.0000 | 3038.2 |  |
| q27 | easy | unspecified | True | True | True | False | 5 | 5 | True |  | 1.0000 | 2370.6 |  |
| q21 | easy | unspecified | False | True | False | True | 5 | 5 | False |  | 0.0000 | 1513.1 |  |
| q22 | easy | unspecified | False | True | False | True | 5 | 5 | False |  | 0.0000 | 1827.7 |  |
| q23 | easy | unspecified | False | True | True | True | 5 | 5 | True |  | 1.0000 | 1342.5 |  |
| q24 | easy | unspecified | False | True | False | True | 5 | 5 | False |  | 0.0000 | 1896.1 |  |
