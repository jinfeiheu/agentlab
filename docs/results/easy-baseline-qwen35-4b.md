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
| task_success | 0.9630 |
| answerable_success | 0.9565 |
| tool_accuracy | 1.0000 |
| refusal_rate | 1.0000 |
| avg_search_calls | 1.7826 |
| avg_correctness | 4.5556 |
| avg_faithfulness | 5.0000 |
| citation_support_rate | 1.0000 |
| avg_token_f1 | n/a |
| exact_match | n/a |
| context_precision | 0.8188 |
| context_recall | 0.8696 |
| citation_precision | 1.0000 |
| p50_latency_ms | 3395.5615 |
| p95_latency_ms | 4667.4143 |
| total_tokens | 63097 |
| total_cost | 0.1933 |

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
| task_success | 0.9630 |
| answerable_success | 0.9565 |
| avg_correctness | 4.5556 |
| avg_faithfulness | 5.0000 |
| citation_support_rate | 1.0000 |
| refusal_rate | 1.0000 |
| avg_token_f1 | n/a |
| exact_match | n/a |
| context_precision | 0.8188 |
| context_recall | 0.8696 |
| citation_precision | 1.0000 |
| tool_accuracy | 1.0000 |
| avg_search_calls | 1.7826 |
| p50_latency_ms | 3395.5615 |
| p95_latency_ms | 4667.4143 |
| total_tokens | 63097 |
| total_cost | 0.1933 |

### 按 category

| 指标 | unspecified |
|---|---:|
| count | 27 |
| task_success | 0.9630 |
| answerable_success | 0.9565 |
| avg_correctness | 4.5556 |
| avg_faithfulness | 5.0000 |
| citation_support_rate | 1.0000 |
| refusal_rate | 1.0000 |
| avg_token_f1 | n/a |
| exact_match | n/a |
| context_precision | 0.8188 |
| context_recall | 0.8696 |
| citation_precision | 1.0000 |
| tool_accuracy | 1.0000 |
| avg_search_calls | 1.7826 |
| p50_latency_ms | 3395.5615 |
| p95_latency_ms | 4667.4143 |
| total_tokens | 63097 |
| total_cost | 0.1933 |

## 逐题结果

| id | difficulty | category | answerable | task_success | tool_accuracy | refused | correctness | faithfulness | citation_support | token_f1 | citation_precision | latency_ms | error |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| q01 | easy | unspecified | True | True | True | False | 5 | 5 | True |  | 1.0000 | 4233.1 |  |
| q02 | easy | unspecified | True | True | True | False | 5 | 5 | True |  | 1.0000 | 3883.0 |  |
| q03 | easy | unspecified | True | True | True | False | 5 | 5 | True |  | 1.0000 | 3972.5 |  |
| q04 | easy | unspecified | True | True | True | False | 5 | 5 | True |  | 1.0000 | 3335.9 |  |
| q05 | easy | unspecified | True | True | True | False | 5 | 5 | True |  | 1.0000 | 1704.9 |  |
| q06 | easy | unspecified | True | True | True | False | 5 | 5 | True |  | 1.0000 | 1784.4 |  |
| q07 | easy | unspecified | True | True | True | False | 5 | 5 | True |  | 1.0000 | 2953.8 |  |
| q08 | easy | unspecified | True | True | True | False | 5 | 5 | True |  | 1.0000 | 3921.1 |  |
| q09 | easy | unspecified | True | True | True | False | 5 | 5 | True |  | 1.0000 | 2412.1 |  |
| q10 | easy | unspecified | True | True | True | False | 5 | 5 | True |  | 1.0000 | 3559.8 |  |
| q11 | easy | unspecified | True | True | True | False | 5 | 5 | True |  | 1.0000 | 4887.1 |  |
| q12 | easy | unspecified | True | True | True | False | 5 | 5 | True |  | 1.0000 | 3115.2 |  |
| q13 | easy | unspecified | True | True | True | False | 5 | 5 | True |  | 1.0000 | 3050.0 |  |
| q14 | easy | unspecified | True | False | True | False | 3 | 5 | True |  | 1.0000 | 3742.5 |  |
| q15 | easy | unspecified | True | True | True | False | 5 | 5 | True |  | 1.0000 | 2595.5 |  |
| q16 | easy | unspecified | True | True | True | False | 5 | 5 | True |  | 1.0000 | 2867.4 |  |
| q17 | easy | unspecified | True | True | True | False | 5 | 5 | True |  | 1.0000 | 4640.8 |  |
| q18 | easy | unspecified | True | True | True | False | 5 | 5 | True |  | 1.0000 | 3484.2 |  |
| q19 | easy | unspecified | True | True | True | False | 5 | 5 | True |  | 1.0000 | 3395.6 |  |
| q20 | easy | unspecified | True | True | True | False | 5 | 5 | True |  | 1.0000 | 4667.4 |  |
| q25 | easy | unspecified | True | True | True | False | 5 | 5 | True |  | 1.0000 | 3865.9 |  |
| q26 | easy | unspecified | True | True | True | False | 5 | 5 | True |  | 1.0000 | 3730.8 |  |
| q27 | easy | unspecified | True | True | True | False | 5 | 5 | True |  | 1.0000 | 2415.4 |  |
| q21 | easy | unspecified | False | True | False | True | 5 | 5 | False |  | 0.0000 | 1775.7 |  |
| q22 | easy | unspecified | False | True | False | True | 5 | 5 | False |  | 0.0000 | 2344.7 |  |
| q23 | easy | unspecified | False | True | True | True | 0 | 5 | True |  | 1.0000 | 1658.3 |  |
| q24 | easy | unspecified | False | True | True | True | 0 | 5 | False |  | 1.0000 | 3450.5 |  |
