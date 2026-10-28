# RAG 评测报告

## 配置

| 项 | 值 |
|---|---|
| corpus | hard |
| judge_model | deepseek-flash |
| closed_book | True |

## 汇总

### 生成

| 指标 | 值 |
|---|---:|
| count | 100 |
| task_success | 0.1200 |
| answerable_success | 0.0353 |
| tool_accuracy | 0.0000 |
| refusal_rate | 0.7333 |
| avg_search_calls | 0.0000 |
| avg_correctness | 1.2700 |
| avg_faithfulness | 2.5200 |
| citation_support_rate | 0.0000 |
| avg_token_f1 | 0.1707 |
| exact_match | 0.0000 |
| context_precision | n/a |
| context_recall | n/a |
| citation_precision | 0.0000 |
| p50_latency_ms | 1873.1098 |
| p95_latency_ms | 3387.3602 |
| total_tokens | 48894 |
| total_cost | 0.2310 |

### 检索

| 指标 | 值 |
|---|---:|

## 分层结果

### 按 difficulty

| 指标 | easy | medium | hard |
|---|---:|---:|---:|
| count | 37 | 34 | 29 |
| task_success | 0.0270 | 0.1176 | 0.2414 |
| answerable_success | 0.0270 | 0.0667 | 0.0000 |
| avg_correctness | 0.8378 | 1.3235 | 1.7586 |
| avg_faithfulness | 2.4595 | 2.8529 | 2.2069 |
| citation_support_rate | 0.0000 | 0.0000 | 0.0000 |
| refusal_rate | n/a | 0.7500 | 0.7273 |
| avg_token_f1 | 0.1749 | 0.1643 | 0.1730 |
| exact_match | 0.0000 | 0.0000 | 0.0000 |
| context_precision | n/a | n/a | n/a |
| context_recall | n/a | n/a | n/a |
| citation_precision | 0.0000 | 0.0000 | 0.0000 |
| tool_accuracy | 0.0000 | 0.0000 | 0.0000 |
| avg_search_calls | 0.0000 | 0.0000 | 0.0000 |
| p50_latency_ms | 1861.0050 | 1921.0935 | 1702.4719 |
| p95_latency_ms | 3416.2172 | 3387.3602 | 4345.5254 |
| total_tokens | 17230 | 17099 | 14565 |
| total_cost | 0.0786 | 0.0825 | 0.0699 |

### 按 category

| 指标 | ambiguous | multi-hop | single-hop | table-numeric | temporal-version | unanswerable-distractor |
|---|---:|---:|---:|---:|---:|---:|
| count | 10 | 25 | 30 | 10 | 10 | 15 |
| task_success | 0.0000 | 0.0000 | 0.0333 | 0.2000 | 0.0000 | 0.6000 |
| answerable_success | 0.0000 | 0.0000 | 0.0333 | 0.2000 | 0.0000 | n/a |
| avg_correctness | 1.5000 | 0.6800 | 0.7667 | 1.4000 | 0.5000 | 3.5333 |
| avg_faithfulness | 3.5000 | 2.0000 | 2.0333 | 3.0000 | 2.5000 | 3.4000 |
| citation_support_rate | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a |
| refusal_rate | n/a | n/a | n/a | n/a | n/a | 0.7333 |
| avg_token_f1 | 0.1192 | 0.1683 | 0.1891 | 0.1390 | 0.1916 | 0.1797 |
| exact_match | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| context_precision | n/a | n/a | n/a | n/a | n/a | n/a |
| context_recall | n/a | n/a | n/a | n/a | n/a | n/a |
| citation_precision | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a |
| tool_accuracy | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a |
| avg_search_calls | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a |
| p50_latency_ms | 2071.5390 | 1482.0612 | 1672.2193 | 2010.4677 | 1900.3915 | 2053.8381 |
| p95_latency_ms | 2680.8243 | 4345.5254 | 3195.9539 | 3416.2172 | 3387.3602 | 3107.5629 |
| total_tokens | 4992 | 12384 | 13505 | 5286 | 4923 | 7804 |
| total_cost | 0.0244 | 0.0584 | 0.0602 | 0.0260 | 0.0232 | 0.0388 |

## 逐题结果

