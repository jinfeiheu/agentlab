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
| answerable_success | 0.8588 |
| tool_accuracy | 0.9294 |
| refusal_rate | 1.0000 |
| avg_search_calls | 1.8235 |
| avg_correctness | 4.5600 |
| avg_faithfulness | 4.7500 |
| citation_support_rate | 0.9176 |
| avg_token_f1 | 0.2201 |
| exact_match | 0.0000 |
| context_precision | 0.8637 |
| context_recall | 0.7722 |
| citation_precision | 0.9412 |
| p50_latency_ms | 3426.0811 |
| p95_latency_ms | 6347.4866 |
| total_tokens | 216020 |
| total_cost | 0.6356 |

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
| task_success | 0.9459 | 0.7059 | 0.8276 |
| answerable_success | 0.9459 | 0.7333 | 0.8889 |
| avg_correctness | 4.7838 | 4.2353 | 4.6552 |
| avg_faithfulness | 4.9189 | 4.6471 | 4.6552 |
| citation_support_rate | 0.9459 | 0.8667 | 0.9444 |
| refusal_rate | n/a | 1.0000 | 1.0000 |
| avg_token_f1 | 0.2005 | 0.2518 | 0.2079 |
| exact_match | 0.0000 | 0.0000 | 0.0000 |
| context_precision | 0.8468 | 0.8639 | 0.8981 |
| context_recall | 0.8829 | 0.7611 | 0.5630 |
| citation_precision | 0.9459 | 0.9000 | 1.0000 |
| tool_accuracy | 0.9189 | 0.9000 | 1.0000 |
| avg_search_calls | 1.4865 | 1.7667 | 2.6111 |
| p50_latency_ms | 3168.5125 | 3575.4861 | 3923.2631 |
| p95_latency_ms | 5563.5699 | 5961.3591 | 6574.8555 |
| total_tokens | 73838 | 74814 | 67368 |
| total_cost | 0.2047 | 0.2223 | 0.2087 |

### 按 category

| 指标 | ambiguous | multi-hop | single-hop | table-numeric | temporal-version | unanswerable-distractor |
|---|---:|---:|---:|---:|---:|---:|
| count | 10 | 25 | 30 | 10 | 10 | 15 |
| task_success | 0.4000 | 0.8000 | 0.9667 | 0.9000 | 1.0000 | 0.7333 |
| answerable_success | 0.4000 | 0.8400 | 0.9667 | 0.9000 | 1.0000 | n/a |
| avg_correctness | 3.2000 | 4.4800 | 4.8333 | 4.5000 | 5.0000 | 4.8000 |
| avg_faithfulness | 5.0000 | 4.7600 | 4.7667 | 5.0000 | 5.0000 | 4.2000 |
| citation_support_rate | 0.7000 | 0.9200 | 0.9667 | 0.9000 | 1.0000 | n/a |
| refusal_rate | n/a | n/a | n/a | n/a | n/a | 1.0000 |
| avg_token_f1 | 0.1840 | 0.2514 | 0.2115 | 0.2481 | 0.2654 | 0.1603 |
| exact_match | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| context_precision | 0.6333 | 0.8700 | 0.9278 | 0.7500 | 1.0000 | n/a |
| context_recall | 0.4167 | 0.6687 | 0.9833 | 0.8000 | 0.7250 | n/a |
| citation_precision | 0.7000 | 1.0000 | 0.9667 | 0.9000 | 1.0000 | n/a |
| tool_accuracy | 0.7000 | 1.0000 | 0.9667 | 0.8000 | 1.0000 | n/a |
| avg_search_calls | 1.6000 | 2.4000 | 1.4333 | 1.6000 | 2.0000 | n/a |
| p50_latency_ms | 3289.3196 | 4556.2776 | 3166.2763 | 3610.1241 | 3633.9478 | 1655.4656 |
| p95_latency_ms | 6852.3075 | 6574.8555 | 5563.5699 | 4971.7990 | 6347.4866 | 4350.8668 |
| total_tokens | 21173 | 70839 | 59574 | 23954 | 22695 | 17785 |
| total_cost | 0.0643 | 0.2179 | 0.1653 | 0.0671 | 0.0676 | 0.0534 |

## 逐题结果

