import pytest

from app.rag import embeddings


def test_empty_embeddings():
    assert embeddings.create_embeddings([]) == []


def test_embedding_generation(mocker):
    fake = mocker.Mock()

    fake.return_value = [[1.0, 2.0, 3.0]]

    mocker.patch.object(
        embeddings,
        "_embedder",
        fake,
    )

    result = embeddings.create_embeddings(["hello"])

    assert len(result) == 1
    assert result[0] == [1.0, 2.0, 3.0]


def test_retry_failure(mocker):
    fake = mocker.Mock(side_effect=Exception("failed"))

    mocker.patch.object(
        embeddings,
        "_embedder",
        fake,
    )

    with pytest.raises(RuntimeError):
        embeddings.create_embeddings(["hello"])