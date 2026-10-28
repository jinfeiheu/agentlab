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
| task_success | 0.8600 |
| answerable_success | 0.8706 |
| tool_accuracy | 0.9647 |
| refusal_rate | 1.0000 |
| avg_search_calls | 1.9412 |
| avg_correctness | 4.1200 |
| avg_faithfulness | 4.8400 |
| citation_support_rate | 0.9647 |
| avg_token_f1 | 0.2204 |
| exact_match | 0.0000 |
| context_precision | 0.8441 |
| context_recall | 0.7875 |
| citation_precision | 0.9500 |
| p50_latency_ms | 2732.6562 |
| p95_latency_ms | 5021.4655 |
| total_tokens | 228888 |
| total_cost | 0.6649 |

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
| task_success | 0.9459 | 0.8529 | 0.7586 |
| answerable_success | 0.9459 | 0.8333 | 0.7778 |
| avg_correctness | 4.7297 | 4.2647 | 3.1724 |
| avg_faithfulness | 4.9730 | 4.9412 | 4.5517 |
| citation_support_rate | 0.9459 | 0.9667 | 1.0000 |
| refusal_rate | n/a | 1.0000 | 1.0000 |
| avg_token_f1 | 0.2087 | 0.2443 | 0.2073 |
| exact_match | 0.0000 | 0.0000 | 0.0000 |
| context_precision | 0.8491 | 0.8167 | 0.8796 |
| context_recall | 0.9640 | 0.7278 | 0.5241 |
| citation_precision | 0.9459 | 0.9583 | 0.9444 |
| tool_accuracy | 0.9459 | 0.9667 | 1.0000 |
| avg_search_calls | 1.4054 | 2.1667 | 2.6667 |
| p50_latency_ms | 2497.7113 | 3407.2708 | 3302.5636 |
| p95_latency_ms | 3541.7773 | 4732.5341 | 5974.8603 |
| total_tokens | 72615 | 86344 | 69929 |
| total_cost | 0.2009 | 0.2507 | 0.2132 |

### 按 category

| 指标 | ambiguous | multi-hop | single-hop | table-numeric | temporal-version | unanswerable-distractor |
|---|---:|---:|---:|---:|---:|---:|
| count | 10 | 25 | 30 | 10 | 10 | 15 |
| task_success | 0.5000 | 0.8400 | 0.9667 | 0.9000 | 1.0000 | 0.8000 |
| answerable_success | 0.5000 | 0.8400 | 0.9667 | 0.9000 | 1.0000 | n/a |
| avg_correctness | 3.4000 | 4.5600 | 4.8333 | 4.5000 | 5.0000 | 1.6000 |
| avg_faithfulness | 4.9000 | 4.9200 | 4.9667 | 5.0000 | 5.0000 | 4.2000 |
| citation_support_rate | 0.9000 | 1.0000 | 0.9667 | 0.9000 | 1.0000 | n/a |
| refusal_rate | n/a | n/a | n/a | n/a | n/a | 1.0000 |
| avg_token_f1 | 0.1781 | 0.2599 | 0.2211 | 0.2150 | 0.2801 | 0.1453 |
| exact_match | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| context_precision | 0.6083 | 0.8733 | 0.9000 | 0.8333 | 0.8500 | n/a |
| context_recall | 0.5833 | 0.6040 | 0.9833 | 1.0000 | 0.6500 | n/a |
| citation_precision | 0.8750 | 0.9600 | 0.9667 | 0.9000 | 1.0000 | n/a |
| tool_accuracy | 0.9000 | 1.0000 | 0.9667 | 0.9000 | 1.0000 | n/a |
| avg_search_calls | 1.7000 | 2.8400 | 1.4000 | 1.5000 | 2.0000 | n/a |
| p50_latency_ms | 3776.8516 | 4370.6109 | 2498.6069 | 2676.7849 | 2495.7251 | 1958.5502 |
| p95_latency_ms | 4579.6339 | 5974.8603 | 3541.7773 | 3873.6332 | 4247.1349 | 3504.5052 |
| total_tokens | 23450 | 80665 | 58785 | 24605 | 22266 | 19117 |
| total_cost | 0.0707 | 0.2403 | 0.1636 | 0.0681 | 0.0649 | 0.0573 |

## 逐题结果

