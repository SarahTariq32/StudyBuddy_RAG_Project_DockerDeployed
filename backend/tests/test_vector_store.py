from app.rag import vector_store


def test_search_empty_collection(mocker):
    collection = mocker.Mock()

    collection.count.return_value = 0

    mocker.patch.object(
        vector_store,
        "_collection",
        collection,
    )

    assert vector_store.search([1, 2], 5) == []


def test_search_results(mocker):
    collection = mocker.Mock()

    collection.count.return_value = 1

    collection.query.return_value = {
        "metadatas": [[
            {
                "doc_id": "1",
                "source": "book.pdf",
                "parent_text": "Python",
            }
        ]],
        "distances": [[0.1]],
    }

    mocker.patch.object(
        vector_store,
        "_collection",
        collection,
    )

    result = vector_store.search(
        [1, 2],
        5,
    )

    assert len(result) == 1
    assert result[0]["source"] == "book.pdf"
    assert result[0]["distance"] == 0.1


def test_missing_source(mocker):
    collection = mocker.Mock()

    collection.count.return_value = 1

    collection.query.return_value = {
        "metadatas": [[
            {
                "doc_id": "ABC",
                "parent_text": "Python",
            }
        ]],
        "distances": [[0.2]],
    }

    mocker.patch.object(
        vector_store,
        "_collection",
        collection,
    )

    result = vector_store.search(
        [1],
        2,
    )

    assert result[0]["source"] == "ABC"


def test_add_chunks(mocker):
    collection = mocker.Mock()

    mocker.patch.object(
        vector_store,
        "_collection",
        collection,
    )

    vector_store.add_chunks(
        "doc1",
        "book.pdf",
        ["child"],
        ["parent"],
        [0],
        [[1.0, 2.0]],
    )

    collection.add.assert_called_once()


def test_delete_document(mocker):
    collection = mocker.Mock()

    mocker.patch.object(
        vector_store,
        "_collection",
        collection,
    )

    vector_store.delete_document("123")

    collection.delete.assert_called_once_with(
        where={"doc_id": "123"}
    )