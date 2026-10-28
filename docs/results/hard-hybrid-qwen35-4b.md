# RAG 评测报告

## 配置

| 项 | 值 |
|---|---|
| corpus | hard |
| judge_model | qwen3.5:4b |
| closed_book | False |

## 汇总

### 生成

| 指标 | 值 |
|---|---:|
| count | 100 |
| task_success | 0.8800 |
| answerable_success | 0.9059 |
| tool_accuracy | 0.9647 |
| refusal_rate | 1.0000 |
| avg_search_calls | 1.9412 |
| avg_correctness | 4.3000 |
| avg_faithfulness | 4.7600 |
| citation_support_rate | 0.9647 |
| avg_token_f1 | 0.2313 |
| exact_match | 0.0000 |
| context_precision | 0.8637 |
| context_recall | 0.7722 |
| citation_precision | 0.9382 |
| p50_latency_ms | 2669.0864 |
| p95_latency_ms | 4720.8335 |
| total_tokens | 218995 |
| total_cost | 0.6447 |

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
| task_success | 1.0000 | 0.7941 | 0.8276 |
| answerable_success | 1.0000 | 0.8333 | 0.8333 |
| avg_correctness | 5.0000 | 4.2647 | 3.4483 |
| avg_faithfulness | 5.0000 | 4.6765 | 4.5517 |
| citation_support_rate | 1.0000 | 0.9000 | 1.0000 |
| refusal_rate | n/a | 1.0000 | 1.0000 |
| avg_token_f1 | 0.2257 | 0.2391 | 0.2293 |
| exact_match | 0.0000 | 0.0000 | 0.0000 |
| context_precision | 0.8468 | 0.8639 | 0.8981 |
| context_recall | 0.8829 | 0.7611 | 0.5630 |
| citation_precision | 0.9730 | 0.8583 | 1.0000 |
| tool_accuracy | 1.0000 | 0.9000 | 1.0000 |
| avg_search_calls | 1.6486 | 1.7667 | 2.8333 |
| p50_latency_ms | 2448.9462 | 2791.8286 | 4008.3691 |
| p95_latency_ms | 3608.1290 | 4407.5656 | 5863.8996 |
| total_tokens | 77439 | 72242 | 69314 |
| total_cost | 0.2144 | 0.2167 | 0.2137 |

### 按 category

| 指标 | ambiguous | multi-hop | single-hop | table-numeric | temporal-version | unanswerable-distractor |
|---|---:|---:|---:|---:|---:|---:|
| count | 10 | 25 | 30 | 10 | 10 | 15 |
| task_success | 0.6000 | 0.8800 | 0.9667 | 1.0000 | 1.0000 | 0.7333 |
| answerable_success | 0.6000 | 0.8800 | 0.9667 | 1.0000 | 1.0000 | n/a |
| avg_correctness | 3.6000 | 4.7200 | 4.8333 | 5.0000 | 5.0000 | 2.0667 |
| avg_faithfulness | 4.9000 | 4.9200 | 5.0000 | 5.0000 | 5.0000 | 3.6000 |
| citation_support_rate | 0.8000 | 1.0000 | 0.9667 | 1.0000 | 1.0000 | n/a |
| refusal_rate | n/a | n/a | n/a | n/a | n/a | 1.0000 |
| avg_token_f1 | 0.2157 | 0.2586 | 0.2288 | 0.2251 | 0.2812 | 0.1720 |
| exact_match | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| context_precision | 0.6333 | 0.8700 | 0.9278 | 0.7500 | 1.0000 | n/a |
| context_recall | 0.4167 | 0.6687 | 0.9833 | 0.8000 | 0.7250 | n/a |
| citation_precision | 0.7750 | 1.0000 | 0.9667 | 0.9000 | 0.9000 | n/a |
| tool_accuracy | 0.8000 | 1.0000 | 0.9667 | 1.0000 | 1.0000 | n/a |
| avg_search_calls | 1.6000 | 2.4800 | 1.5000 | 1.8000 | 2.4000 | n/a |
| p50_latency_ms | 3200.4827 | 4117.8346 | 2430.5441 | 2961.3639 | 2614.6000 | 1892.9328 |
| p95_latency_ms | 4706.7140 | 5863.8996 | 3326.0950 | 3680.9868 | 4844.5689 | 4115.9707 |
| total_tokens | 21987 | 66929 | 58591 | 26217 | 26456 | 18815 |
| total_cost | 0.0671 | 0.2102 | 0.1627 | 0.0732 | 0.0753 | 0.0562 |

## 逐题结果

