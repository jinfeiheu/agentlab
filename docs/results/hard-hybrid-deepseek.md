# RAG 评测报告

## 配置

| 项 | 值 |
|---|---|
| corpus | hard |
| judge_model | deepseek-flash |
| closed_book | False |

## 汇总

### 生成

| 指标 | 值 |
|---|---:|
| count | 100 |
| task_success | 0.8600 |
| answerable_success | 0.8706 |
| tool_accuracy | 0.9647 |
| refusal_rate | 0.9333 |
| avg_search_calls | 1.8588 |
| avg_correctness | 4.6600 |
| avg_faithfulness | 4.8400 |
| citation_support_rate | 0.9412 |
| avg_token_f1 | 0.2295 |
| exact_match | 0.0000 |
| context_precision | 0.8637 |
| context_recall | 0.7722 |
| citation_precision | 0.9294 |
| p50_latency_ms | 2679.6000 |
| p95_latency_ms | 4376.4970 |
| total_tokens | 220369 |
| total_cost | 0.6423 |

### 检索

| 指标 | 值 |
|---|---:|
| count | 85 |
| recall@3 | 0.7722 |
| mrr | 0.8878 |
| ndcg@3 | 0.7808 |
| context_precision | 0.8637 |
| context_recall | 0.7722 |

## 分层结果

### 按 difficulty

| 指标 | easy | medium | hard |
|---|---:|---:|---:|
| count | 37 | 34 | 29 |
| task_success | 0.9730 | 0.7647 | 0.8276 |
| answerable_success | 0.9730 | 0.8000 | 0.7778 |
| avg_correctness | 4.9459 | 4.4412 | 4.5517 |
| avg_faithfulness | 5.0000 | 4.6765 | 4.8276 |
| citation_support_rate | 1.0000 | 0.8333 | 1.0000 |
| refusal_rate | n/a | 1.0000 | 0.9091 |
| avg_token_f1 | 0.2160 | 0.2528 | 0.2192 |
| exact_match | 0.0000 | 0.0000 | 0.0000 |
| context_precision | 0.8468 | 0.8639 | 0.8981 |
| context_recall | 0.8829 | 0.7611 | 0.5630 |
| citation_precision | 0.9730 | 0.8667 | 0.9444 |
| tool_accuracy | 1.0000 | 0.9000 | 1.0000 |
| avg_search_calls | 1.5405 | 1.7667 | 2.6667 |
| p50_latency_ms | 2531.6056 | 2825.8917 | 3112.2805 |
| p95_latency_ms | 4136.2022 | 5537.4916 | 5461.7877 |
| total_tokens | 79860 | 77032 | 63477 |
| total_cost | 0.2221 | 0.2278 | 0.1923 |

### 按 category

| 指标 | ambiguous | multi-hop | single-hop | table-numeric | temporal-version | unanswerable-distractor |
|---|---:|---:|---:|---:|---:|---:|
| count | 10 | 25 | 30 | 10 | 10 | 15 |
| task_success | 0.3000 | 0.8400 | 0.9333 | 1.0000 | 1.0000 | 0.9333 |
| answerable_success | 0.4000 | 0.8800 | 0.9333 | 1.0000 | 1.0000 | n/a |
| avg_correctness | 3.4000 | 4.5600 | 4.7667 | 5.0000 | 5.0000 | 5.0000 |
| avg_faithfulness | 4.7000 | 4.8800 | 4.8333 | 5.0000 | 5.0000 | 4.6667 |
| citation_support_rate | 0.8000 | 0.9200 | 0.9667 | 1.0000 | 1.0000 | n/a |
| refusal_rate | n/a | n/a | n/a | n/a | n/a | 0.9333 |
| avg_token_f1 | 0.2193 | 0.2705 | 0.2253 | 0.2294 | 0.2558 | 0.1587 |
| exact_match | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| context_precision | 0.6333 | 0.8700 | 0.9278 | 0.7500 | 1.0000 | n/a |
| context_recall | 0.4167 | 0.6687 | 0.9833 | 0.8000 | 0.7250 | n/a |
| citation_precision | 0.7000 | 1.0000 | 0.9667 | 0.8000 | 1.0000 | n/a |
| tool_accuracy | 0.8000 | 1.0000 | 0.9667 | 1.0000 | 1.0000 | n/a |
| avg_search_calls | 1.2000 | 2.5600 | 1.5000 | 1.7000 | 2.0000 | n/a |
| p50_latency_ms | 3103.7673 | 3633.8288 | 2427.8058 | 2885.4832 | 2577.9655 | 1754.2221 |
| p95_latency_ms | 3924.7952 | 5734.8666 | 4136.2022 | 4081.0385 | 3321.9946 | 3487.6000 |
| total_tokens | 18589 | 74514 | 62282 | 24822 | 22092 | 18070 |
| total_cost | 0.0590 | 0.2217 | 0.1744 | 0.0695 | 0.0640 | 0.0536 |

