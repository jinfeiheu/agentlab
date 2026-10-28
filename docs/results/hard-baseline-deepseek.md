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
| task_success | 0.8300 |
| answerable_success | 0.8118 |
| tool_accuracy | 0.9294 |
| refusal_rate | 1.0000 |
| avg_search_calls | 1.8118 |
| avg_correctness | 4.4500 |
| avg_faithfulness | 4.8200 |
| citation_support_rate | 0.9294 |
| avg_token_f1 | 0.2151 |
| exact_match | 0.0000 |
| context_precision | 0.8441 |
| context_recall | 0.7875 |
| citation_precision | 0.9029 |
| p50_latency_ms | 2552.2088 |
| p95_latency_ms | 4836.8750 |
| total_tokens | 217559 |
| total_cost | 0.6371 |

### 检索

| 指标 | 值 |
|---|---:|
| count | 85 |
| recall@3 | 0.7875 |
| mrr | 0.8490 |
| ndcg@3 | 0.7698 |
| context_precision | 0.8441 |
| context_recall | 0.7875 |

## 分层结果

### 按 difficulty

| 指标 | easy | medium | hard |
|---|---:|---:|---:|
| count | 37 | 34 | 29 |
| task_success | 0.9459 | 0.7647 | 0.7586 |
| answerable_success | 0.9459 | 0.7333 | 0.6667 |
| avg_correctness | 4.8108 | 4.1765 | 4.3103 |
| avg_faithfulness | 4.9189 | 4.7941 | 4.7241 |
| citation_support_rate | 0.9459 | 0.8667 | 1.0000 |
| refusal_rate | n/a | 1.0000 | 1.0000 |
| avg_token_f1 | 0.2009 | 0.2274 | 0.2187 |
| exact_match | 0.0000 | 0.0000 | 0.0000 |
| context_precision | 0.8491 | 0.8167 | 0.8796 |
| context_recall | 0.9640 | 0.7278 | 0.5241 |
| citation_precision | 0.9189 | 0.8333 | 0.9861 |
| tool_accuracy | 0.9459 | 0.8667 | 1.0000 |
| avg_search_calls | 1.4865 | 1.8667 | 2.3889 |
| p50_latency_ms | 2429.8262 | 2656.2892 | 3325.9256 |
| p95_latency_ms | 3029.7685 | 5482.2173 | 6199.2268 |
| total_tokens | 73991 | 77387 | 66181 |
| total_cost | 0.2051 | 0.2272 | 0.2048 |

### 按 category

| 指标 | ambiguous | multi-hop | single-hop | table-numeric | temporal-version | unanswerable-distractor |
|---|---:|---:|---:|---:|---:|---:|
| count | 10 | 25 | 30 | 10 | 10 | 15 |
| task_success | 0.3000 | 0.7600 | 0.9667 | 0.8000 | 1.0000 | 0.9333 |
| answerable_success | 0.3000 | 0.7600 | 0.9667 | 0.8000 | 1.0000 | n/a |
| avg_correctness | 2.8000 | 4.3600 | 4.8333 | 4.1000 | 5.0000 | 4.8000 |
| avg_faithfulness | 4.8000 | 4.9200 | 4.8333 | 5.0000 | 4.9000 | 4.4667 |
| citation_support_rate | 0.7000 | 1.0000 | 0.9667 | 0.8000 | 1.0000 | n/a |
| refusal_rate | n/a | n/a | n/a | n/a | n/a | 1.0000 |
| avg_token_f1 | 0.1740 | 0.2552 | 0.2230 | 0.1723 | 0.2408 | 0.1710 |
| exact_match | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| context_precision | 0.6083 | 0.8733 | 0.9000 | 0.8333 | 0.8500 | n/a |
| context_recall | 0.5833 | 0.6040 | 0.9833 | 1.0000 | 0.6500 | n/a |
| citation_precision | 0.7000 | 0.9900 | 0.9333 | 0.7000 | 1.0000 | n/a |
| tool_accuracy | 0.7000 | 1.0000 | 0.9667 | 0.8000 | 1.0000 | n/a |
| avg_search_calls | 1.4000 | 2.5200 | 1.4667 | 1.3000 | 2.0000 | n/a |
| p50_latency_ms | 2684.5439 | 3665.8325 | 2337.2125 | 2636.3228 | 2656.2892 | 1901.8334 |
| p95_latency_ms | 4443.9457 | 6199.2268 | 2717.9739 | 4298.0514 | 3920.3585 | 3519.4371 |
| total_tokens | 18836 | 76112 | 58405 | 22101 | 22630 | 19475 |
| total_cost | 0.0561 | 0.2314 | 0.1614 | 0.0632 | 0.0666 | 0.0584 |

## 逐题结果

