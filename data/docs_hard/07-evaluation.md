# 评测协议

## 指标定义

检索指标包括 Recall@3、MRR 和 nDCG@3。task_success 定义为 correctness≥4 且 citation_support 为真;tool_accuracy 和 citation_support_rate 只统计可回答题,refusal_rate 只统计不可回答题。

## 新指标

Token F1 与 Exact Match 用 jieba 分词后计算。Context Precision@3 是命中位置 precision 的均值;Context Recall@3 等于 Recall@3;Citation Precision 是回答引用被工具证据支持的比例。

## Judge 设计

裁判使用 JSON mode 输出 correctness、faithfulness、citation_support 和 reason。判定 correctness 时以参考答案为准,温度固定为 0。解析失败或接口异常时返回 0 分和 judge failed 原因,不中断评测。

## Golden 集

easy 集有 27 条,其中 4 条不可回答,作为冻结回归集。hard 集有 100 条,分为单跳 30、多跳 25、时间/版本 10、歧义 10、带干扰的不可回答 15、表格/数值 10。

## 消融设计

closed-book 消融移除 search_docs 工具,用同一份 hard golden 对比 open-book。easy 集不允许改动,hard 集只追加,避免数据泄漏。

## 历史基线

easy 集 baseline 的 R@3 为 0.8696,MRR 为 0.8188,nDCG@3 为 0.8081,总成本 0.1781 元,p50 3287.8 毫秒。hybrid+bge rerank 的 R@3 为 0.9130,MRR 为 0.8623,nDCG@3 为 0.8462,总成本 0.1810 元,p50 4815.4 毫秒。

## 已知偏差

同模型裁判可能偏爱自己的表达;hard 集样本量仍不足以给出窄置信区间;temperature=0 也不能保证完全可复现,报告应记录每次运行的数值。
