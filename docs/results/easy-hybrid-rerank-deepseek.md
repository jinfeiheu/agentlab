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
| avg_search_calls | 1.7826 |
| avg_correctness | 5.0000 |
| avg_faithfulness | 4.9259 |
| citation_support_rate | 1.0000 |
| avg_token_f1 | n/a |
| exact_match | n/a |
| context_precision | 0.8514 |
| context_recall | 0.9130 |
| citation_precision | 1.0000 |
| p50_latency_ms | 4390.7235 |
| p95_latency_ms | 6009.7297 |
| total_tokens | 61848 |
| total_cost | 0.1889 |

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
| avg_correctness | 5.0000 |
| avg_faithfulness | 4.9259 |
| citation_support_rate | 1.0000 |
| refusal_rate | 1.0000 |
| avg_token_f1 | n/a |
| exact_match | n/a |
| context_precision | 0.8514 |
| context_recall | 0.9130 |
| citation_precision | 1.0000 |
| tool_accuracy | 1.0000 |
| avg_search_calls | 1.7826 |
| p50_latency_ms | 4390.7235 |
| p95_latency_ms | 6009.7297 |
| total_tokens | 61848 |
| total_cost | 0.1889 |

### 按 category

| 指标 | unspecified |
|---|---:|
| count | 27 |
| task_success | 1.0000 |
| answerable_success | 1.0000 |
| avg_correctness | 5.0000 |
| avg_faithfulness | 4.9259 |
| citation_support_rate | 1.0000 |
| refusal_rate | 1.0000 |
| avg_token_f1 | n/a |
| exact_match | n/a |
| context_precision | 0.8514 |
| context_recall | 0.9130 |
| citation_precision | 1.0000 |
| tool_accuracy | 1.0000 |
| avg_search_calls | 1.7826 |
| p50_latency_ms | 4390.7235 |
| p95_latency_ms | 6009.7297 |
| total_tokens | 61848 |
| total_cost | 0.1889 |

## 逐题结果

| id | difficulty | category | answerable | task_success | tool_accuracy | refused | correctness | faithfulness | citation_support | token_f1 | citation_precision | latency_ms | error |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| q01 | easy | unspecified | True | True | True | False | 5 | 5 | True |  | 1.0000 | 14243.2 |  |
| q02 | easy | unspecified | True | True | True | False | 5 | 5 | True |  | 1.0000 | 2373.9 |  |
| q03 | easy | unspecified | True | True | True | False | 5 | 5 | True |  | 1.0000 | 5577.9 |  |
| q04 | easy | unspecified | True | True | True | False | 5 | 5 | True |  | 1.0000 | 2893.0 |  |
| q05 | easy | unspecified | True | True | True | False | 5 | 5 | True |  | 1.0000 | 3175.0 |  |
| q06 | easy | unspecified | True | True | True | False | 5 | 5 | True |  | 1.0000 | 2936.3 |  |
| q07 | easy | unspecified | True | True | True | False | 5 | 5 | True |  | 1.0000 | 4871.3 |  |
| q08 | easy | unspecified | True | True | True | False | 5 | 5 | True |  | 1.0000 | 5732.2 |  |
| q09 | easy | unspecified | True | True | True | False | 5 | 5 | True |  | 1.0000 | 3122.6 |  |
| q10 | easy | unspecified | True | True | True | False | 5 | 5 | True |  | 1.0000 | 4927.5 |  |
| q11 | easy | unspecified | True | True | True | False | 5 | 5 | True |  | 1.0000 | 6009.7 |  |
| q12 | easy | unspecified | True | True | True | False | 5 | 5 | True |  | 1.0000 | 4390.7 |  |
| q13 | easy | unspecified | True | True | True | False | 5 | 5 | True |  | 1.0000 | 4529.9 |  |
| q14 | easy | unspecified | True | True | True | False | 5 | 5 | True |  | 1.0000 | 4454.1 |  |
| q15 | easy | unspecified | True | True | True | False | 5 | 5 | True |  | 1.0000 | 3600.6 |  |
| q16 | easy | unspecified | True | True | True | False | 5 | 5 | True |  | 1.0000 | 4671.3 |  |
| q17 | easy | unspecified | True | True | True | False | 5 | 4 | True |  | 1.0000 | 5434.0 |  |
| q18 | easy | unspecified | True | True | True | False | 5 | 5 | True |  | 1.0000 | 3844.4 |  |
| q19 | easy | unspecified | True | True | True | False | 5 | 5 | True |  | 1.0000 | 4393.1 |  |
| q20 | easy | unspecified | True | True | True | False | 5 | 5 | True |  | 1.0000 | 5702.6 |  |
| q25 | easy | unspecified | True | True | True | False | 5 | 5 | True |  | 1.0000 | 4131.8 |  |
| q26 | easy | unspecified | True | True | True | False | 5 | 5 | True |  | 1.0000 | 5255.9 |  |
| q27 | easy | unspecified | True | True | True | False | 5 | 5 | True |  | 1.0000 | 3763.8 |  |
| q21 | easy | unspecified | False | True | False | True | 5 | 5 | False |  | 0.0000 | 1528.4 |  |
| q22 | easy | unspecified | False | True | False | True | 5 | 4 | False |  | 0.0000 | 1878.2 |  |
| q23 | easy | unspecified | False | True | True | True | 5 | 5 | True |  | 1.0000 | 2047.8 |  |
| q24 | easy | unspecified | False | True | True | True | 5 | 5 | False |  | 0.0000 | 2924.3 |  |
