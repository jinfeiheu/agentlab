"""Postgres 持久化集成测试:默认跳过,设置 RUN_INTEGRATION=1 才运行。"""

import os
import uuid

import pytest
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langgraph.store.postgres import AsyncPostgresStore

import config
from graph import build_graph
from tools import calculator

TEST_DB = os.getenv("TEST_DATABASE_URL") or config.DATABASE_URL

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        os.getenv("RUN_INTEGRATION") != "1",
        reason="需要真实 Postgres;设置 RUN_INTEGRATION=1 后运行",
    ),
]


class ScriptedModel(BaseChatModel):
    """固定返回预设 AI 消息,避免调用真实模型。"""

    responses: list[AIMessage]
    calls: int = 0

    @property
    def _llm_type(self) -> str:
        return "scripted"

    def bind_tools(self, tools, **kwargs):
        return self

    def _generate(self, messages, stop=None, run_manager=None, **kwargs):
        message = self.responses[self.calls % len(self.responses)]
        self.calls += 1
        return ChatResult(generations=[ChatGeneration(message=message)])


def _thread_config() -> dict:
    """每次运行使用唯一 thread_id,避免历史 checkpoint 干扰断言。"""
    return {"configurable": {"thread_id": f"persist-{uuid.uuid4().hex}"}}


def build_test_graph(checkpointer=None, store=None):
    """用真实 build_graph + 脚本模型,只考验持久化层。"""
    model = ScriptedModel(responses=[AIMessage(content="持久化测试回答")])
    return build_graph(model, [calculator], checkpointer=checkpointer, store=store)


def graph_compiled_with(saver):
    """模拟新进程:用新的 saver 重新编译同一张图。"""
    return build_test_graph(checkpointer=saver)


async def test_async_saver_persists_thread():
    cfg = _thread_config()
    async with AsyncPostgresSaver.from_conn_string(TEST_DB) as saver:
        await saver.setup()
        graph = build_test_graph(checkpointer=saver)
        await graph.ainvoke({"messages": [("user", "hi")]}, cfg)
    async with AsyncPostgresSaver.from_conn_string(TEST_DB) as saver2:
        state = await graph_compiled_with(saver2).aget_state(cfg)
    assert state.values["messages"]
    assert state.values["messages"][-1].content == "持久化测试回答"


async def test_async_store_persists_items():
    namespace = ("tests", "persistence", uuid.uuid4().hex)
    async with AsyncPostgresStore.from_conn_string(TEST_DB) as store:
        await store.setup()
        await store.aput(namespace, "greeting", {"text": "你好"})
    async with AsyncPostgresStore.from_conn_string(TEST_DB) as store2:
        item = await store2.aget(namespace, "greeting")
    assert item is not None
    assert item.value == {"text": "你好"}


async def test_postgres_store_isolates_users():
    """AsyncPostgresStore 的前缀搜索不能跨 user 命名空间。"""
    from langgraph.store.postgres.aio import PostgresIndexConfig

    from tests.fakes import FakeEmbeddings

    suffix = uuid.uuid4().hex
    alice = f"user_alice_{suffix}"
    bob = f"user_bob_{suffix}"
    index = PostgresIndexConfig(
        dims=config.EMBED_DIMS,
        embed=FakeEmbeddings(config.EMBED_DIMS),
    )
    async with AsyncPostgresStore.from_conn_string(
        TEST_DB, index=index
    ) as store:
        await store.setup()
        await store.aput(("user", alice, "profile"), "name", {"value": "小明"})
        alice_items = await store.asearch(
            ("user", alice), query="名字", limit=5
        )
        bob_items = await store.asearch(
            ("user", bob), query="名字", limit=5
        )
        assert any(item.value.get("value") == "小明" for item in alice_items)
        assert bob_items == []
        await store.adelete(("user", alice, "profile"), "name")


async def test_build_services_persists_across_instances(monkeypatch):
    """USE_DB=true 时服务使用 Postgres;新实例仍能读到旧会话。"""
    import api
    from tests.fakes import FakeRetriever

    monkeypatch.setattr(api, "USE_DB", True)
    monkeypatch.setattr(api, "DATABASE_URL", TEST_DB)
    monkeypatch.setattr(
        api,
        "build_chat_model",
        lambda **kwargs: ScriptedModel(
            responses=[AIMessage(content="持久化测试回答")]
        ),
    )
    monkeypatch.setattr(
        api, "build_inmemory_retriever", lambda docs_dir: FakeRetriever([])
    )
    cfg = _thread_config()
    first = await api.build_services()
    try:
        await first.db_check()
        await first.graph.ainvoke({"messages": [("user", "hi")]}, cfg)
    finally:
        await first.aclose()
    second = await api.build_services()
    try:
        state = await second.graph.aget_state(cfg)
    finally:
        await second.aclose()
    assert state.values["messages"][-1].content == "持久化测试回答"