| id | difficulty | category | answerable | task_success | tool_accuracy | refused | correctness | faithfulness | citation_support | token_f1 | citation_precision | latency_ms | error |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| h001 | easy | single-hop | True | True | True | False | 5 | 5 | True | 0.2000 | 1.0000 | 3326.1 |  |
| h002 | easy | single-hop | True | True | True | False | 5 | 5 | True | 0.1319 | 1.0000 | 2559.4 |  |
| h003 | easy | single-hop | True | True | True | False | 5 | 5 | True | 0.3175 | 1.0000 | 2386.4 |  |
| h004 | easy | single-hop | True | True | True | False | 5 | 5 | True | 0.2025 | 1.0000 | 2132.3 |  |
| h005 | easy | single-hop | True | True | True | False | 5 | 5 | True | 0.2778 | 1.0000 | 2125.6 |  |
| h006 | easy | single-hop | True | True | True | False | 5 | 5 | True | 0.3043 | 1.0000 | 1824.8 |  |
| h007 | easy | single-hop | True | True | True | False | 5 | 5 | True | 0.1754 | 1.0000 | 2374.2 |  |
| h008 | easy | single-hop | True | True | True | False | 5 | 5 | True | 0.1039 | 1.0000 | 2207.2 |  |
| h009 | medium | single-hop | True | True | True | False | 5 | 5 | True | 0.2373 | 1.0000 | 2099.4 |  |
| h010 | easy | single-hop | True | True | True | False | 5 | 5 | True | 0.1319 | 1.0000 | 2696.4 |  |
| h011 | easy | single-hop | True | True | True | False | 5 | 5 | True | 0.1212 | 1.0000 | 2493.5 |  |
| h012 | easy | single-hop | True | True | True | False | 5 | 5 | True | 0.1622 | 1.0000 | 2506.9 |  |
| h013 | easy | single-hop | True | True | True | False | 5 | 5 | True | 0.1373 | 1.0000 | 2721.4 |  |
| h014 | easy | single-hop | True | True | True | False | 5 | 5 | True | 0.1389 | 1.0000 | 2487.0 |  |
| h015 | easy | single-hop | True | True | True | False | 5 | 5 | True | 0.1633 | 1.0000 | 2668.6 |  |
| h016 | easy | single-hop | True | True | True | False | 5 | 5 | True | 0.1296 | 1.0000 | 2448.9 |  |
| h017 | easy | single-hop | True | True | True | False | 5 | 5 | True | 0.3404 | 1.0000 | 2125.7 |  |
| h018 | easy | single-hop | True | True | True | False | 5 | 5 | True | 0.6667 | 1.0000 | 2254.6 |  |
| h019 | easy | single-hop | True | True | True | False | 5 | 5 | True | 0.1020 | 1.0000 | 4000.1 |  |
| h020 | easy | single-hop | True | True | True | False | 5 | 5 | True | 0.2791 | 1.0000 | 2412.1 |  |
| h021 | medium | single-hop | True | False | False | False | 0 | 5 | False | 0.3000 | 0.0000 | 2745.7 |  |
| h022 | easy | single-hop | True | True | True | False | 5 | 5 | True | 0.3404 | 1.0000 | 2597.0 |  |
| h023 | easy | single-hop | True | True | True | False | 5 | 5 | True | 0.3529 | 1.0000 | 2094.7 |  |
| h024 | easy | single-hop | True | True | True | False | 5 | 5 | True | 0.1389 | 1.0000 | 2307.9 |  |
| h025 | medium | single-hop | True | True | True | False | 5 | 5 | True | 0.3429 | 1.0000 | 2665.2 |  |
| h026 | easy | single-hop | True | True | True | False | 5 | 5 | True | 0.1724 | 1.0000 | 2918.2 |  |
| h027 | easy | single-hop | True | True | True | False | 5 | 5 | True | 0.2449 | 1.0000 | 2272.9 |  |
| h028 | easy | single-hop | True | True | True | False | 5 | 5 | True | 0.1961 | 1.0000 | 2083.2 |  |
| h029 | easy | single-hop | True | True | True | False | 5 | 5 | True | 0.2118 | 1.0000 | 2832.3 |  |
| h030 | easy | single-hop | True | True | True | False | 5 | 5 | True | 0.2414 | 1.0000 | 1886.8 |  |
| h031 | medium | multi-hop | True | True | True | False | 5 | 5 | True | 0.2874 | 1.0000 | 3599.1 |  |
| h032 | hard | multi-hop | True | True | True | False | 5 | 5 | True | 0.2568 | 1.0000 | 4800.7 |  |
| h033 | hard | multi-hop | True | True | True | False | 5 | 5 | True | 0.2167 | 1.0000 | 4716.3 |  |
| h034 | hard | multi-hop | True | True | True | False | 5 | 5 | True | 0.4368 | 1.0000 | 2416.9 |  |
| h035 | hard | multi-hop | True | True | True | False | 5 | 5 | True | 0.2214 | 1.0000 | 4481.5 |  |
| h036 | hard | multi-hop | True | True | True | False | 5 | 4 | True | 0.1881 | 1.0000 | 4298.4 |  |
| h037 | hard | multi-hop | True | True | True | False | 5 | 5 | True | 0.2252 | 1.0000 | 4008.4 |  |
| h038 | medium | multi-hop | True | True | True | False | 5 | 5 | True | 0.2604 | 1.0000 | 2611.8 |  |
| h039 | hard | multi-hop | True | True | True | False | 5 | 4 | True | 0.3140 | 1.0000 | 4720.8 |  |
| h040 | medium | multi-hop | True | True | True | False | 5 | 5 | True | 0.1891 | 1.0000 | 4407.6 |  |
| h041 | medium | multi-hop | True | True | True | False | 5 | 5 | True | 0.2326 | 1.0000 | 2981.2 |  |
| h042 | medium | multi-hop | True | True | True | False | 4 | 5 | True | 0.2182 | 1.0000 | 2828.1 |  |
| h043 | hard | multi-hop | True | False | True | False | 3 | 5 | True | 0.2276 | 1.0000 | 5863.9 |  |
| h044 | hard | multi-hop | True | True | True | False | 5 | 5 | True | 0.2920 | 1.0000 | 4576.0 |  |
| h045 | hard | multi-hop | True | True | True | False | 5 | 5 | True | 0.2172 | 1.0000 | 4117.8 |  |
| h046 | medium | multi-hop | True | True | True | False | 5 | 5 | True | 0.3394 | 1.0000 | 3408.1 |  |
| h047 | medium | multi-hop | True | False | True | False | 3 | 5 | True | 0.1376 | 1.0000 | 4383.4 |  |
| h048 | medium | multi-hop | True | True | True | False | 5 | 5 | True | 0.2295 | 1.0000 | 3203.6 |  |
| h049 | hard | multi-hop | True | True | True | False | 5 | 5 | True | 0.3051 | 1.0000 | 5898.0 |  |
| h050 | hard | multi-hop | True | True | True | False | 5 | 5 | True | 0.1603 | 1.0000 | 4519.5 |  |
| h051 | medium | multi-hop | True | True | True | False | 5 | 5 | True | 0.3522 | 1.0000 | 2824.5 |  |
| h052 | medium | multi-hop | True | True | True | False | 5 | 5 | True | 0.2824 | 1.0000 | 2391.4 |  |
| h053 | medium | multi-hop | True | True | True | False | 5 | 5 | True | 0.3212 | 1.0000 | 2759.1 |  |
| h054 | hard | multi-hop | True | False | True | False | 3 | 5 | True | 0.1905 | 1.0000 | 5600.1 |  |
| h055 | hard | multi-hop | True | True | True | False | 5 | 5 | True | 0.3636 | 1.0000 | 3289.2 |  |
| h056 | medium | temporal-version | True | True | True | False | 5 | 5 | True | 0.1800 | 0.0000 | 2443.5 |  |
| h057 | easy | temporal-version | True | True | True | False | 5 | 5 | True | 0.1519 | 1.0000 | 2288.1 |  |
| h058 | easy | temporal-version | True | True | True | False | 5 | 5 | True | 0.3014 | 1.0000 | 2279.5 |  |
| h059 | hard | temporal-version | True | True | True | False | 5 | 5 | True | 0.2716 | 1.0000 | 2927.3 |  |
| h060 | medium | temporal-version | True | True | True | False | 5 | 5 | True | 0.2796 | 1.0000 | 2595.1 |  |
| h061 | medium | temporal-version | True | True | True | False | 5 | 5 | True | 0.3958 | 1.0000 | 2634.1 |  |
| h062 | easy | temporal-version | True | True | True | False | 5 | 5 | True | 0.3514 | 1.0000 | 2504.7 |  |
| h063 | hard | temporal-version | True | True | True | False | 5 | 5 | True | 0.1938 | 1.0000 | 4844.6 |  |
| h064 | medium | temporal-version | True | True | True | False | 5 | 5 | True | 0.3826 | 1.0000 | 3174.5 |  |
| h065 | medium | temporal-version | True | True | True | False | 5 | 5 | True | 0.3040 | 1.0000 | 4314.5 |  |
| h066 | medium | ambiguous | True | True | True | False | 5 | 5 | True | 0.2714 | 0.7500 | 2730.9 |  |
| h067 | medium | ambiguous | True | False | False | False | 0 | 5 | False | 0.1400 | 0.0000 | 2298.1 |  |
| h068 | medium | ambiguous | True | False | False | False | 0 | 5 | False | 0.0735 | 0.0000 | 3489.0 |  |
| h069 | easy | ambiguous | True | True | True | False | 5 | 5 | True | 0.2667 | 1.0000 | 3608.1 |  |
| h070 | medium | ambiguous | True | True | True | False | 5 | 5 | True | 0.3540 | 1.0000 | 2825.7 |  |
| h071 | hard | ambiguous | True | True | True | False | 5 | 5 | True | 0.2975 | 1.0000 | 4078.5 |  |
| h072 | medium | ambiguous | True | True | True | False | 5 | 5 | True | 0.2810 | 1.0000 | 2911.9 |  |
| h073 | hard | ambiguous | True | False | True | False | 3 | 5 | True | 0.1317 | 1.0000 | 3884.6 |  |
| h074 | medium | ambiguous | True | True | True | False | 5 | 5 | True | 0.1389 | 1.0000 | 2680.9 |  |
| h075 | medium | ambiguous | True | False | True | False | 3 | 4 | True | 0.2018 | 1.0000 | 4706.7 |  |
| h076 | medium | unanswerable-distractor | False | False | False | True | 5 | 0 | False | 0.1250 | 0.0000 | 1906.1 |  |
| h077 | hard | unanswerable-distractor | False | False | False | True | 5 | 0 | False | 0.1892 | 0.0000 | 1276.8 |  |
| h078 | hard | unanswerable-distractor | False | True | True | True | 1 | 4 | True | 0.4400 | 1.0000 | 2434.0 |  |
| h079 | medium | unanswerable-distractor | False | False | False | True | 5 | 0 | False | 0.1165 | 0.0000 | 2359.6 |  |
| h080 | medium | unanswerable-distractor | False | True | False | True | 0 | 5 | False | 0.0727 | 0.0000 | 1752.7 |  |
| h081 | hard | unanswerable-distractor | False | True | False | True | 0 | 5 | False | 0.0971 | 0.0000 | 2231.2 |  |
| h082 | hard | unanswerable-distractor | False | False | False | True | 0 | 0 | False | 0.1905 | 0.0000 | 1448.6 |  |
| h083 | hard | unanswerable-distractor | False | True | False | True | 0 | 5 | False | 0.1818 | 0.0000 | 1574.5 |  |
| h084 | hard | unanswerable-distractor | False | True | True | True | 0 | 5 | True | 0.2020 | 1.0000 | 4116.0 |  |
| h085 | hard | unanswerable-distractor | False | True | False | True | 5 | 5 | False | 0.1667 | 0.0000 | 1593.2 |  |
| h086 | hard | unanswerable-distractor | False | True | True | True | 5 | 5 | True | 0.3200 | 1.0000 | 2282.7 |  |
| h087 | hard | unanswerable-distractor | False | True | False | True | 0 | 5 | False | 0.0714 | 0.0000 | 1892.9 |  |
| h088 | hard | unanswerable-distractor | False | True | False | True | 0 | 5 | False | 0.1860 | 0.0000 | 1362.0 |  |
| h089 | hard | unanswerable-distractor | False | True | False | True | 0 | 5 | False | 0.0941 | 0.0000 | 1850.4 |  |
| h090 | medium | unanswerable-distractor | False | True | True | True | 5 | 5 | True | 0.1277 | 1.0000 | 2067.3 |  |
| h091 | easy | table-numeric | True | True | True | False | 5 | 5 | True | 0.3429 | 0.0000 | 2485.4 |  |
| h092 | easy | table-numeric | True | True | True | False | 5 | 5 | True | 0.2385 | 1.0000 | 2365.3 |  |
| h093 | easy | table-numeric | True | True | True | False | 5 | 5 | True | 0.2414 | 1.0000 | 2396.3 |  |
| h094 | easy | table-numeric | True | True | True | False | 5 | 5 | True | 0.1750 | 1.0000 | 2909.7 |  |
| h095 | medium | table-numeric | True | True | True | False | 5 | 5 | True | 0.1446 | 1.0000 | 3681.0 |  |
| h096 | easy | table-numeric | True | True | True | False | 5 | 5 | True | 0.1961 | 1.0000 | 3013.0 |  |
| h097 | easy | table-numeric | True | True | True | False | 5 | 5 | True | 0.1010 | 1.0000 | 3356.8 |  |
| h098 | medium | table-numeric | True | True | True | False | 5 | 5 | True | 0.3689 | 1.0000 | 3560.7 |  |
| h099 | medium | table-numeric | True | True | True | False | 5 | 5 | True | 0.2011 | 1.0000 | 3171.0 |  |
| h100 | medium | table-numeric | True | True | True | False | 5 | 5 | True | 0.2418 | 1.0000 | 2669.5 |  |
