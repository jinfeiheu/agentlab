import time

import jwt as pyjwt
import pytest

from auth import DEMO_USERS, login, sign_token, verify_token

TEST_SECRET = "test-secret-0123456789abcdef0123456789"


def test_token_is_standard_jwt():
    token = sign_token("alice", secret=TEST_SECRET)
    assert len(token.split(".")) == 3
    header = pyjwt.get_unverified_header(token)
    assert header["alg"] == "HS256"
    assert header["typ"] == "JWT"
    claims = pyjwt.decode(token, TEST_SECRET, algorithms=["HS256"])
    assert claims["sub"] == "alice"
    assert claims["exp"] > time.time()


def test_login_valid_and_invalid():
    assert login("alice", "alice-pass") is not None
    assert login("alice", "wrong") is None


def test_demo_users_map_to_expected_ids():
    assert DEMO_USERS["alice"].user_id == "user_alice"
    assert DEMO_USERS["bob"].user_id == "user_bob"
    assert DEMO_USERS["carol"].user_id == "user_carol"


def test_all_demo_users_can_login():
    for username, user_id in (
        ("bob", "user_bob"),
        ("carol", "user_carol"),
    ):
        token = login(username, f"{username}-pass")
        assert token is not None
        assert verify_token(token) == user_id


def test_token_roundtrip():
    token = sign_token("alice", secret=TEST_SECRET)
    assert verify_token(token, secret=TEST_SECRET) == "alice"


def test_tampered_token_rejected():
    token = sign_token("alice", secret=TEST_SECRET)
    with pytest.raises(ValueError):
        verify_token(token + "x", secret=TEST_SECRET)


def test_expired_token_rejected():
    token = sign_token("alice", secret=TEST_SECRET, ttl_seconds=-1)
    with pytest.raises(ValueError):
        verify_token(token, secret=TEST_SECRET)
