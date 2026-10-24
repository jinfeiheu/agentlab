# pgvector 与检索实现

## 表与扩展

Postgres 使用 pgvector 扩展,向量列类型为 vector(1024)。easy 语料写入 docs collection,hard 语料写入 docs_hard collection,两者互不影响。

## 索引参数

当前使用 HNSW 索引:m=16,ef_construction=64,距离度量 cosine。HNSW 在数据量小于 100 万行时优于 IVFFlat。

## IVFFlat 说明

2025 年的内部草稿曾推荐 IVFFlat(lists=100),但该建议已在 2026-08-15 被 HNSW 方案取代,草稿保留在附录中仅作历史参考。

## 混合检索实现

向量检索取前 8 条,BM25 取正分前 8 条,用 RRF 融合,RRF 常数 k=60,最终返回 top_n=6。BM25 使用 jieba 分词,索引在启动时从全部 chunk 构建。

## 性能基线

在 easy 语料 54 个 chunk 上,纯向量检索 p50 约 45 毫秒;混合检索 p50 约 60 毫秒;叠加 bge-reranker-v2-m3 后整条检索链 p50 约 300 毫秒(不含首次模型加载)。

## 故障排查

连接被拒绝时先运行 scripts/start_db.sh;缺少 vector 扩展时执行 CREATE EXTENSION vector;collection 不存在时先运行 ingest.py。
