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
| avg_search_calls | 1.8696 |
| avg_correctness | 4.6296 |
| avg_faithfulness | 5.0000 |
| citation_support_rate | 1.0000 |
| avg_token_f1 | n/a |
| exact_match | n/a |
| context_precision | 0.8514 |
| context_recall | 0.9130 |
| citation_precision | 1.0000 |
| p50_latency_ms | 4569.5216 |
| p95_latency_ms | 6708.7125 |
| total_tokens | 63010 |
| total_cost | 0.1906 |

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
| avg_correctness | 4.6296 |
| avg_faithfulness | 5.0000 |
| citation_support_rate | 1.0000 |
| refusal_rate | 1.0000 |
| avg_token_f1 | n/a |
| exact_match | n/a |
| context_precision | 0.8514 |
| context_recall | 0.9130 |
| citation_precision | 1.0000 |
| tool_accuracy | 1.0000 |
| avg_search_calls | 1.8696 |
| p50_latency_ms | 4569.5216 |
| p95_latency_ms | 6708.7125 |
| total_tokens | 63010 |
| total_cost | 0.1906 |

### 按 category

| 指标 | unspecified |
|---|---:|
| count | 27 |
| task_success | 1.0000 |
| answerable_success | 1.0000 |
| avg_correctness | 4.6296 |
| avg_faithfulness | 5.0000 |
| citation_support_rate | 1.0000 |
| refusal_rate | 1.0000 |
| avg_token_f1 | n/a |
| exact_match | n/a |
| context_precision | 0.8514 |
| context_recall | 0.9130 |
| citation_precision | 1.0000 |
| tool_accuracy | 1.0000 |
| avg_search_calls | 1.8696 |
| p50_latency_ms | 4569.5216 |
| p95_latency_ms | 6708.7125 |
| total_tokens | 63010 |
| total_cost | 0.1906 |

## 逐题结果

| id | difficulty | category | answerable | task_success | tool_accuracy | refused | correctness | faithfulness | citation_support | token_f1 | citation_precision | latency_ms | error |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| q01 | easy | unspecified | True | True | True | False | 5 | 5 | True |  | 1.0000 | 16803.7 |  |
| q02 | easy | unspecified | True | True | True | False | 5 | 5 | True |  | 1.0000 | 3437.7 |  |
| q03 | easy | unspecified | True | True | True | False | 5 | 5 | True |  | 1.0000 | 5749.2 |  |
| q04 | easy | unspecified | True | True | True | False | 5 | 5 | True |  | 1.0000 | 2275.8 |  |
| q05 | easy | unspecified | True | True | True | False | 5 | 5 | True |  | 1.0000 | 2183.8 |  |
| q06 | easy | unspecified | True | True | True | False | 5 | 5 | True |  | 1.0000 | 3264.9 |  |
| q07 | easy | unspecified | True | True | True | False | 5 | 5 | True |  | 1.0000 | 4536.5 |  |
| q08 | easy | unspecified | True | True | True | False | 5 | 5 | True |  | 1.0000 | 5613.5 |  |
| q09 | easy | unspecified | True | True | True | False | 5 | 5 | True |  | 1.0000 | 5246.8 |  |
| q10 | easy | unspecified | True | True | True | False | 5 | 5 | True |  | 1.0000 | 4812.5 |  |
| q11 | easy | unspecified | True | True | True | False | 4 | 5 | True |  | 1.0000 | 6098.1 |  |
| q12 | easy | unspecified | True | True | True | False | 5 | 5 | True |  | 1.0000 | 4440.1 |  |
| q13 | easy | unspecified | True | True | True | False | 5 | 5 | True |  | 1.0000 | 4670.1 |  |
| q14 | easy | unspecified | True | True | True | False | 5 | 5 | True |  | 1.0000 | 4943.7 |  |
| q15 | easy | unspecified | True | True | True | False | 5 | 5 | True |  | 1.0000 | 2860.7 |  |
| q16 | easy | unspecified | True | True | True | False | 5 | 5 | True |  | 1.0000 | 3772.6 |  |
| q17 | easy | unspecified | True | True | True | False | 5 | 5 | True |  | 1.0000 | 6708.7 |  |
| q18 | easy | unspecified | True | True | True | False | 5 | 5 | True |  | 1.0000 | 4949.3 |  |
| q19 | easy | unspecified | True | True | True | False | 5 | 5 | True |  | 1.0000 | 4569.5 |  |
| q20 | easy | unspecified | True | True | True | False | 5 | 5 | True |  | 1.0000 | 5834.1 |  |
| q25 | easy | unspecified | True | True | True | False | 5 | 5 | True |  | 1.0000 | 4224.6 |  |
| q26 | easy | unspecified | True | True | True | False | 5 | 5 | True |  | 1.0000 | 5116.4 |  |
| q27 | easy | unspecified | True | True | True | False | 5 | 5 | True |  | 1.0000 | 4605.5 |  |
| q21 | easy | unspecified | False | True | False | True | 1 | 5 | False |  | 0.0000 | 996.5 |  |
| q22 | easy | unspecified | False | True | False | True | 5 | 5 | False |  | 0.0000 | 2548.0 |  |
| q23 | easy | unspecified | False | True | True | True | 0 | 5 | True |  | 1.0000 | 3070.2 |  |
| q24 | easy | unspecified | False | True | False | True | 5 | 5 | False |  | 0.0000 | 2165.7 |  |
