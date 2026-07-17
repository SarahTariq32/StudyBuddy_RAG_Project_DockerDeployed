import pytest

from app.rag.chunking import create_parent_chunks, create_child_chunks


def test_parent_chunks_created():
    text = "A" * 1000

    chunks = create_parent_chunks(text, 200, 50)

    assert len(chunks) > 1
    assert chunks[0] == text[:200]


def test_invalid_parent_size():
    with pytest.raises(ValueError):
        create_parent_chunks("abc", 0, 0)


def test_invalid_overlap():
    with pytest.raises(ValueError):
        create_parent_chunks("abc", 100, 100)


def test_child_chunks_created():
    parents = ["A" * 300]

    children, mapping = create_child_chunks(parents, 100, 20)

    assert len(children) == len(mapping)
    assert mapping[0] == 0


def test_invalid_child_size():
    with pytest.raises(ValueError):
        create_child_chunks(["abc"], 0, 0)