| id | difficulty | category | answerable | task_success | tool_accuracy | refused | correctness | faithfulness | citation_support | token_f1 | citation_precision | latency_ms | error |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| h001 | easy | single-hop | True | True | True | False | 5 | 5 | True | 0.1613 | 1.0000 | 2718.0 |  |
| h002 | easy | single-hop | True | True | True | False | 5 | 5 | True | 0.1446 | 1.0000 | 2342.1 |  |
| h003 | easy | single-hop | True | True | True | False | 5 | 5 | True | 0.2667 | 1.0000 | 2232.9 |  |
| h004 | easy | single-hop | True | True | True | False | 5 | 5 | True | 0.1739 | 1.0000 | 2520.2 |  |
| h005 | easy | single-hop | True | True | True | False | 5 | 5 | True | 0.3548 | 1.0000 | 2349.6 |  |
| h006 | easy | single-hop | True | True | True | False | 5 | 5 | True | 0.1707 | 1.0000 | 2429.8 |  |
| h007 | easy | single-hop | True | True | True | False | 5 | 5 | True | 0.3509 | 1.0000 | 2248.4 |  |
| h008 | easy | single-hop | True | True | True | False | 5 | 5 | True | 0.1333 | 1.0000 | 2185.7 |  |
| h009 | medium | single-hop | True | True | True | False | 5 | 5 | True | 0.2913 | 1.0000 | 2269.2 |  |
| h010 | easy | single-hop | True | True | True | False | 5 | 5 | True | 0.1446 | 1.0000 | 2289.7 |  |
| h011 | easy | single-hop | True | True | True | False | 5 | 5 | True | 0.1429 | 0.0000 | 2667.7 |  |
| h012 | easy | single-hop | True | True | True | False | 5 | 5 | True | 0.1429 | 1.0000 | 2649.3 |  |
| h013 | easy | single-hop | True | True | True | False | 5 | 5 | True | 0.1839 | 1.0000 | 2607.1 |  |
| h014 | easy | single-hop | True | True | True | False | 5 | 5 | True | 0.1250 | 1.0000 | 2159.8 |  |
| h015 | easy | single-hop | True | True | True | False | 5 | 5 | True | 0.1918 | 1.0000 | 2067.4 |  |
| h016 | easy | single-hop | True | True | True | False | 5 | 5 | True | 0.1121 | 1.0000 | 2179.6 |  |
| h017 | easy | single-hop | True | True | True | False | 5 | 5 | True | 0.3404 | 1.0000 | 1876.7 |  |
| h018 | easy | single-hop | True | True | True | False | 5 | 5 | True | 0.3673 | 1.0000 | 2685.2 |  |
| h019 | easy | single-hop | True | True | True | False | 5 | 5 | True | 0.1075 | 1.0000 | 2277.6 |  |
| h020 | easy | single-hop | True | True | True | False | 5 | 5 | True | 0.2278 | 1.0000 | 2006.5 |  |
| h021 | medium | single-hop | True | False | False | False | 0 | 0 | False | 0.4270 | 0.0000 | 1159.4 |  |
| h022 | easy | single-hop | True | True | True | False | 5 | 5 | True | 0.3200 | 1.0000 | 2509.8 |  |
| h023 | easy | single-hop | True | True | True | False | 5 | 5 | True | 0.3509 | 1.0000 | 2445.8 |  |
| h024 | easy | single-hop | True | True | True | False | 5 | 5 | True | 0.0879 | 1.0000 | 2328.8 |  |
| h025 | medium | single-hop | True | True | True | False | 5 | 5 | True | 0.3250 | 1.0000 | 2546.9 |  |
| h026 | easy | single-hop | True | True | True | False | 5 | 5 | True | 0.2174 | 1.0000 | 2497.2 |  |
| h027 | easy | single-hop | True | True | True | False | 5 | 5 | True | 0.2222 | 1.0000 | 2332.3 |  |
| h028 | easy | single-hop | True | True | True | False | 5 | 5 | True | 0.1163 | 1.0000 | 2792.4 |  |
| h029 | easy | single-hop | True | True | True | False | 5 | 5 | True | 0.2250 | 1.0000 | 2539.5 |  |
| h030 | easy | single-hop | True | True | True | False | 5 | 5 | True | 0.2642 | 1.0000 | 2084.3 |  |
| h031 | medium | multi-hop | True | True | True | False | 5 | 5 | True | 0.2623 | 1.0000 | 4836.9 |  |
| h032 | hard | multi-hop | True | True | True | False | 5 | 5 | True | 0.2230 | 1.0000 | 6199.2 |  |
| h033 | hard | multi-hop | True | True | True | False | 5 | 5 | True | 0.2476 | 1.0000 | 3325.9 |  |
| h034 | hard | multi-hop | True | True | True | False | 5 | 5 | True | 0.4568 | 1.0000 | 2858.7 |  |
| h035 | hard | multi-hop | True | True | True | False | 4 | 4 | True | 0.2092 | 1.0000 | 4342.6 |  |
| h036 | hard | multi-hop | True | False | True | False | 2 | 5 | True | 0.1098 | 1.0000 | 3278.7 |  |
| h037 | hard | multi-hop | True | True | True | False | 5 | 5 | True | 0.2308 | 1.0000 | 4589.4 |  |
| h038 | medium | multi-hop | True | True | True | False | 5 | 4 | True | 0.2136 | 1.0000 | 4896.7 |  |
| h039 | hard | multi-hop | True | True | True | False | 4 | 5 | True | 0.2656 | 1.0000 | 4060.3 |  |
| h040 | medium | multi-hop | True | False | True | False | 3 | 5 | True | 0.2162 | 1.0000 | 3665.8 |  |
| h041 | medium | multi-hop | True | True | True | False | 5 | 5 | True | 0.2839 | 1.0000 | 2574.3 |  |
| h042 | medium | multi-hop | True | True | True | False | 5 | 5 | True | 0.1791 | 1.0000 | 5482.2 |  |
| h043 | hard | multi-hop | True | False | True | False | 2 | 5 | True | 0.2653 | 1.0000 | 3718.2 |  |
| h044 | hard | multi-hop | True | True | True | False | 5 | 5 | True | 0.3120 | 1.0000 | 4070.1 |  |
| h045 | hard | multi-hop | True | True | True | False | 5 | 5 | True | 0.2222 | 0.7500 | 3631.3 |  |
| h046 | medium | multi-hop | True | True | True | False | 5 | 5 | True | 0.4060 | 1.0000 | 2936.8 |  |
| h047 | medium | multi-hop | True | False | True | False | 3 | 5 | True | 0.1503 | 1.0000 | 2990.5 |  |
| h048 | medium | multi-hop | True | True | True | False | 5 | 5 | True | 0.2353 | 1.0000 | 3193.5 |  |
| h049 | hard | multi-hop | True | True | True | False | 5 | 5 | True | 0.3410 | 1.0000 | 3323.0 |  |
| h050 | hard | multi-hop | True | False | True | False | 3 | 5 | True | 0.2176 | 1.0000 | 4335.1 |  |
| h051 | medium | multi-hop | True | True | True | False | 5 | 5 | True | 0.3214 | 1.0000 | 3355.8 |  |
| h052 | medium | multi-hop | True | True | True | False | 5 | 5 | True | 0.2400 | 1.0000 | 2564.9 |  |
| h053 | medium | multi-hop | True | True | True | False | 5 | 5 | True | 0.3014 | 1.0000 | 5565.8 |  |
| h054 | hard | multi-hop | True | False | True | False | 3 | 5 | True | 0.1734 | 1.0000 | 6946.1 |  |
| h055 | hard | multi-hop | True | True | True | False | 5 | 5 | True | 0.2968 | 1.0000 | 3397.0 |  |
| h056 | medium | temporal-version | True | True | True | False | 5 | 5 | True | 0.1406 | 1.0000 | 2611.5 |  |
| h057 | easy | temporal-version | True | True | True | False | 5 | 5 | True | 0.1930 | 1.0000 | 2717.6 |  |
| h058 | easy | temporal-version | True | True | True | False | 5 | 4 | True | 0.2558 | 1.0000 | 2541.4 |  |
| h059 | hard | temporal-version | True | True | True | False | 5 | 5 | True | 0.2800 | 1.0000 | 2267.1 |  |
| h060 | medium | temporal-version | True | True | True | False | 5 | 5 | True | 0.2817 | 1.0000 | 2358.6 |  |
| h061 | medium | temporal-version | True | True | True | False | 5 | 5 | True | 0.3469 | 1.0000 | 2701.0 |  |
| h062 | easy | temporal-version | True | True | True | False | 5 | 5 | True | 0.1806 | 1.0000 | 3757.2 |  |
| h063 | hard | temporal-version | True | True | True | False | 5 | 5 | True | 0.2095 | 1.0000 | 3920.4 |  |
| h064 | medium | temporal-version | True | True | True | False | 5 | 5 | True | 0.2479 | 1.0000 | 2490.4 |  |
| h065 | medium | temporal-version | True | True | True | False | 5 | 5 | True | 0.2720 | 1.0000 | 3734.2 |  |
| h066 | medium | ambiguous | True | False | True | False | 3 | 5 | True | 0.3654 | 1.0000 | 2474.7 |  |
| h067 | medium | ambiguous | True | False | False | False | 2 | 5 | False | 0.0408 | 0.0000 | 1726.8 |  |
| h068 | medium | ambiguous | True | False | False | False | 2 | 5 | False | 0.0984 | 0.0000 | 1625.9 |  |
| h069 | easy | ambiguous | True | False | False | False | 2 | 3 | False | 0.0000 | 0.0000 | 2077.4 |  |
| h070 | medium | ambiguous | True | True | True | False | 4 | 5 | True | 0.3256 | 1.0000 | 2894.4 |  |
| h071 | hard | ambiguous | True | False | True | False | 2 | 5 | True | 0.1165 | 1.0000 | 3244.5 |  |
| h072 | medium | ambiguous | True | True | True | False | 4 | 5 | True | 0.2540 | 1.0000 | 3687.8 |  |
| h073 | hard | ambiguous | True | False | True | False | 3 | 5 | True | 0.1515 | 1.0000 | 3401.1 |  |
| h074 | medium | ambiguous | True | False | True | False | 2 | 5 | True | 0.1748 | 1.0000 | 2371.4 |  |
| h075 | medium | ambiguous | True | True | True | False | 4 | 5 | True | 0.2130 | 1.0000 | 4443.9 |  |
| h076 | medium | unanswerable-distractor | False | True | False | True | 5 | 4 | False | 0.1429 | 0.0000 | 1789.5 |  |
| h077 | hard | unanswerable-distractor | False | True | False | True | 5 | 4 | False | 0.2041 | 0.0000 | 1406.8 |  |
| h078 | hard | unanswerable-distractor | False | True | True | True | 5 | 5 | True | 0.3333 | 1.0000 | 2557.5 |  |
| h079 | medium | unanswerable-distractor | False | True | False | True | 5 | 5 | False | 0.2069 | 0.0000 | 1536.6 |  |
| h080 | medium | unanswerable-distractor | False | True | False | True | 5 | 5 | False | 0.0968 | 0.0000 | 1129.6 |  |
| h081 | hard | unanswerable-distractor | False | True | True | True | 5 | 5 | True | 0.3133 | 1.0000 | 3346.8 |  |
| h082 | hard | unanswerable-distractor | False | True | False | True | 4 | 4 | False | 0.2041 | 0.0000 | 2041.0 |  |
| h083 | hard | unanswerable-distractor | False | True | False | True | 4 | 4 | False | 0.1569 | 0.0000 | 1214.3 |  |
| h084 | hard | unanswerable-distractor | False | True | True | True | 5 | 5 | True | 0.1786 | 1.0000 | 3519.4 |  |
| h085 | hard | unanswerable-distractor | False | True | False | True | 5 | 5 | False | 0.0625 | 0.0000 | 2094.5 |  |
| h086 | hard | unanswerable-distractor | False | True | True | True | 5 | 5 | True | 0.2581 | 1.0000 | 1901.8 |  |
| h087 | hard | unanswerable-distractor | False | False | False | True | 4 | 2 | False | 0.0522 | 0.0000 | 1778.4 |  |
| h088 | hard | unanswerable-distractor | False | True | False | True | 5 | 4 | False | 0.1290 | 0.0000 | 2073.2 |  |
| h089 | hard | unanswerable-distractor | False | True | False | True | 5 | 5 | False | 0.1220 | 0.0000 | 1875.6 |  |
| h090 | medium | unanswerable-distractor | False | True | True | True | 5 | 5 | True | 0.1053 | 1.0000 | 2363.2 |  |
| h091 | easy | table-numeric | True | False | False | False | 1 | 5 | False | 0.0930 | 0.0000 | 1385.9 |  |
| h092 | easy | table-numeric | True | True | True | False | 5 | 5 | True | 0.3210 | 1.0000 | 2219.4 |  |
| h093 | easy | table-numeric | True | True | True | False | 5 | 5 | True | 0.1687 | 1.0000 | 2477.7 |  |
| h094 | easy | table-numeric | True | True | True | False | 5 | 5 | True | 0.1918 | 1.0000 | 3029.8 |  |
| h095 | medium | table-numeric | True | True | True | False | 5 | 5 | True | 0.1304 | 1.0000 | 4298.1 |  |
| h096 | easy | table-numeric | True | True | True | False | 5 | 5 | True | 0.2500 | 1.0000 | 2544.1 |  |
| h097 | easy | table-numeric | True | True | True | False | 5 | 5 | True | 0.1333 | 1.0000 | 2870.1 |  |
| h098 | medium | table-numeric | True | False | False | False | 0 | 5 | False | 0.0211 | 0.0000 | 2455.5 |  |
| h099 | medium | table-numeric | True | True | True | False | 5 | 5 | True | 0.2250 | 0.0000 | 2728.5 |  |
| h100 | medium | table-numeric | True | True | True | False | 5 | 5 | True | 0.1887 | 1.0000 | 2823.2 |  |
