from app.llm import factory


def test_singleton():
    """
    Ensures factory caches provider instance.
    """

    assert hasattr(factory, "_client")


def test_provider_constant():
    assert isinstance(factory.LLM_PROVIDER, str)