| id | difficulty | category | answerable | task_success | tool_accuracy | refused | correctness | faithfulness | citation_support | token_f1 | citation_precision | latency_ms | error |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| h001 | easy | single-hop | True | True | True | False | 5 | 5 | True | 0.1869 | 1.0000 | 2712.3 |  |
| h002 | easy | single-hop | True | True | True | False | 5 | 5 | True | 0.1364 | 1.0000 | 2969.3 |  |
| h003 | easy | single-hop | True | True | True | False | 5 | 5 | True | 0.2105 | 1.0000 | 2025.1 |  |
| h004 | easy | single-hop | True | True | True | False | 5 | 5 | True | 0.2105 | 1.0000 | 2568.2 |  |
| h005 | easy | single-hop | True | True | True | False | 5 | 5 | True | 0.4878 | 1.0000 | 1841.4 |  |
| h006 | easy | single-hop | True | True | True | False | 5 | 5 | True | 0.1707 | 1.0000 | 2135.7 |  |
| h007 | easy | single-hop | True | True | True | False | 5 | 5 | True | 0.3509 | 1.0000 | 2132.1 |  |
| h008 | easy | single-hop | True | True | True | False | 5 | 5 | True | 0.1039 | 1.0000 | 2127.9 |  |
| h009 | medium | single-hop | True | True | True | False | 5 | 5 | True | 0.2617 | 1.0000 | 2556.4 |  |
| h010 | easy | single-hop | True | True | True | False | 5 | 5 | True | 0.1359 | 1.0000 | 2522.5 |  |
| h011 | easy | single-hop | True | True | True | False | 5 | 5 | True | 0.1290 | 1.0000 | 1714.5 |  |
| h012 | easy | single-hop | True | True | True | False | 5 | 5 | True | 0.1846 | 1.0000 | 2341.0 |  |
| h013 | easy | single-hop | True | True | True | False | 5 | 5 | True | 0.1667 | 1.0000 | 2604.1 |  |
| h014 | easy | single-hop | True | True | True | False | 5 | 5 | True | 0.2609 | 1.0000 | 2514.9 |  |
| h015 | easy | single-hop | True | True | True | False | 5 | 5 | True | 0.1441 | 1.0000 | 2497.7 |  |
| h016 | easy | single-hop | True | True | True | False | 5 | 5 | True | 0.1346 | 1.0000 | 2436.2 |  |
| h017 | easy | single-hop | True | True | True | False | 5 | 5 | True | 0.2857 | 1.0000 | 2606.8 |  |
| h018 | easy | single-hop | True | True | True | False | 5 | 5 | True | 0.3529 | 1.0000 | 2465.2 |  |
| h019 | easy | single-hop | True | True | True | False | 5 | 5 | True | 0.1237 | 1.0000 | 2499.5 |  |
| h020 | easy | single-hop | True | True | True | False | 5 | 5 | True | 0.2727 | 1.0000 | 2456.9 |  |
| h021 | medium | single-hop | True | False | False | False | 0 | 5 | False | 0.3333 | 0.0000 | 3723.0 |  |
| h022 | easy | single-hop | True | True | True | False | 5 | 5 | True | 0.3721 | 1.0000 | 1614.9 |  |
| h023 | easy | single-hop | True | True | True | False | 5 | 5 | True | 0.3125 | 1.0000 | 2460.5 |  |
| h024 | easy | single-hop | True | True | True | False | 5 | 5 | True | 0.1220 | 1.0000 | 2875.7 |  |
| h025 | medium | single-hop | True | True | True | False | 5 | 5 | True | 0.3429 | 1.0000 | 1822.9 |  |
| h026 | easy | single-hop | True | True | True | False | 5 | 4 | True | 0.1852 | 1.0000 | 2757.2 |  |
| h027 | easy | single-hop | True | True | True | False | 5 | 5 | True | 0.2449 | 1.0000 | 2776.8 |  |
| h028 | easy | single-hop | True | True | True | False | 5 | 5 | True | 0.1075 | 1.0000 | 2233.0 |  |
| h029 | easy | single-hop | True | True | True | False | 5 | 5 | True | 0.1513 | 1.0000 | 3541.8 |  |
| h030 | easy | single-hop | True | True | True | False | 5 | 5 | True | 0.1505 | 1.0000 | 2619.3 |  |
| h031 | medium | multi-hop | True | True | True | False | 5 | 5 | True | 0.2347 | 1.0000 | 5136.3 |  |
| h032 | hard | multi-hop | True | True | True | False | 5 | 5 | True | 0.2041 | 1.0000 | 4470.4 |  |
| h033 | hard | multi-hop | True | True | True | False | 5 | 5 | True | 0.2443 | 1.0000 | 4370.6 |  |
| h034 | hard | multi-hop | True | True | True | False | 5 | 5 | True | 0.4348 | 1.0000 | 2791.3 |  |
| h035 | hard | multi-hop | True | True | True | False | 5 | 5 | True | 0.2255 | 1.0000 | 5168.3 |  |
| h036 | hard | multi-hop | True | False | True | False | 1 | 5 | True | 0.1507 | 0.0000 | 4496.5 |  |
| h037 | hard | multi-hop | True | True | True | False | 5 | 5 | True | 0.1667 | 1.0000 | 5305.3 |  |
| h038 | medium | multi-hop | True | True | True | False | 5 | 5 | True | 0.2328 | 1.0000 | 3873.8 |  |
| h039 | hard | multi-hop | True | True | True | False | 5 | 4 | True | 0.4024 | 1.0000 | 3099.3 |  |
| h040 | medium | multi-hop | True | True | True | False | 4 | 5 | True | 0.1979 | 1.0000 | 3972.8 |  |
| h041 | medium | multi-hop | True | True | True | False | 5 | 5 | True | 0.3284 | 1.0000 | 3459.4 |  |
| h042 | medium | multi-hop | True | True | True | False | 5 | 4 | True | 0.2481 | 1.0000 | 4487.1 |  |
| h043 | hard | multi-hop | True | False | True | False | 3 | 5 | True | 0.1976 | 1.0000 | 5974.9 |  |
| h044 | hard | multi-hop | True | True | True | False | 5 | 5 | True | 0.3378 | 1.0000 | 3795.1 |  |
| h045 | hard | multi-hop | True | True | True | False | 5 | 5 | True | 0.1977 | 1.0000 | 3459.9 |  |
| h046 | medium | multi-hop | True | True | True | False | 5 | 5 | True | 0.3613 | 1.0000 | 2853.1 |  |
| h047 | medium | multi-hop | True | False | True | False | 3 | 5 | True | 0.1340 | 1.0000 | 4629.8 |  |
| h048 | medium | multi-hop | True | True | True | False | 5 | 5 | True | 0.2775 | 1.0000 | 3698.5 |  |
| h049 | hard | multi-hop | True | True | True | False | 5 | 5 | True | 0.2880 | 1.0000 | 3302.6 |  |
| h050 | hard | multi-hop | True | True | True | False | 5 | 5 | True | 0.2241 | 1.0000 | 5021.5 |  |
| h051 | medium | multi-hop | True | True | True | False | 5 | 5 | True | 0.2974 | 1.0000 | 4732.5 |  |
| h052 | medium | multi-hop | True | True | True | False | 5 | 5 | True | 0.2105 | 1.0000 | 2735.1 |  |
| h053 | medium | multi-hop | True | True | True | False | 5 | 5 | True | 0.3066 | 1.0000 | 4417.3 |  |
| h054 | hard | multi-hop | True | False | True | False | 3 | 5 | True | 0.1993 | 1.0000 | 6808.9 |  |
| h055 | hard | multi-hop | True | True | True | False | 5 | 5 | True | 0.3966 | 1.0000 | 2635.9 |  |
| h056 | medium | temporal-version | True | True | True | False | 5 | 5 | True | 0.1385 | 1.0000 | 2473.5 |  |
| h057 | easy | temporal-version | True | True | True | False | 5 | 5 | True | 0.1727 | 1.0000 | 2878.7 |  |
| h058 | easy | temporal-version | True | True | True | False | 5 | 5 | True | 0.2899 | 1.0000 | 2059.5 |  |
| h059 | hard | temporal-version | True | True | True | False | 5 | 5 | True | 0.2442 | 1.0000 | 3008.6 |  |
| h060 | medium | temporal-version | True | True | True | False | 5 | 5 | True | 0.3881 | 1.0000 | 2169.2 |  |
| h061 | medium | temporal-version | True | True | True | False | 5 | 5 | True | 0.4176 | 1.0000 | 2273.2 |  |
| h062 | easy | temporal-version | True | True | True | False | 5 | 5 | True | 0.2892 | 1.0000 | 2517.9 |  |
| h063 | hard | temporal-version | True | True | True | False | 5 | 5 | True | 0.2189 | 1.0000 | 4247.1 |  |
| h064 | medium | temporal-version | True | True | True | False | 5 | 5 | True | 0.3711 | 1.0000 | 2376.2 |  |
| h065 | medium | temporal-version | True | True | True | False | 5 | 5 | True | 0.2707 | 1.0000 | 2923.2 |  |
| h066 | medium | ambiguous | True | True | True | False | 4 | 5 | True | 0.3063 | 1.0000 | 2886.4 |  |
| h067 | medium | ambiguous | True | False | True | False | 3 | 4 | True | 0.1091 | 0.7500 | 3821.0 |  |
| h068 | medium | ambiguous | True | True | True | False | 5 | 5 | True | 0.1609 | 1.0000 | 3732.7 |  |
| h069 | easy | ambiguous | True | False | False | False | 0 | 5 | False | 0.0638 | 0.0000 | 1693.7 |  |
| h070 | medium | ambiguous | True | True | True | False | 5 | 5 | True | 0.2877 | 1.0000 | 3010.9 |  |
| h071 | hard | ambiguous | True | False | True | False | 1 | 5 | True | 0.1346 | 1.0000 | 3848.5 |  |
| h072 | medium | ambiguous | True | True | True | False | 5 | 5 | True | 0.2446 | 1.0000 | 4281.9 |  |
| h073 | hard | ambiguous | True | True | True | False | 5 | 5 | True | 0.1091 | 1.0000 | 4579.6 |  |
| h074 | medium | ambiguous | True | False | True | False | 3 | 5 | True | 0.1618 | 1.0000 | 4176.2 |  |
| h075 | medium | ambiguous | True | False | True | False | 3 | 5 | True | 0.2028 | 1.0000 | 3729.4 |  |
| h076 | medium | unanswerable-distractor | False | True | False | True | 5 | 5 | False | 0.1301 | 0.0000 | 2108.9 |  |
| h077 | hard | unanswerable-distractor | False | False | False | True | 1 | 3 | False | 0.2308 | 0.0000 | 1083.3 |  |
| h078 | hard | unanswerable-distractor | False | True | True | True | 3 | 5 | True | 0.2037 | 1.0000 | 2799.9 |  |
| h079 | medium | unanswerable-distractor | False | True | False | True | 0 | 5 | False | 0.2692 | 0.0000 | 1637.9 |  |
| h080 | medium | unanswerable-distractor | False | True | False | True | 0 | 5 | False | 0.0533 | 0.0000 | 1975.5 |  |
| h081 | hard | unanswerable-distractor | False | True | False | True | 0 | 5 | False | 0.1690 | 0.0000 | 1958.6 |  |
| h082 | hard | unanswerable-distractor | False | True | False | True | 0 | 5 | False | 0.1277 | 0.0000 | 1869.6 |  |
| h083 | hard | unanswerable-distractor | False | True | False | True | 0 | 5 | False | 0.1379 | 0.0000 | 1723.8 |  |
| h084 | hard | unanswerable-distractor | False | True | True | True | 0 | 4 | True | 0.1449 | 1.0000 | 3504.5 |  |
| h085 | hard | unanswerable-distractor | False | False | False | True | 5 | 1 | False | 0.1429 | 0.0000 | 1365.3 |  |
| h086 | hard | unanswerable-distractor | False | True | True | True | 0 | 5 | True | 0.1553 | 1.0000 | 2618.6 |  |
| h087 | hard | unanswerable-distractor | False | False | False | True | 5 | 0 | False | 0.1071 | 0.0000 | 1894.4 |  |
| h088 | hard | unanswerable-distractor | False | True | False | True | 0 | 5 | False | 0.0909 | 0.0000 | 1633.1 |  |
| h089 | hard | unanswerable-distractor | False | True | False | True | 0 | 5 | False | 0.1250 | 0.0000 | 2006.4 |  |
| h090 | medium | unanswerable-distractor | False | True | True | True | 5 | 5 | True | 0.0909 | 1.0000 | 2746.3 |  |
| h091 | easy | table-numeric | True | False | False | False | 0 | 5 | False | 0.0678 | 0.0000 | 1921.1 |  |
| h092 | easy | table-numeric | True | True | True | False | 5 | 5 | True | 0.2963 | 1.0000 | 2623.3 |  |
| h093 | easy | table-numeric | True | True | True | False | 5 | 5 | True | 0.2333 | 1.0000 | 2730.2 |  |
| h094 | easy | table-numeric | True | True | True | False | 5 | 5 | True | 0.1892 | 1.0000 | 3557.3 |  |
| h095 | medium | table-numeric | True | True | True | False | 5 | 5 | True | 0.1600 | 1.0000 | 3873.6 |  |
| h096 | easy | table-numeric | True | True | True | False | 5 | 5 | True | 0.1818 | 1.0000 | 2131.2 |  |
| h097 | easy | table-numeric | True | True | True | False | 5 | 5 | True | 0.2439 | 1.0000 | 2150.5 |  |
| h098 | medium | table-numeric | True | True | True | False | 5 | 5 | True | 0.3654 | 1.0000 | 3844.3 |  |
| h099 | medium | table-numeric | True | True | True | False | 5 | 5 | True | 0.2083 | 1.0000 | 3355.1 |  |
| h100 | medium | table-numeric | True | True | True | False | 5 | 5 | True | 0.2041 | 1.0000 | 2291.0 |  |
