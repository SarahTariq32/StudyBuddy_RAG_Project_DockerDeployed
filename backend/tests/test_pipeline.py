import pytest

from app.rag import pipeline


def test_empty_question():
    result = pipeline.retrieve_context_with_debug("")

    assert result["context"] == []
    assert result["rewrites"] == []
    assert result["retrieval_hits"] == []
    assert result["multi_query_used"] is False


def test_ranked_hits(mocker):
    mocker.patch(
        "app.rag.pipeline.create_embeddings",
        return_value=[[1.0, 2.0]],
    )

    mocker.patch(
        "app.rag.pipeline.vector_store.search",
        return_value=[
            {
                "parent_text": "Python is a language.",
                "source": "python.pdf",
                "distance": 0.12,
            }
        ],
    )

    parents, debug = pipeline._ranked_parent_hits(
        ["Python"],
        set(),
    )

    assert len(parents) == 1
    assert parents[0]["source"] == "python.pdf"
    assert len(debug) == 1


def test_duplicate_removed(mocker):
    mocker.patch(
        "app.rag.pipeline.create_embeddings",
        return_value=[[1.0]],
    )

    mocker.patch(
        "app.rag.pipeline.vector_store.search",
        return_value=[
            {
                "parent_text": "Duplicate",
                "source": "a.pdf",
                "distance": 0.1,
            },
            {
                "parent_text": "Duplicate",
                "source": "a.pdf",
                "distance": 0.2,
            },
        ],
    )

    parents, _ = pipeline._ranked_parent_hits(
        ["AI"],
        set(),
    )

    assert len(parents) == 1


def test_distance_filter(mocker):
    mocker.patch(
        "app.rag.pipeline.create_embeddings",
        return_value=[[1.0]],
    )

    mocker.patch(
        "app.rag.pipeline.vector_store.search",
        return_value=[
            {
                "parent_text": "Far away",
                "source": "doc.pdf",
                "distance": 999,
            }
        ],
    )

    parents, _ = pipeline._ranked_parent_hits(
        ["AI"],
        set(),
    )

    assert parents == []


def test_direct_retrieval_only(mocker):
    mocker.patch(
        "app.rag.pipeline._ranked_parent_hits",
        return_value=(
            [
                {
                    "text": "Context",
                    "source": "book.pdf",
                }
            ],
            [],
        ),
    )

    result = pipeline.retrieve_context_with_debug(
        "Explain AI"
    )

    assert result["context"][0]["source"] == "book.pdf"