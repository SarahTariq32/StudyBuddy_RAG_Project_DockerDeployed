from app.rag import generator


def test_small_talk():
    reply = generator.non_rag_reply_for_small_talk("hi")

    assert "Hi!" in reply


def test_unknown_not_small_talk():
    assert (
        generator.non_rag_reply_for_small_talk(
            "Explain transformers"
        )
        is None
    )


def test_prompt_contains_context():
    prompt = generator.build_prompt(
        "What is AI?",
        [{"text": "Artificial Intelligence", "source": "book.pdf"}],
        [],
    )

    assert "Artificial Intelligence" in prompt
    assert "book.pdf" in prompt


def test_generate_answer(mocker):
    fake = mocker.Mock()

    fake.generate_with_meta.return_value = {
        "text": "Answer",
        "token_usage": {},
        "model": "test",
    }

    mocker.patch(
        "app.rag.generator.get_llm_client",
        return_value=fake,
    )

    result = generator.generate_answer_with_meta(
        "AI",
        [],
        [],
    )

    assert result["answer"] == "Answer"