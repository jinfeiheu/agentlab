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
| task_success | 0.8900 |
| answerable_success | 0.9059 |
| tool_accuracy | 0.9647 |
| refusal_rate | 1.0000 |
| avg_search_calls | 1.7647 |
| avg_correctness | 4.1700 |
| avg_faithfulness | 4.8800 |
| citation_support_rate | 0.9647 |
| avg_token_f1 | 0.2359 |
| exact_match | 0.0000 |
| context_precision | 0.8637 |
| context_recall | 0.7722 |
| citation_precision | 0.9647 |
| p50_latency_ms | 3429.0717 |
| p95_latency_ms | 5995.4240 |
| total_tokens | 213035 |
| total_cost | 0.6318 |

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
| task_success | 0.9730 | 0.8529 | 0.8276 |
| answerable_success | 0.9730 | 0.8667 | 0.8333 |
| avg_correctness | 4.8649 | 4.1471 | 3.3103 |
| avg_faithfulness | 5.0000 | 4.8529 | 4.7586 |
| citation_support_rate | 0.9730 | 0.9333 | 1.0000 |
| refusal_rate | n/a | 1.0000 | 1.0000 |
| avg_token_f1 | 0.2281 | 0.2512 | 0.2279 |
| exact_match | 0.0000 | 0.0000 | 0.0000 |
| context_precision | 0.8468 | 0.8639 | 0.8981 |
| context_recall | 0.8829 | 0.7611 | 0.5630 |
| citation_precision | 0.9730 | 0.9333 | 1.0000 |
| tool_accuracy | 0.9730 | 0.9333 | 1.0000 |
| avg_search_calls | 1.4865 | 1.8667 | 2.1667 |
| p50_latency_ms | 3289.2665 | 3636.4690 | 3916.4689 |
| p95_latency_ms | 4418.3012 | 6971.1019 | 5364.9941 |
| total_tokens | 78963 | 77286 | 56786 |
| total_cost | 0.2203 | 0.2306 | 0.1809 |

### 按 category

| 指标 | ambiguous | multi-hop | single-hop | table-numeric | temporal-version | unanswerable-distractor |
|---|---:|---:|---:|---:|---:|---:|
| count | 10 | 25 | 30 | 10 | 10 | 15 |
| task_success | 0.7000 | 0.8800 | 0.9333 | 1.0000 | 1.0000 | 0.8000 |
| answerable_success | 0.7000 | 0.8800 | 0.9333 | 1.0000 | 1.0000 | n/a |
| avg_correctness | 3.9000 | 4.7200 | 4.6667 | 5.0000 | 5.0000 | 1.3333 |
| avg_faithfulness | 5.0000 | 5.0000 | 5.0000 | 5.0000 | 5.0000 | 4.2000 |
| citation_support_rate | 0.9000 | 1.0000 | 0.9333 | 1.0000 | 1.0000 | n/a |
| refusal_rate | n/a | n/a | n/a | n/a | n/a | 1.0000 |
| avg_token_f1 | 0.2174 | 0.2689 | 0.2331 | 0.2385 | 0.2904 | 0.1604 |
| exact_match | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| context_precision | 0.6333 | 0.8700 | 0.9278 | 0.7500 | 1.0000 | n/a |
| context_recall | 0.4167 | 0.6687 | 0.9833 | 0.8000 | 0.7250 | n/a |
| citation_precision | 0.9000 | 1.0000 | 0.9333 | 1.0000 | 1.0000 | n/a |
| tool_accuracy | 0.9000 | 1.0000 | 0.9333 | 1.0000 | 1.0000 | n/a |
| avg_search_calls | 1.4000 | 2.2400 | 1.4333 | 1.6000 | 2.1000 | n/a |
| p50_latency_ms | 3791.2643 | 4145.4907 | 3156.2981 | 3698.9861 | 3598.9390 | 2074.7286 |
| p95_latency_ms | 4591.4182 | 6971.1019 | 4418.3012 | 4630.2976 | 5364.9941 | 3731.9510 |
| total_tokens | 20119 | 66507 | 61208 | 24995 | 22947 | 17259 |
| total_cost | 0.0622 | 0.2078 | 0.1714 | 0.0703 | 0.0670 | 0.0531 |

## 逐题结果

