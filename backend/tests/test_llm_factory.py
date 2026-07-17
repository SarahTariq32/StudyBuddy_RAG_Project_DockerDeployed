import pytest

from app.llm import factory


def test_cached_client(mocker):
    fake = object()

    factory._client = fake

    assert factory.get_llm_client() is fake

    factory._client = None


def test_unknown_provider(mocker):
    factory._client = None

    mocker.patch.object(
        factory,
        "LLM_PROVIDER",
        "unknown",
    )

    with pytest.raises(ValueError):
        factory.get_llm_client()

    factory._client = None