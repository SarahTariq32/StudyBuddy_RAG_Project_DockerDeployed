from unittest.mock import MagicMock

from app.routes import chat


def test_follow_up_detection():
    assert chat._looks_like_follow_up("What are its advantages?")
    assert chat._looks_like_follow_up("How can I learn it?")
    assert chat._looks_like_follow_up("Why is that?")
    assert not chat._looks_like_follow_up("Explain machine learning.")


def test_last_user_message():
    history = [
        {"role": "user", "message": "What is AI?"},
        {"role": "assistant", "message": "Artificial Intelligence..."},
        {"role": "user", "message": "Explain neural networks"},
    ]

    result = chat._last_user_message(history, "What are its advantages?")
    assert result == "Explain neural networks"


def test_rewrite_with_history():
    history = [
        {"role": "user", "message": "Explain Docker"},
    ]

    rewritten = chat._rewrite_with_history(
        "What are its advantages?",
        history,
    )

    assert "about: Explain Docker" in rewritten


def test_answer_outcome_answered():
    result = chat._answer_outcome(
        "Docker is a container platform.",
        5,
    )

    assert result == "answered"


def test_answer_outcome_no_context():
    result = chat._answer_outcome(
        "Some answer",
        0,
    )

    assert result == "answer_without_context"


def test_answer_outcome_empty():
    result = chat._answer_outcome("", 2)

    assert result == "empty"


def test_new_stage_state():
    stages = chat._new_stage_state()

    assert len(stages) == 5

    for stage in stages.values():
        assert stage["status"] == "skipped"
        assert stage["execution_status"] == "Skipped"


def test_set_stage_completed():
    stages = chat._new_stage_state()

    chat._set_stage_completed(
        stages,
        "retrieval",
        latency_ms=150,
        outcome="success",
    )

    assert stages["retrieval"]["status"] == "success"
    assert stages["retrieval"]["latency_ms"] == 150
    assert stages["retrieval"]["outcome"] == "success"


def test_set_stage_failed():
    stages = chat._new_stage_state()

    chat._set_stage_failed(
        stages,
        "embedding",
        reason="Embedding API failed",
        latency_ms=50,
    )

    assert stages["embedding"]["status"] == "failed"
    assert stages["embedding"]["failure_reason"] == "Embedding API failed"
    assert stages["embedding"]["latency_ms"] == 50