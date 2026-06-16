from morning_paper.retrieval.dedup import dedup_candidates
from morning_paper.retrieval.feeds import Candidate


def _c(id: str, title: str, score: float = 0.5) -> Candidate:
    return Candidate(
        id=id,
        title=title,
        body="",
        url="",
        lang="en",
        source="test",
        published_at="",
        score=score,
    )


def test_dedup_removes_near_duplicate():
    a = _c("a", "Apple announces new iPhone model", 0.9)
    b = _c("b", "Apple announces new iPhone model today", 0.5)
    result = dedup_candidates([a, b])
    assert len(result) == 1
    assert result[0].id == "a"


def test_dedup_keeps_different():
    a = _c("a", "Apple announces iPhone")
    b = _c("b", "Samsung releases Galaxy phone")
    assert len(dedup_candidates([a, b])) == 2


def test_dedup_empty():
    assert dedup_candidates([]) == []


def test_dedup_single():
    a = _c("a", "Some headline")
    assert dedup_candidates([a]) == [a]


def test_dedup_keeps_higher_score():
    low = _c("low", "Breaking news about technology today", 0.2)
    high = _c("high", "Breaking news about technology today right now", 0.8)
    result = dedup_candidates([low, high])
    assert len(result) == 1
    assert result[0].id == "high"
