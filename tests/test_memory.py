from langchain_core.messages import AIMessage, HumanMessage
from langgraph.store.memory import InMemoryStore

from agentlab.security.auth import UserContext
from agentlab.agent.memory import (
    MemoryItem,
    detect_memory_candidate,
    extract_memories,
    load_profile,
    maybe_extract_and_save,
    messages_used_save_memory,
    save_episode,
    save_memory,
    search_memory,
    summarize_and_save,
    upsert_memory,
)
from tests.fakes import (
    FailingRunnable,
    FakeEmbeddings,
    FakeRuntime,
    FakeRunnable,
)


def make_store() -> InMemoryStore:
    return InMemoryStore(index={"embed": FakeEmbeddings(dim=4), "dims": 4})


def test_save_and_search_memory_same_user():
    store = make_store()
    runtime = FakeRuntime(UserContext(user_id="user_alice"), store=store)
    save_memory.func("name", "小明", runtime)
    assert "小明" in search_memory.func("名字", runtime)


def test_memory_persists_across_sessions():
    store = make_store()
    save_memory.func(
        "name",
        "小明",
        FakeRuntime(UserContext(user_id="user_alice"), store=store),
    )
    other_session = FakeRuntime(UserContext(user_id="user_alice"), store=store)
    assert "小明" in search_memory.func("名字", other_session)


def test_memory_isolated_between_users():
    store = make_store()
    save_memory.func(
        "name",
        "小明",
        FakeRuntime(UserContext(user_id="user_alice"), store=store),
    )
    out = search_memory.func(
        "名字", FakeRuntime(UserContext(user_id="user_bob"), store=store)
    )
    assert "小明" not in out


def test_memory_tools_report_disabled_without_store():
    runtime = FakeRuntime(UserContext(user_id="user_alice"), store=None)
    assert "未启用" in save_memory.func("name", "小明", runtime)
    assert "未启用" in search_memory.func("name", runtime)


def test_search_memory_returns_no_match_message():
    store = make_store()
    runtime = FakeRuntime(UserContext(user_id="user_alice"), store=store)
    assert "没有找到" in search_memory.func("不存在", runtime)


def test_summarize_and_save_stores_episode():
    store = make_store()
    model = FakeRunnable(AIMessage(content="用户叫小明"))
    summarize_and_save(
        model,
        store,
        "user_alice",
        [HumanMessage(content="我叫小明")],
        thread_id="thread-1",
    )
    items = store.search(
        ("user", "user_alice", "episode"), query="小明", limit=5
    )
    episodes = [item for item in items if item.key.startswith("episode:")]
    assert episodes
    assert "小明" in episodes[0].value["value"]


def test_summarize_and_save_ignores_missing_store():
    summarize_and_save(
        FakeRunnable(AIMessage(content="x")),
        None,
        "user_alice",
        [HumanMessage(content="hi")],
    )


def test_detect_memory_candidate():
    assert detect_memory_candidate("请记住我的名字叫小明")
    assert detect_memory_candidate("以后都用中文回答")
    assert detect_memory_candidate("我最喜欢的颜色是蓝色")
    assert detect_memory_candidate("I prefer dark mode, remember that")
    assert not detect_memory_candidate("checkpointer 是什么")


def test_extract_memories_parses_json_and_normalizes_key():
    model = FakeRunnable(
        AIMessage(
            content=(
                '{"memories":[{"type":"profile","key":"name",'
                '"value":"小明","confidence":0.9}]}'
            )
        )
    )
    items = extract_memories(model, "我叫小明")
    assert len(items) == 1
    assert items[0].type == "profile"
    assert items[0].key == "profile.name"
    assert items[0].value == "小明"


def test_extract_memories_invalid_json_returns_empty():
    model = FakeRunnable(AIMessage(content="这不是 JSON"))
    assert extract_memories(model, "我叫小明") == []


def test_upsert_memory_updates_same_key():
    store = make_store()
    upsert_memory(store, "user_alice", MemoryItem("fact", "fact.city", "杭州"))
    upsert_memory(store, "user_alice", MemoryItem("fact", "fact.city", "上海"))
    items = store.search(("user", "user_alice", "fact"), query="城市", limit=5)
    assert len(items) == 1
    assert items[0].value["value"] == "上海"


def test_upsert_memory_dedupes_same_value_under_new_key():
    store = make_store()
    upsert_memory(store, "user_alice", MemoryItem("fact", "fact.city", "杭州"))
    result = upsert_memory(
        store, "user_alice", MemoryItem("fact", "fact.location", "杭州")
    )
    items = store.search(("user", "user_alice", "fact"), query="杭州", limit=5)
    assert len(items) == 1
    assert items[0].key == "fact.city"
    assert "已合并" in result


def test_save_memory_infers_profile_and_preference_types():
    store = make_store()
    runtime = FakeRuntime(UserContext(user_id="user_alice"), store=store)
    save_memory.func("name", "小明", runtime)
    save_memory.func("color", "蓝色", runtime)
    profile = store.search(
        ("user", "user_alice", "profile"), query="小明", limit=5
    )
    preference = store.search(
        ("user", "user_alice", "preference"), query="蓝色", limit=5
    )
    assert profile and profile[0].key == "profile.name"
    assert preference and preference[0].key == "preference.color"


def test_load_profile_formats_profile_items():
    store = make_store()
    upsert_memory(
        store, "user_alice", MemoryItem("profile", "profile.name", "小明")
    )
    out = load_profile(store, "user_alice")
    assert "profile.name" in out
    assert "小明" in out


class TTLStore:
    supports_ttl = True

    def __init__(self):
        self.puts = []

    def search(self, *args, **kwargs):
        return []

    def put(self, *args, **kwargs):
        self.puts.append((args, kwargs))


def test_upsert_memory_passes_ttl_in_minutes():
    store = TTLStore()
    upsert_memory(
        store,
        "user_alice",
        MemoryItem(
            "episode", "episode:t1", "摘要", ttl_minutes=5
        ),
    )
    assert store.puts
    assert store.puts[0][1]["ttl"] == 5


def test_save_episode_upserts_per_thread():
    store = make_store()
    save_episode(store, "user_alice", "第一版摘要", thread_id="t1")
    save_episode(store, "user_alice", "第二版摘要", thread_id="t1")
    items = store.search(
        ("user", "user_alice", "episode"), query="摘要", limit=5
    )
    assert len(items) == 1
    assert items[0].value["value"] == "第二版摘要"


def test_maybe_extract_and_save_skips_non_candidate():
    store = make_store()
    result = maybe_extract_and_save(
        FailingRunnable(), store, "user_alice", "checkpointer 是什么"
    )
    assert result == []


def test_maybe_extract_and_save_writes_candidate():
    store = make_store()
    model = FakeRunnable(
        AIMessage(
            content=(
                '{"memories":[{"type":"profile","key":"name",'
                '"value":"小明","confidence":0.9}]}'
            )
        )
    )
    result = maybe_extract_and_save(model, store, "user_alice", "我叫小明")
    assert len(result) == 1
    items = store.search(("user", "user_alice", "profile"), query="小明", limit=5)
    assert items
    assert items[0].value["value"] == "小明"


def test_messages_used_save_memory():
    call = AIMessage(
        content="",
        tool_calls=[
            {"name": "save_memory", "args": {"key": "name"}, "id": "m1"}
        ],
    )
    assert messages_used_save_memory([call])
    assert not messages_used_save_memory([HumanMessage(content="hi")])