| id | difficulty | category | answerable | task_success | tool_accuracy | refused | correctness | faithfulness | citation_support | token_f1 | citation_precision | latency_ms | error |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| h001 | easy | single-hop | True | True | True | False | 5 | 5 | True | 0.2703 | 1.0000 | 12000.7 |  |
| h002 | easy | single-hop | True | True | True | False | 5 | 5 | True | 0.1333 | 1.0000 | 3406.5 |  |
| h003 | easy | single-hop | True | True | True | False | 5 | 5 | True | 0.2041 | 1.0000 | 2947.1 |  |
| h004 | easy | single-hop | True | True | True | False | 5 | 5 | True | 0.1649 | 1.0000 | 2854.1 |  |
| h005 | easy | single-hop | True | True | True | False | 5 | 5 | True | 0.1980 | 1.0000 | 3328.0 |  |
| h006 | easy | single-hop | True | True | True | False | 5 | 5 | True | 0.3889 | 1.0000 | 2858.1 |  |
| h007 | easy | single-hop | True | True | True | False | 5 | 5 | True | 0.3509 | 1.0000 | 2564.0 |  |
| h008 | easy | single-hop | True | True | True | False | 5 | 5 | True | 0.1096 | 1.0000 | 3150.5 |  |
| h009 | medium | single-hop | True | True | True | False | 5 | 5 | True | 0.3256 | 1.0000 | 3197.7 |  |
| h010 | easy | single-hop | True | True | True | False | 5 | 5 | True | 0.1290 | 1.0000 | 3343.9 |  |
| h011 | easy | single-hop | True | True | True | False | 5 | 5 | True | 0.0889 | 1.0000 | 2762.1 |  |
| h012 | easy | single-hop | True | True | True | False | 5 | 5 | True | 0.1690 | 1.0000 | 2663.1 |  |
| h013 | easy | single-hop | True | True | True | False | 5 | 5 | True | 0.1842 | 1.0000 | 4418.3 |  |
| h014 | easy | single-hop | True | True | True | False | 5 | 5 | True | 0.5455 | 1.0000 | 2819.4 |  |
| h015 | easy | single-hop | True | True | True | False | 5 | 5 | True | 0.1600 | 1.0000 | 2662.9 |  |
| h016 | easy | single-hop | True | True | True | False | 5 | 5 | True | 0.1373 | 1.0000 | 3548.5 |  |
| h017 | easy | single-hop | True | True | True | False | 5 | 5 | True | 0.3636 | 1.0000 | 3356.2 |  |
| h018 | easy | single-hop | True | True | True | False | 5 | 5 | True | 0.3750 | 1.0000 | 3197.3 |  |
| h019 | easy | single-hop | True | False | False | False | 0 | 5 | False | 0.0217 | 0.0000 | 3111.3 |  |
| h020 | easy | single-hop | True | True | True | False | 5 | 5 | True | 0.2857 | 1.0000 | 3377.0 |  |
| h021 | medium | single-hop | True | False | False | False | 0 | 5 | False | 0.3423 | 0.0000 | 2700.2 |  |
| h022 | easy | single-hop | True | True | True | False | 5 | 5 | True | 0.2581 | 1.0000 | 2508.1 |  |
| h023 | easy | single-hop | True | True | True | False | 5 | 5 | True | 0.5625 | 1.0000 | 3008.2 |  |
| h024 | easy | single-hop | True | True | True | False | 5 | 5 | True | 0.1316 | 1.0000 | 4241.4 |  |
| h025 | medium | single-hop | True | True | True | False | 5 | 5 | True | 0.2927 | 1.0000 | 3354.4 |  |
| h026 | easy | single-hop | True | True | True | False | 5 | 5 | True | 0.1818 | 1.0000 | 3162.1 |  |
| h027 | easy | single-hop | True | True | True | False | 5 | 5 | True | 0.1081 | 1.0000 | 4167.3 |  |
| h028 | easy | single-hop | True | True | True | False | 5 | 5 | True | 0.1163 | 1.0000 | 2595.7 |  |
| h029 | easy | single-hop | True | True | True | False | 5 | 5 | True | 0.2609 | 1.0000 | 3397.3 |  |
| h030 | easy | single-hop | True | True | True | False | 5 | 5 | True | 0.1346 | 1.0000 | 2866.9 |  |
| h031 | medium | multi-hop | True | True | True | False | 5 | 5 | True | 0.2390 | 1.0000 | 3451.7 |  |
| h032 | hard | multi-hop | True | True | True | False | 5 | 5 | True | 0.2222 | 1.0000 | 4773.7 |  |
| h033 | hard | multi-hop | True | True | True | False | 5 | 5 | True | 0.2762 | 1.0000 | 3864.6 |  |
| h034 | hard | multi-hop | True | True | True | False | 5 | 5 | True | 0.4043 | 1.0000 | 3928.7 |  |
| h035 | hard | multi-hop | True | True | True | False | 5 | 5 | True | 0.2397 | 1.0000 | 4871.7 |  |
| h036 | hard | multi-hop | True | False | True | False | 3 | 5 | True | 0.1135 | 1.0000 | 4768.9 |  |
| h037 | hard | multi-hop | True | True | True | False | 5 | 5 | True | 0.2452 | 1.0000 | 5106.8 |  |
| h038 | medium | multi-hop | True | True | True | False | 5 | 5 | True | 0.1725 | 1.0000 | 6971.1 |  |
| h039 | hard | multi-hop | True | True | True | False | 5 | 5 | True | 0.3716 | 1.0000 | 4131.4 |  |
| h040 | medium | multi-hop | True | True | True | False | 4 | 5 | True | 0.1875 | 1.0000 | 5332.8 |  |
| h041 | medium | multi-hop | True | True | True | False | 5 | 5 | True | 0.3117 | 1.0000 | 3068.5 |  |
| h042 | medium | multi-hop | True | True | True | False | 5 | 5 | True | 0.2062 | 1.0000 | 6775.7 |  |
| h043 | hard | multi-hop | True | False | True | False | 3 | 5 | True | 0.3007 | 1.0000 | 3876.4 |  |
| h044 | hard | multi-hop | True | True | True | False | 5 | 5 | True | 0.3619 | 1.0000 | 4080.1 |  |
| h045 | hard | multi-hop | True | True | True | False | 5 | 5 | True | 0.2330 | 1.0000 | 3916.5 |  |
| h046 | medium | multi-hop | True | True | True | False | 5 | 5 | True | 0.4085 | 1.0000 | 3484.4 |  |
| h047 | medium | multi-hop | True | True | True | False | 5 | 5 | True | 0.1944 | 1.0000 | 7945.4 |  |
| h048 | medium | multi-hop | True | True | True | False | 5 | 5 | True | 0.2162 | 1.0000 | 3804.4 |  |
| h049 | hard | multi-hop | True | True | True | False | 5 | 5 | True | 0.3439 | 1.0000 | 4178.9 |  |
| h050 | hard | multi-hop | True | True | True | False | 5 | 5 | True | 0.1429 | 1.0000 | 5995.4 |  |
| h051 | medium | multi-hop | True | False | True | False | 3 | 5 | True | 0.2886 | 1.0000 | 6314.4 |  |
| h052 | medium | multi-hop | True | True | True | False | 5 | 5 | True | 0.2581 | 1.0000 | 3697.7 |  |
| h053 | medium | multi-hop | True | True | True | False | 5 | 5 | True | 0.4167 | 1.0000 | 3156.2 |  |
| h054 | hard | multi-hop | True | True | True | False | 5 | 5 | True | 0.3125 | 1.0000 | 4145.5 |  |
| h055 | hard | multi-hop | True | True | True | False | 5 | 5 | True | 0.2550 | 1.0000 | 4540.0 |  |
| h056 | medium | temporal-version | True | True | True | False | 5 | 5 | True | 0.1682 | 1.0000 | 3643.5 |  |
| h057 | easy | temporal-version | True | True | True | False | 5 | 5 | True | 0.1846 | 1.0000 | 3583.2 |  |
| h058 | easy | temporal-version | True | True | True | False | 5 | 5 | True | 0.3793 | 1.0000 | 3191.6 |  |
| h059 | hard | temporal-version | True | True | True | False | 5 | 5 | True | 0.2937 | 1.0000 | 3171.9 |  |
| h060 | medium | temporal-version | True | True | True | False | 5 | 5 | True | 0.3714 | 1.0000 | 3614.7 |  |
| h061 | medium | temporal-version | True | True | True | False | 5 | 5 | True | 0.3585 | 1.0000 | 3150.6 |  |
| h062 | easy | temporal-version | True | True | True | False | 5 | 5 | True | 0.2476 | 1.0000 | 3486.0 |  |
| h063 | hard | temporal-version | True | True | True | False | 5 | 5 | True | 0.1581 | 1.0000 | 5365.0 |  |
| h064 | medium | temporal-version | True | True | True | False | 5 | 5 | True | 0.3226 | 1.0000 | 3685.7 |  |
| h065 | medium | temporal-version | True | True | True | False | 5 | 5 | True | 0.4198 | 1.0000 | 3802.7 |  |
| h066 | medium | ambiguous | True | True | True | False | 5 | 5 | True | 0.1988 | 1.0000 | 3885.3 |  |
| h067 | medium | ambiguous | True | False | False | False | 0 | 5 | False | 0.0820 | 0.0000 | 2475.5 |  |
| h068 | medium | ambiguous | True | True | True | False | 5 | 5 | True | 0.1931 | 1.0000 | 4310.8 |  |
| h069 | easy | ambiguous | True | True | True | False | 5 | 5 | True | 0.2901 | 1.0000 | 3664.2 |  |
| h070 | medium | ambiguous | True | True | True | False | 5 | 5 | True | 0.4286 | 1.0000 | 2492.0 |  |
| h071 | hard | ambiguous | True | False | True | False | 3 | 5 | True | 0.2521 | 1.0000 | 4591.4 |  |
| h072 | medium | ambiguous | True | True | True | False | 5 | 5 | True | 0.2909 | 1.0000 | 3697.3 |  |
| h073 | hard | ambiguous | True | True | True | False | 5 | 5 | True | 0.1333 | 1.0000 | 4137.7 |  |
| h074 | medium | ambiguous | True | True | True | False | 5 | 5 | True | 0.1644 | 1.0000 | 3325.5 |  |
| h075 | medium | ambiguous | True | False | True | False | 1 | 5 | True | 0.1412 | 1.0000 | 4201.1 |  |
| h076 | medium | unanswerable-distractor | False | False | False | True | 5 | 0 | False | 0.0903 | 0.0000 | 2894.1 |  |
| h077 | hard | unanswerable-distractor | False | False | False | True | 1 | 3 | False | 0.1818 | 0.0000 | 1500.0 |  |
| h078 | hard | unanswerable-distractor | False | True | True | True | 0 | 5 | True | 0.3333 | 1.0000 | 3242.6 |  |
| h079 | medium | unanswerable-distractor | False | True | False | True | 0 | 5 | False | 0.1154 | 0.0000 | 1994.3 |  |
| h080 | medium | unanswerable-distractor | False | True | False | True | 0 | 5 | False | 0.1026 | 0.0000 | 1671.6 |  |
| h081 | hard | unanswerable-distractor | False | True | False | True | 0 | 5 | False | 0.2034 | 0.0000 | 2060.6 |  |
| h082 | hard | unanswerable-distractor | False | True | False | True | 0 | 5 | False | 0.1569 | 0.0000 | 1683.6 |  |
| h083 | hard | unanswerable-distractor | False | True | False | True | 0 | 5 | False | 0.1765 | 0.0000 | 2074.7 |  |
| h084 | hard | unanswerable-distractor | False | True | True | True | 5 | 5 | True | 0.1837 | 1.0000 | 3732.0 |  |
| h085 | hard | unanswerable-distractor | False | True | False | True | 0 | 5 | False | 0.0741 | 0.0000 | 2197.0 |  |
| h086 | hard | unanswerable-distractor | False | True | True | True | 1 | 5 | True | 0.2667 | 1.0000 | 3190.8 |  |
| h087 | hard | unanswerable-distractor | False | False | False | True | 5 | 0 | False | 0.0602 | 0.0000 | 2417.6 |  |
| h088 | hard | unanswerable-distractor | False | True | False | True | 0 | 5 | False | 0.2051 | 0.0000 | 1707.5 |  |
| h089 | hard | unanswerable-distractor | False | True | False | True | 0 | 5 | False | 0.1067 | 0.0000 | 1695.7 |  |
| h090 | medium | unanswerable-distractor | False | True | True | True | 3 | 5 | True | 0.1500 | 0.0000 | 2579.2 |  |
| h091 | easy | table-numeric | True | True | True | False | 5 | 5 | True | 0.3429 | 1.0000 | 2714.4 |  |
| h092 | easy | table-numeric | True | True | True | False | 5 | 5 | True | 0.2222 | 1.0000 | 3289.3 |  |
| h093 | easy | table-numeric | True | True | True | False | 5 | 5 | True | 0.2034 | 1.0000 | 3708.3 |  |
| h094 | easy | table-numeric | True | True | True | False | 5 | 5 | True | 0.1667 | 1.0000 | 3794.9 |  |
| h095 | medium | table-numeric | True | True | True | False | 5 | 5 | True | 0.1750 | 1.0000 | 4630.3 |  |
| h096 | easy | table-numeric | True | True | True | False | 5 | 5 | True | 0.2273 | 1.0000 | 3375.0 |  |
| h097 | easy | table-numeric | True | True | True | False | 5 | 5 | True | 0.1408 | 1.0000 | 3730.0 |  |
| h098 | medium | table-numeric | True | True | True | False | 5 | 5 | True | 0.3918 | 1.0000 | 3689.6 |  |
| h099 | medium | table-numeric | True | True | True | False | 5 | 5 | True | 0.2759 | 1.0000 | 3778.3 |  |
| h100 | medium | table-numeric | True | True | True | False | 5 | 5 | True | 0.2391 | 1.0000 | 3629.5 |  |
