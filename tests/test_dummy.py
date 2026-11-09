from coverage_isolate.dummy import answer


def test_answer_returns_placeholder() -> None:
    assert answer() == 42
