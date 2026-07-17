import os

from app import config


def test_default_env():
    value = config.get_env_var(
        "THIS_VARIABLE_DOES_NOT_EXIST",
        "default",
    )

    assert value == "default"


def test_existing_env(monkeypatch):
    monkeypatch.setenv(
        "TEST_ENV",
        "hello",
    )

    value = config.get_env_var("TEST_ENV")

    assert value == "hello"


def test_empty_env(monkeypatch):
    monkeypatch.setenv(
        "EMPTY_VAR",
        "",
    )

    value = config.get_env_var(
        "EMPTY_VAR",
        "fallback",
    )

    assert value == "fallback"


def test_chunk_sizes():
    assert config.PARENT_CHUNK_SIZE > 0
    assert config.CHILD_CHUNK_SIZE > 0
    assert config.CHUNK_OVERLAP >= 0


def test_limits():
    assert config.MAX_PDFS > 0
    assert config.MAX_FILE_SIZE_MB > 0