## 逐题结果

| id | difficulty | category | answerable | task_success | tool_accuracy | refused | correctness | faithfulness | citation_support | token_f1 | citation_precision | latency_ms | error |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| h001 | easy | single-hop | True | True | True | False | 5 | 5 | True | 0.1961 | 1.0000 | 2531.6 |  |
| h002 | easy | single-hop | True | True | True | False | 5 | 5 | True | 0.1579 | 1.0000 | 2537.3 |  |
| h003 | easy | single-hop | True | True | True | False | 5 | 5 | True | 0.2667 | 1.0000 | 2036.3 |  |
| h004 | easy | single-hop | True | True | True | False | 5 | 5 | True | 0.2222 | 1.0000 | 2139.3 |  |
| h005 | easy | single-hop | True | True | True | False | 5 | 5 | True | 0.3125 | 1.0000 | 1845.6 |  |
| h006 | easy | single-hop | True | True | True | False | 5 | 5 | True | 0.1522 | 1.0000 | 3111.8 |  |
| h007 | easy | single-hop | True | True | True | False | 5 | 5 | True | 0.3509 | 1.0000 | 1909.6 |  |
| h008 | easy | single-hop | True | True | True | False | 5 | 5 | True | 0.1231 | 1.0000 | 2269.4 |  |
| h009 | medium | single-hop | True | True | True | False | 5 | 5 | True | 0.2456 | 1.0000 | 2903.1 |  |
| h010 | easy | single-hop | True | True | True | False | 5 | 5 | True | 0.0952 | 1.0000 | 2939.9 |  |
| h011 | easy | single-hop | True | True | True | False | 5 | 5 | True | 0.1311 | 1.0000 | 1953.1 |  |
| h012 | easy | single-hop | True | True | True | False | 5 | 5 | True | 0.1791 | 1.0000 | 2742.9 |  |
| h013 | easy | single-hop | True | False | True | False | 3 | 5 | True | 0.1212 | 1.0000 | 2247.4 |  |
| h014 | easy | single-hop | True | True | True | False | 5 | 5 | True | 0.6316 | 1.0000 | 1829.9 |  |
| h015 | easy | single-hop | True | True | True | False | 5 | 5 | True | 0.1101 | 1.0000 | 2589.2 |  |
| h016 | easy | single-hop | True | True | True | False | 5 | 5 | True | 0.1489 | 1.0000 | 2367.9 |  |
| h017 | easy | single-hop | True | True | True | False | 5 | 5 | True | 0.3810 | 1.0000 | 2104.1 |  |
| h018 | easy | single-hop | True | True | True | False | 5 | 5 | True | 0.2133 | 1.0000 | 3959.3 |  |
| h019 | easy | single-hop | True | True | True | False | 5 | 5 | True | 0.1075 | 1.0000 | 4136.2 |  |
| h020 | easy | single-hop | True | True | True | False | 5 | 5 | True | 0.2500 | 1.0000 | 2132.1 |  |
| h021 | medium | single-hop | True | False | False | False | 0 | 0 | False | 0.3918 | 0.0000 | 1687.0 |  |
| h022 | easy | single-hop | True | True | True | False | 5 | 5 | True | 0.2623 | 1.0000 | 2237.4 |  |
| h023 | easy | single-hop | True | True | True | False | 5 | 5 | True | 0.2778 | 1.0000 | 2645.5 |  |
| h024 | easy | single-hop | True | True | True | False | 5 | 5 | True | 0.0917 | 1.0000 | 4139.0 |  |
| h025 | medium | single-hop | True | True | True | False | 5 | 5 | True | 0.3478 | 1.0000 | 1803.0 |  |
| h026 | easy | single-hop | True | True | True | False | 5 | 5 | True | 0.4167 | 1.0000 | 2271.1 |  |
| h027 | easy | single-hop | True | True | True | False | 5 | 5 | True | 0.1644 | 1.0000 | 2758.4 |  |
| h028 | easy | single-hop | True | True | True | False | 5 | 5 | True | 0.1149 | 1.0000 | 2487.7 |  |
| h029 | easy | single-hop | True | True | True | False | 5 | 5 | True | 0.1837 | 1.0000 | 3410.4 |  |
| h030 | easy | single-hop | True | True | True | False | 5 | 5 | True | 0.1111 | 1.0000 | 2598.8 |  |
| h031 | medium | multi-hop | True | True | True | False | 5 | 5 | True | 0.2637 | 1.0000 | 5537.5 |  |
| h032 | hard | multi-hop | True | True | True | False | 5 | 5 | True | 0.2454 | 1.0000 | 5242.8 |  |
| h033 | hard | multi-hop | True | True | True | False | 5 | 5 | True | 0.2321 | 1.0000 | 3880.3 |  |
| h034 | hard | multi-hop | True | True | True | False | 5 | 5 | True | 0.4000 | 1.0000 | 2713.7 |  |
| h035 | hard | multi-hop | True | True | True | False | 4 | 4 | True | 0.2545 | 1.0000 | 3152.1 |  |
| h036 | hard | multi-hop | True | False | True | False | 2 | 5 | True | 0.1071 | 1.0000 | 5461.8 |  |
| h037 | hard | multi-hop | True | True | True | False | 5 | 5 | True | 0.1946 | 1.0000 | 4306.7 |  |
| h038 | medium | multi-hop | True | True | True | False | 5 | 5 | True | 0.2383 | 1.0000 | 4231.5 |  |
| h039 | hard | multi-hop | True | True | True | False | 4 | 5 | True | 0.3400 | 1.0000 | 3633.8 |  |
| h040 | medium | multi-hop | True | True | True | False | 5 | 4 | True | 0.1356 | 1.0000 | 5734.9 |  |
| h041 | medium | multi-hop | True | True | True | False | 5 | 5 | True | 0.3478 | 1.0000 | 3440.7 |  |
| h042 | medium | multi-hop | True | False | True | False | 4 | 4 | False | 0.2276 | 1.0000 | 3916.7 |  |
| h043 | hard | multi-hop | True | True | True | False | 4 | 5 | True | 0.1793 | 1.0000 | 4006.8 |  |
| h044 | hard | multi-hop | True | True | True | False | 5 | 5 | True | 0.4756 | 1.0000 | 2516.9 |  |
| h045 | hard | multi-hop | True | True | True | False | 5 | 5 | True | 0.2365 | 1.0000 | 3112.3 |  |
| h046 | medium | multi-hop | True | True | True | False | 5 | 5 | True | 0.4203 | 1.0000 | 2854.6 |  |
| h047 | medium | multi-hop | True | False | True | False | 3 | 5 | False | 0.1307 | 1.0000 | 3931.7 |  |
| h048 | medium | multi-hop | True | True | True | False | 5 | 5 | True | 0.2629 | 1.0000 | 3111.4 |  |
| h049 | hard | multi-hop | True | True | True | False | 5 | 5 | True | 0.3122 | 1.0000 | 3074.7 |  |
| h050 | hard | multi-hop | True | True | True | False | 5 | 5 | True | 0.2538 | 1.0000 | 3542.2 |  |
| h051 | medium | multi-hop | True | True | True | False | 5 | 5 | True | 0.2990 | 1.0000 | 4376.5 |  |
| h052 | medium | multi-hop | True | True | True | False | 5 | 5 | True | 0.2927 | 1.0000 | 2397.1 |  |
| h053 | medium | multi-hop | True | True | True | False | 5 | 5 | True | 0.4158 | 1.0000 | 2466.2 |  |
| h054 | hard | multi-hop | True | False | True | False | 3 | 5 | True | 0.2086 | 1.0000 | 5933.4 |  |
| h055 | hard | multi-hop | True | True | True | False | 5 | 5 | True | 0.2875 | 1.0000 | 3302.0 |  |
| h056 | medium | temporal-version | True | True | True | False | 5 | 5 | True | 0.2222 | 1.0000 | 2544.7 |  |
| h057 | easy | temporal-version | True | True | True | False | 5 | 5 | True | 0.1746 | 1.0000 | 2611.2 |  |
| h058 | easy | temporal-version | True | True | True | False | 5 | 5 | True | 0.2368 | 1.0000 | 2168.9 |  |
| h059 | hard | temporal-version | True | True | True | False | 5 | 5 | True | 0.2543 | 1.0000 | 3242.9 |  |
| h060 | medium | temporal-version | True | True | True | False | 5 | 5 | True | 0.2388 | 1.0000 | 2454.3 |  |
| h061 | medium | temporal-version | True | True | True | False | 5 | 5 | True | 0.3167 | 1.0000 | 2852.5 |  |
| h062 | easy | temporal-version | True | True | True | False | 5 | 5 | True | 0.2069 | 1.0000 | 2354.1 |  |
| h063 | hard | temporal-version | True | True | True | False | 5 | 5 | True | 0.2009 | 1.0000 | 3322.0 |  |
| h064 | medium | temporal-version | True | True | True | False | 5 | 5 | True | 0.3529 | 1.0000 | 2356.7 |  |
| h065 | medium | temporal-version | True | True | True | False | 5 | 5 | True | 0.3542 | 1.0000 | 2750.7 |  |
| h066 | medium | ambiguous | True | False | True | False | 3 | 5 | True | 0.2727 | 1.0000 | 2151.3 |  |
| h067 | medium | ambiguous | True | False | False | False | 4 | 5 | False | 0.1138 | 0.0000 | 2572.6 |  |
| h068 | medium | ambiguous | True | False | False | False | 1 | 2 | False | 0.1042 | 0.0000 | 2405.7 |  |
| h069 | easy | ambiguous | True | True | True | False | 5 | 5 | True | 0.3333 | 1.0000 | 2871.7 |  |
| h070 | medium | ambiguous | True | True | True | False | 5 | 5 | True | 0.3684 | 1.0000 | 2363.9 |  |
| h071 | hard | ambiguous | True | False | True | False | 3 | 5 | True | 0.1830 | 1.0000 | 3335.9 |  |
| h072 | medium | ambiguous | True | True | True | False | 5 | 5 | True | 0.2819 | 1.0000 | 3924.8 |  |
| h073 | hard | ambiguous | True | False | True | False | 2 | 5 | True | 0.1467 | 0.0000 | 3735.9 |  |
| h074 | medium | ambiguous | True | False | True | False | 3 | 5 | True | 0.1560 | 1.0000 | 3725.1 |  |
| h075 | medium | ambiguous | True | False | True | False | 3 | 5 | True | 0.2328 | 1.0000 | 3622.0 |  |
| h076 | medium | unanswerable-distractor | False | True | False | True | 5 | 5 | False | 0.1165 | 0.0000 | 1587.6 |  |
| h077 | hard | unanswerable-distractor | False | True | False | True | 5 | 5 | False | 0.2041 | 0.0000 | 1541.0 |  |
| h078 | hard | unanswerable-distractor | False | True | True | True | 5 | 5 | True | 0.2826 | 1.0000 | 2230.0 |  |
| h079 | medium | unanswerable-distractor | False | True | False | True | 5 | 4 | False | 0.1587 | 0.0000 | 1759.8 |  |
| h080 | medium | unanswerable-distractor | False | True | False | True | 5 | 5 | False | 0.1639 | 0.0000 | 1652.2 |  |
| h081 | hard | unanswerable-distractor | False | True | False | True | 5 | 4 | False | 0.1316 | 0.0000 | 2024.0 |  |
| h082 | hard | unanswerable-distractor | False | True | False | True | 5 | 4 | False | 0.1509 | 0.0000 | 1694.4 |  |
| h083 | hard | unanswerable-distractor | False | True | False | True | 5 | 5 | False | 0.1404 | 0.0000 | 1656.6 |  |
| h084 | hard | unanswerable-distractor | False | False | True | False | 5 | 5 | True | 0.1613 | 1.0000 | 2349.6 |  |
| h085 | hard | unanswerable-distractor | False | True | False | True | 5 | 4 | False | 0.0702 | 0.0000 | 1754.2 |  |
| h086 | hard | unanswerable-distractor | False | True | True | True | 5 | 5 | True | 0.3043 | 1.0000 | 1931.7 |  |
| h087 | hard | unanswerable-distractor | False | True | False | True | 5 | 5 | False | 0.0930 | 0.0000 | 1718.7 |  |
| h088 | hard | unanswerable-distractor | False | True | False | True | 5 | 5 | False | 0.1600 | 0.0000 | 1325.1 |  |
| h089 | hard | unanswerable-distractor | False | True | False | True | 5 | 4 | False | 0.1449 | 0.0000 | 1978.7 |  |
| h090 | medium | unanswerable-distractor | False | True | True | True | 5 | 5 | True | 0.0976 | 1.0000 | 3487.6 |  |
| h091 | easy | table-numeric | True | True | True | False | 5 | 5 | True | 0.1846 | 1.0000 | 3574.3 |  |
| h092 | easy | table-numeric | True | True | True | False | 5 | 5 | True | 0.2667 | 1.0000 | 2358.5 |  |
| h093 | easy | table-numeric | True | True | True | False | 5 | 5 | True | 0.1522 | 0.0000 | 2971.7 |  |
| h094 | easy | table-numeric | True | True | True | False | 5 | 5 | True | 0.1458 | 1.0000 | 3575.3 |  |
| h095 | medium | table-numeric | True | True | True | False | 5 | 5 | True | 0.1176 | 1.0000 | 4081.0 |  |
| h096 | easy | table-numeric | True | True | True | False | 5 | 5 | True | 0.2564 | 1.0000 | 2208.4 |  |
| h097 | easy | table-numeric | True | True | True | False | 5 | 5 | True | 0.2632 | 1.0000 | 2761.1 |  |
| h098 | medium | table-numeric | True | True | True | False | 5 | 5 | True | 0.3878 | 1.0000 | 3148.1 |  |
| h099 | medium | table-numeric | True | True | True | False | 5 | 5 | True | 0.3111 | 1.0000 | 2720.7 |  |
| h100 | medium | table-numeric | True | True | True | False | 5 | 5 | True | 0.2083 | 0.0000 | 2799.3 |  |