| id | difficulty | category | answerable | task_success | tool_accuracy | refused | correctness | faithfulness | citation_support | token_f1 | citation_precision | latency_ms | error |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| h001 | easy | single-hop | True | False | False | False | 0 | 3 | False | 0.3429 | 0.0000 | 2055.7 |  |
| h002 | easy | single-hop | True | False | False | False | 3 | 5 | False | 0.1786 | 0.0000 | 2633.7 |  |
| h003 | easy | single-hop | True | False | False | False | 3 | 5 | False | 0.1408 | 0.0000 | 2407.2 |  |
| h004 | easy | single-hop | True | False | False | False | 0 | 0 | False | 0.1176 | 0.0000 | 1076.5 |  |
| h005 | easy | single-hop | True | False | False | False | 0 | 0 | False | 0.3333 | 0.0000 | 1043.7 |  |
| h006 | easy | single-hop | True | False | False | False | 2 | 5 | False | 0.0870 | 0.0000 | 1922.8 |  |
| h007 | easy | single-hop | True | False | False | False | 0 | 0 | False | 0.1212 | 0.0000 | 2248.2 |  |
| h008 | easy | single-hop | True | False | False | False | 1 | 5 | False | 0.0339 | 0.0000 | 2024.3 |  |
| h009 | medium | single-hop | True | False | False | False | 0 | 0 | False | 0.1500 | 0.0000 | 1409.8 |  |
| h010 | easy | single-hop | True | False | False | False | 2 | 5 | False | 0.0580 | 0.0000 | 3559.6 |  |
| h011 | easy | single-hop | True | False | False | False | 0 | 0 | False | 0.1875 | 0.0000 | 768.2 |  |
| h012 | easy | single-hop | True | True | False | False | 5 | 5 | False | 0.2286 | 0.0000 | 2067.1 |  |
| h013 | easy | single-hop | True | False | False | False | 0 | 0 | False | 0.3200 | 0.0000 | 1713.5 |  |
| h014 | easy | single-hop | True | False | False | False | 0 | 0 | False | 0.2000 | 0.0000 | 1036.5 |  |
| h015 | easy | single-hop | True | False | False | False | 0 | 0 | False | 0.2581 | 0.0000 | 1613.4 |  |
| h016 | easy | single-hop | True | False | False | False | 0 | 5 | False | 0.0667 | 0.0000 | 2711.3 |  |
| h017 | easy | single-hop | True | False | False | False | 0 | 0 | False | 0.3571 | 0.0000 | 1035.9 |  |
| h018 | easy | single-hop | True | False | False | False | 1 | 5 | False | 0.0800 | 0.0000 | 2643.5 |  |
| h019 | easy | single-hop | True | False | False | False | 3 | 5 | False | 0.0377 | 0.0000 | 3196.0 |  |
| h020 | easy | single-hop | True | False | False | False | 0 | 0 | False | 0.3226 | 0.0000 | 1622.1 |  |
| h021 | medium | single-hop | True | False | False | False | 0 | 0 | False | 0.3043 | 0.0000 | 1437.4 |  |
| h022 | easy | single-hop | True | False | False | False | 0 | 0 | False | 0.1667 | 0.0000 | 1360.2 |  |
| h023 | easy | single-hop | True | False | False | False | 0 | 0 | False | 0.2857 | 0.0000 | 1031.6 |  |
| h024 | easy | single-hop | True | False | False | False | 1 | 4 | False | 0.0952 | 0.0000 | 1861.0 |  |
| h025 | medium | single-hop | True | False | False | False | 0 | 0 | False | 0.3448 | 0.0000 | 1631.0 |  |
| h026 | easy | single-hop | True | False | False | False | 0 | 0 | False | 0.2000 | 0.0000 | 739.4 |  |
| h027 | easy | single-hop | True | False | False | False | 0 | 0 | False | 0.3077 | 0.0000 | 698.2 |  |
| h028 | easy | single-hop | True | False | False | False | 1 | 5 | False | 0.1017 | 0.0000 | 2710.4 |  |
| h029 | easy | single-hop | True | False | False | False | 1 | 4 | False | 0.0800 | 0.0000 | 1885.2 |  |
| h030 | easy | single-hop | True | False | False | False | 0 | 0 | False | 0.1667 | 0.0000 | 796.9 |  |
| h031 | medium | multi-hop | True | False | False | False | 0 | 0 | False | 0.2439 | 0.0000 | 1027.8 |  |
| h032 | hard | multi-hop | True | False | False | False | 0 | 0 | False | 0.1449 | 0.0000 | 692.0 |  |
| h033 | hard | multi-hop | True | False | False | False | 0 | 0 | False | 0.1818 | 0.0000 | 944.1 |  |
| h034 | hard | multi-hop | True | False | False | False | 0 | 1 | False | 0.1695 | 0.0000 | 1427.8 |  |
| h035 | hard | multi-hop | True | False | False | False | 0 | 0 | False | 0.1333 | 0.0000 | 1482.1 |  |
| h036 | hard | multi-hop | True | False | False | False | 0 | 0 | False | 0.1667 | 0.0000 | 758.9 |  |
| h037 | hard | multi-hop | True | False | False | False | 0 | 1 | False | 0.0426 | 0.0000 | 782.4 |  |
| h038 | medium | multi-hop | True | False | False | False | 3 | 5 | False | 0.0652 | 0.0000 | 2491.7 |  |
| h039 | hard | multi-hop | True | False | False | False | 0 | 0 | False | 0.1846 | 0.0000 | 1702.5 |  |
| h040 | medium | multi-hop | True | False | False | False | 0 | 0 | False | 0.2449 | 0.0000 | 1512.7 |  |
| h041 | medium | multi-hop | True | False | False | False | 1 | 5 | False | 0.0635 | 0.0000 | 1654.5 |  |
| h042 | medium | multi-hop | True | False | False | False | 1 | 4 | False | 0.1446 | 0.0000 | 2378.2 |  |
| h043 | hard | multi-hop | True | False | False | False | 2 | 5 | False | 0.0943 | 0.0000 | 3321.1 |  |
| h044 | hard | multi-hop | True | False | False | False | 2 | 5 | False | 0.2056 | 0.0000 | 2216.5 |  |
| h045 | hard | multi-hop | True | False | False | False | 2 | 5 | False | 0.1739 | 0.0000 | 4345.5 |  |
| h046 | medium | multi-hop | True | False | False | False | 0 | 5 | False | 0.1837 | 0.0000 | 2684.1 |  |
| h047 | medium | multi-hop | True | False | False | False | 2 | 5 | False | 0.1053 | 0.0000 | 3090.9 |  |
| h048 | medium | multi-hop | True | False | False | False | 0 | 0 | False | 0.1860 | 0.0000 | 1264.9 |  |
| h049 | hard | multi-hop | True | False | False | False | 3 | 4 | False | 0.2035 | 0.0000 | 4681.3 |  |
| h050 | hard | multi-hop | True | False | False | False | 0 | 0 | False | 0.2857 | 0.0000 | 1151.7 |  |
| h051 | medium | multi-hop | True | False | False | False | 0 | 0 | False | 0.1034 | 0.0000 | 955.1 |  |
| h052 | medium | multi-hop | True | False | False | False | 1 | 5 | False | 0.1429 | 0.0000 | 3499.8 |  |
| h053 | medium | multi-hop | True | False | False | False | 0 | 0 | False | 0.3043 | 0.0000 | 790.2 |  |
| h054 | hard | multi-hop | True | False | False | False | 0 | 0 | False | 0.2963 | 0.0000 | 1267.7 |  |
| h055 | hard | multi-hop | True | False | False | False | 0 | 0 | False | 0.1364 | 0.0000 | 1062.0 |  |
| h056 | medium | temporal-version | True | False | False | False | 1 | 5 | False | 0.2632 | 0.0000 | 1903.0 |  |
| h057 | easy | temporal-version | True | False | False | False | 0 | 5 | False | 0.2041 | 0.0000 | 2284.0 |  |
| h058 | easy | temporal-version | True | False | False | False | 0 | 0 | False | 0.0345 | 0.0000 | 1011.8 |  |
| h059 | hard | temporal-version | True | False | False | False | 0 | 0 | False | 0.2051 | 0.0000 | 938.2 |  |
| h060 | medium | temporal-version | True | False | False | False | 0 | 5 | False | 0.0625 | 0.0000 | 3387.4 |  |
| h061 | medium | temporal-version | True | False | False | False | 3 | 5 | False | 0.1304 | 0.0000 | 2241.3 |  |
| h062 | easy | temporal-version | True | False | False | False | 1 | 5 | False | 0.3030 | 0.0000 | 1968.9 |  |
| h063 | hard | temporal-version | True | False | False | False | 0 | 0 | False | 0.2917 | 0.0000 | 1457.3 |  |
| h064 | medium | temporal-version | True | False | False | False | 0 | 0 | False | 0.3000 | 0.0000 | 843.6 |  |
| h065 | medium | temporal-version | True | False | False | False | 0 | 0 | False | 0.1212 | 0.0000 | 1897.8 |  |
| h066 | medium | ambiguous | True | False | False | False | 2 | 5 | False | 0.1304 | 0.0000 | 2136.6 |  |
| h067 | medium | ambiguous | True | False | False | False | 3 | 5 | False | 0.1111 | 0.0000 | 2296.1 |  |
| h068 | medium | ambiguous | True | False | False | False | 2 | 5 | False | 0.1096 | 0.0000 | 2006.5 |  |
| h069 | easy | ambiguous | True | False | False | False | 2 | 5 | False | 0.0385 | 0.0000 | 2311.6 |  |
| h070 | medium | ambiguous | True | False | False | False | 0 | 0 | False | 0.2000 | 0.0000 | 1507.5 |  |
| h071 | hard | ambiguous | True | False | False | False | 2 | 5 | False | 0.2000 | 0.0000 | 2680.8 |  |
| h072 | medium | ambiguous | True | False | False | False | 0 | 0 | False | 0.2500 | 0.0000 | 839.4 |  |
| h073 | hard | ambiguous | True | False | False | False | 0 | 0 | False | 0.0513 | 0.0000 | 1337.7 |  |
| h074 | medium | ambiguous | True | False | False | False | 3 | 5 | False | 0.0652 | 0.0000 | 2409.4 |  |
| h075 | medium | ambiguous | True | False | False | False | 1 | 5 | False | 0.0364 | 0.0000 | 1939.2 |  |
| h076 | medium | unanswerable-distractor | False | True | False | True | 5 | 5 | False | 0.3077 | 0.0000 | 1300.0 |  |
| h077 | hard | unanswerable-distractor | False | False | False | False | 0 | 0 | False | 0.1290 | 0.0000 | 2053.8 |  |
| h078 | hard | unanswerable-distractor | False | True | False | True | 5 | 5 | False | 0.2045 | 0.0000 | 2199.5 |  |
| h079 | medium | unanswerable-distractor | False | True | False | True | 4 | 5 | False | 0.2414 | 0.0000 | 1565.6 |  |
| h080 | medium | unanswerable-distractor | False | False | False | True | 4 | 3 | False | 0.1235 | 0.0000 | 2942.1 |  |
| h081 | hard | unanswerable-distractor | False | True | False | True | 5 | 5 | False | 0.1474 | 0.0000 | 2879.9 |  |
| h082 | hard | unanswerable-distractor | False | True | False | True | 5 | 5 | False | 0.1702 | 0.0000 | 2343.1 |  |
| h083 | hard | unanswerable-distractor | False | False | False | False | 0 | 0 | False | 0.2143 | 0.0000 | 1056.4 |  |
| h084 | hard | unanswerable-distractor | False | True | False | True | 5 | 5 | False | 0.2059 | 0.0000 | 2379.6 |  |
| h085 | hard | unanswerable-distractor | False | False | False | False | 0 | 0 | False | 0.2222 | 0.0000 | 1137.8 |  |
| h086 | hard | unanswerable-distractor | False | True | False | True | 5 | 5 | False | 0.2941 | 0.0000 | 1706.1 |  |
| h087 | hard | unanswerable-distractor | False | False | False | True | 5 | 3 | False | 0.0457 | 0.0000 | 3017.1 |  |
| h088 | hard | unanswerable-distractor | False | True | False | True | 5 | 5 | False | 0.1364 | 0.0000 | 2033.0 |  |
| h089 | hard | unanswerable-distractor | False | True | False | True | 5 | 5 | False | 0.0794 | 0.0000 | 3107.6 |  |
| h090 | medium | unanswerable-distractor | False | False | False | False | 0 | 0 | False | 0.1739 | 0.0000 | 1628.6 |  |
| h091 | easy | table-numeric | True | False | False | False | 2 | 4 | False | 0.0690 | 0.0000 | 3416.2 |  |
| h092 | easy | table-numeric | True | False | False | False | 0 | 0 | False | 0.4242 | 0.0000 | 697.8 |  |
| h093 | easy | table-numeric | True | False | False | False | 3 | 5 | False | 0.1224 | 0.0000 | 1927.9 |  |
| h094 | easy | table-numeric | True | False | False | False | 0 | 1 | False | 0.0000 | 0.0000 | 1801.8 |  |
| h095 | medium | table-numeric | True | False | False | False | 0 | 0 | False | 0.0741 | 0.0000 | 2093.0 |  |
| h096 | easy | table-numeric | True | False | False | False | 0 | 5 | False | 0.0000 | 0.0000 | 1295.6 |  |
| h097 | easy | table-numeric | True | False | False | False | 0 | 0 | False | 0.4000 | 0.0000 | 787.5 |  |
| h098 | medium | table-numeric | True | False | False | False | 0 | 5 | False | 0.0247 | 0.0000 | 2881.3 |  |
| h099 | medium | table-numeric | True | True | False | False | 4 | 5 | False | 0.1591 | 0.0000 | 3007.8 |  |
| h100 | medium | table-numeric | True | True | False | False | 5 | 5 | False | 0.1163 | 0.0000 | 2516.3 |  |