| id | difficulty | category | answerable | task_success | tool_accuracy | refused | correctness | faithfulness | citation_support | token_f1 | citation_precision | latency_ms | error |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| h001 | easy | single-hop | True | True | True | False | 5 | 5 | True | 0.2326 | 1.0000 | 11156.4 |  |
| h002 | easy | single-hop | True | True | True | False | 5 | 5 | True | 0.1212 | 1.0000 | 4838.8 |  |
| h003 | easy | single-hop | True | True | True | False | 5 | 5 | True | 0.2105 | 1.0000 | 4924.5 |  |
| h004 | easy | single-hop | True | True | True | False | 5 | 5 | True | 0.2025 | 1.0000 | 2941.3 |  |
| h005 | easy | single-hop | True | True | True | False | 5 | 4 | True | 0.2062 | 1.0000 | 3142.4 |  |
| h006 | easy | single-hop | True | True | True | False | 5 | 5 | True | 0.2545 | 1.0000 | 3094.4 |  |
| h007 | easy | single-hop | True | True | True | False | 5 | 5 | True | 0.3125 | 1.0000 | 2047.6 |  |
| h008 | easy | single-hop | True | True | True | False | 5 | 5 | True | 0.0941 | 1.0000 | 4353.9 |  |
| h009 | medium | single-hop | True | True | True | False | 5 | 5 | True | 0.4000 | 1.0000 | 3372.6 |  |
| h010 | easy | single-hop | True | True | True | False | 5 | 5 | True | 0.1000 | 1.0000 | 3103.2 |  |
| h011 | easy | single-hop | True | True | True | False | 5 | 5 | True | 0.1127 | 1.0000 | 3190.2 |  |
| h012 | easy | single-hop | True | True | True | False | 5 | 5 | True | 0.1538 | 1.0000 | 3730.9 |  |
| h013 | easy | single-hop | True | True | True | False | 5 | 5 | True | 0.1505 | 1.0000 | 5563.6 |  |
| h014 | easy | single-hop | True | True | True | False | 5 | 5 | True | 0.1449 | 1.0000 | 3375.6 |  |
| h015 | easy | single-hop | True | True | True | False | 5 | 5 | True | 0.1778 | 1.0000 | 2745.5 |  |
| h016 | easy | single-hop | True | True | True | False | 5 | 5 | True | 0.1111 | 1.0000 | 3086.7 |  |
| h017 | easy | single-hop | True | True | True | False | 5 | 5 | True | 0.2759 | 1.0000 | 2889.5 |  |
| h018 | easy | single-hop | True | True | True | False | 5 | 5 | True | 0.3673 | 1.0000 | 2418.2 |  |
| h019 | easy | single-hop | True | True | True | False | 5 | 5 | True | 0.0901 | 1.0000 | 3443.1 |  |
| h020 | easy | single-hop | True | True | True | False | 5 | 5 | True | 0.2308 | 1.0000 | 3911.6 |  |
| h021 | medium | single-hop | True | False | False | False | 0 | 1 | False | 0.3958 | 0.0000 | 2114.0 |  |
| h022 | easy | single-hop | True | True | True | False | 5 | 5 | True | 0.1928 | 1.0000 | 2406.0 |  |
| h023 | easy | single-hop | True | True | True | False | 5 | 5 | True | 0.3571 | 1.0000 | 3601.5 |  |
| h024 | easy | single-hop | True | True | True | False | 5 | 5 | True | 0.1316 | 1.0000 | 3527.0 |  |
| h025 | medium | single-hop | True | True | True | False | 5 | 5 | True | 0.2857 | 1.0000 | 2421.1 |  |
| h026 | easy | single-hop | True | True | True | False | 5 | 5 | True | 0.1961 | 1.0000 | 3375.5 |  |
| h027 | easy | single-hop | True | True | True | False | 5 | 5 | True | 0.3529 | 1.0000 | 3505.5 |  |
| h028 | easy | single-hop | True | True | True | False | 5 | 5 | True | 0.1010 | 1.0000 | 2852.9 |  |
| h029 | easy | single-hop | True | True | True | False | 5 | 3 | True | 0.2338 | 1.0000 | 3052.7 |  |
| h030 | easy | single-hop | True | True | True | False | 5 | 5 | True | 0.1481 | 1.0000 | 2454.1 |  |
| h031 | medium | multi-hop | True | True | True | False | 5 | 5 | True | 0.2976 | 1.0000 | 5961.4 |  |
| h032 | hard | multi-hop | True | False | True | False | 4 | 5 | False | 0.1856 | 1.0000 | 6427.1 |  |
| h033 | hard | multi-hop | True | True | True | False | 5 | 5 | True | 0.2513 | 1.0000 | 3923.3 |  |
| h034 | hard | multi-hop | True | True | True | False | 5 | 5 | True | 0.3936 | 1.0000 | 3334.8 |  |
| h035 | hard | multi-hop | True | True | True | False | 4 | 4 | True | 0.2205 | 1.0000 | 5244.0 |  |
| h036 | hard | multi-hop | True | False | True | False | 3 | 5 | True | 0.1439 | 1.0000 | 6574.9 |  |
| h037 | hard | multi-hop | True | True | True | False | 4 | 3 | True | 0.1943 | 1.0000 | 6796.6 |  |
| h038 | medium | multi-hop | True | False | True | False | 3 | 5 | True | 0.2360 | 1.0000 | 4368.0 |  |
| h039 | hard | multi-hop | True | True | True | False | 4 | 5 | True | 0.2731 | 1.0000 | 5413.2 |  |
| h040 | medium | multi-hop | True | True | True | False | 5 | 4 | True | 0.1801 | 1.0000 | 3687.8 |  |
| h041 | medium | multi-hop | True | True | True | False | 5 | 5 | True | 0.2895 | 1.0000 | 3024.5 |  |
| h042 | medium | multi-hop | True | False | True | False | 3 | 5 | True | 0.1574 | 1.0000 | 5049.9 |  |
| h043 | hard | multi-hop | True | True | True | False | 4 | 5 | True | 0.2703 | 1.0000 | 5171.8 |  |
| h044 | hard | multi-hop | True | True | True | False | 5 | 5 | True | 0.3920 | 1.0000 | 4239.7 |  |
| h045 | hard | multi-hop | True | True | True | False | 5 | 5 | True | 0.2025 | 1.0000 | 4557.8 |  |
| h046 | medium | multi-hop | True | True | True | False | 5 | 5 | True | 0.3256 | 1.0000 | 4118.5 |  |
| h047 | medium | multi-hop | True | False | True | False | 3 | 4 | False | 0.1675 | 1.0000 | 4866.4 |  |
| h048 | medium | multi-hop | True | True | True | False | 5 | 5 | True | 0.2674 | 1.0000 | 3379.2 |  |
| h049 | hard | multi-hop | True | True | True | False | 5 | 5 | True | 0.2491 | 1.0000 | 3942.8 |  |
| h050 | hard | multi-hop | True | True | True | False | 5 | 4 | True | 0.2283 | 1.0000 | 3802.8 |  |
| h051 | medium | multi-hop | True | True | True | False | 5 | 5 | True | 0.3412 | 1.0000 | 4157.0 |  |
| h052 | medium | multi-hop | True | True | True | False | 5 | 5 | True | 0.1781 | 1.0000 | 3022.1 |  |
| h053 | medium | multi-hop | True | True | True | False | 5 | 5 | True | 0.3259 | 1.0000 | 4926.0 |  |
| h054 | hard | multi-hop | True | True | True | False | 5 | 5 | True | 0.2049 | 1.0000 | 5185.5 |  |
| h055 | hard | multi-hop | True | True | True | False | 5 | 5 | True | 0.3087 | 1.0000 | 4556.3 |  |
| h056 | medium | temporal-version | True | True | True | False | 5 | 5 | True | 0.2535 | 1.0000 | 3409.1 |  |
| h057 | easy | temporal-version | True | True | True | False | 5 | 5 | True | 0.1860 | 1.0000 | 3168.5 |  |
| h058 | easy | temporal-version | True | True | True | False | 5 | 5 | True | 0.1818 | 1.0000 | 3815.5 |  |
| h059 | hard | temporal-version | True | True | True | False | 5 | 5 | True | 0.2320 | 1.0000 | 3470.2 |  |
| h060 | medium | temporal-version | True | True | True | False | 5 | 5 | True | 0.3478 | 1.0000 | 3674.6 |  |
| h061 | medium | temporal-version | True | True | True | False | 5 | 5 | True | 0.4222 | 1.0000 | 4294.2 |  |
| h062 | easy | temporal-version | True | True | True | False | 5 | 5 | True | 0.3333 | 1.0000 | 2097.3 |  |
| h063 | hard | temporal-version | True | True | True | False | 5 | 5 | True | 0.1515 | 1.0000 | 6347.5 |  |
| h064 | medium | temporal-version | True | True | True | False | 5 | 5 | True | 0.2390 | 1.0000 | 3593.3 |  |
| h065 | medium | temporal-version | True | True | True | False | 5 | 5 | True | 0.3063 | 1.0000 | 4114.6 |  |
| h066 | medium | ambiguous | True | False | True | False | 3 | 5 | True | 0.2429 | 1.0000 | 3557.7 |  |
| h067 | medium | ambiguous | True | False | False | False | 2 | 5 | False | 0.0721 | 0.0000 | 2431.9 |  |
| h068 | medium | ambiguous | True | False | False | False | 2 | 5 | False | 0.0909 | 0.0000 | 1368.2 |  |
| h069 | easy | ambiguous | True | False | False | False | 2 | 5 | False | 0.0000 | 0.0000 | 2054.8 |  |
| h070 | medium | ambiguous | True | True | True | False | 4 | 5 | True | 0.4356 | 1.0000 | 3334.8 |  |
| h071 | hard | ambiguous | True | True | True | False | 5 | 5 | True | 0.2368 | 1.0000 | 5226.9 |  |
| h072 | medium | ambiguous | True | True | True | False | 4 | 5 | True | 0.2906 | 1.0000 | 3185.3 |  |
| h073 | hard | ambiguous | True | False | True | False | 3 | 5 | True | 0.1287 | 1.0000 | 3593.1 |  |
| h074 | medium | ambiguous | True | False | True | False | 3 | 5 | True | 0.1714 | 1.0000 | 3243.8 |  |
| h075 | medium | ambiguous | True | True | True | False | 4 | 5 | True | 0.1714 | 1.0000 | 6852.3 |  |
| h076 | medium | unanswerable-distractor | False | True | False | True | 5 | 4 | False | 0.1818 | 0.0000 | 1853.5 |  |
| h077 | hard | unanswerable-distractor | False | True | False | True | 5 | 5 | False | 0.1389 | 0.0000 | 1350.2 |  |
| h078 | hard | unanswerable-distractor | False | True | True | True | 5 | 5 | True | 0.3934 | 1.0000 | 2323.3 |  |
| h079 | medium | unanswerable-distractor | False | False | False | True | 5 | 2 | False | 0.2667 | 0.0000 | 1302.9 |  |
| h080 | medium | unanswerable-distractor | False | False | False | True | 3 | 3 | False | 0.1205 | 0.0000 | 1655.5 |  |
| h081 | hard | unanswerable-distractor | False | True | True | True | 5 | 5 | False | 0.1408 | 0.0000 | 4350.9 |  |
| h082 | hard | unanswerable-distractor | False | False | False | True | 5 | 3 | False | 0.1270 | 0.0000 | 1327.3 |  |
| h083 | hard | unanswerable-distractor | False | True | False | True | 4 | 5 | False | 0.1569 | 0.0000 | 1080.9 |  |
| h084 | hard | unanswerable-distractor | False | True | True | True | 5 | 5 | True | 0.1417 | 1.0000 | 3797.3 |  |
| h085 | hard | unanswerable-distractor | False | True | False | True | 5 | 4 | False | 0.1905 | 0.0000 | 1425.3 |  |
| h086 | hard | unanswerable-distractor | False | True | True | True | 5 | 5 | True | 0.2078 | 1.0000 | 2073.3 |  |
| h087 | hard | unanswerable-distractor | False | False | False | True | 5 | 3 | False | 0.0559 | 0.0000 | 2336.7 |  |
| h088 | hard | unanswerable-distractor | False | True | False | True | 5 | 5 | False | 0.1143 | 0.0000 | 1268.5 |  |
| h089 | hard | unanswerable-distractor | False | True | False | True | 5 | 4 | False | 0.0935 | 0.0000 | 1638.4 |  |
| h090 | medium | unanswerable-distractor | False | True | True | True | 5 | 5 | True | 0.0741 | 1.0000 | 2048.8 |  |
| h091 | easy | table-numeric | True | False | False | False | 0 | 5 | False | 0.1034 | 0.0000 | 1425.1 |  |
| h092 | easy | table-numeric | True | True | True | False | 5 | 5 | True | 0.5000 | 1.0000 | 3329.5 |  |
| h093 | easy | table-numeric | True | True | True | False | 5 | 5 | True | 0.2308 | 1.0000 | 2483.5 |  |
| h094 | easy | table-numeric | True | True | False | False | 5 | 5 | True | 0.2545 | 1.0000 | 3245.5 |  |
| h095 | medium | table-numeric | True | True | True | False | 5 | 5 | True | 0.1348 | 1.0000 | 4971.8 |  |
| h096 | easy | table-numeric | True | True | True | False | 5 | 5 | True | 0.2000 | 1.0000 | 3025.7 |  |
| h097 | easy | table-numeric | True | True | True | False | 5 | 5 | True | 0.1667 | 1.0000 | 3904.6 |  |
| h098 | medium | table-numeric | True | True | True | False | 5 | 5 | True | 0.4578 | 1.0000 | 4555.0 |  |
| h099 | medium | table-numeric | True | True | True | False | 5 | 5 | True | 0.2623 | 1.0000 | 3890.8 |  |
| h100 | medium | table-numeric | True | True | True | False | 5 | 5 | True | 0.1705 | 1.0000 | 4597.1 |  |
