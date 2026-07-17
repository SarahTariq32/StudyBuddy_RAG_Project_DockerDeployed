from app.rag import query_rewrite


def test_zero_queries():
    assert query_rewrite.generate_multi_queries("AI", 0) == []


def test_llm_rewrites(mocker):
    client = mocker.Mock()

    client.generate.return_value = (
        "Explain AI\n"
        "Define AI\n"
        "AI meaning"
    )

    mocker.patch(
        "app.rag.query_rewrite.get_llm_client",
        return_value=client,
    )

    result = query_rewrite.generate_multi_queries(
        "AI",
        3,
    )

    assert len(result) == 3


def test_fallback_used(mocker):
    client = mocker.Mock()

    client.generate.return_value = ""

    mocker.patch(
        "app.rag.query_rewrite.get_llm_client",
        return_value=client,
    )

    result = query_rewrite.generate_multi_queries(
        "Docker",
        3,
    )

    assert len(result) > 0