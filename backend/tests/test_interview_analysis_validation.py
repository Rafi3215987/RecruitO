from app.graphs.interview_analysis_graph import route_extended
from app.services.interview_analysis import validate_interview_analysis

REQUIREMENTS = [{"text": "Python"}, {"text": "SQL"}]


def _answer(**overrides):
    answer = {"relevance": 4, "accuracy": 4, "completeness": 4, "articulation": 4}
    answer.update(overrides)
    return answer


def test_passes_when_complete_and_high_quality():
    analysis = {"answers": [_answer(), _answer()], "never_explored_requirements": []}
    report = validate_interview_analysis(analysis, REQUIREMENTS)
    assert report["status"] == "passed"
    assert report["reasons"] == []
    assert report["requirement_coverage"] == 1.0


def test_fails_when_no_answers():
    analysis = {"answers": [], "never_explored_requirements": REQUIREMENTS}
    report = validate_interview_analysis(analysis, REQUIREMENTS)
    assert report["status"] == "insufficient"
    assert "insufficient_answers" in report["reasons"]


def test_fails_on_low_requirement_coverage():
    requirements = [{"text": "Python"}, {"text": "SQL"}, {"text": "Docker"}]
    analysis = {
        "answers": [_answer()],
        "never_explored_requirements": [
            {"requirement_index": 1, "requirement": "SQL"},
            {"requirement_index": 2, "requirement": "Docker"},
        ],
    }
    report = validate_interview_analysis(analysis, requirements)
    assert report["status"] == "insufficient"
    assert "low_requirement_coverage" in report["reasons"]


def test_fails_on_low_quality_scores():
    weak = _answer(relevance=1, accuracy=1, completeness=1, articulation=1)
    analysis = {"answers": [weak, weak], "never_explored_requirements": []}
    report = validate_interview_analysis(analysis, REQUIREMENTS)
    assert report["status"] == "insufficient"
    assert "low_quality_scores" in report["reasons"]


def test_route_skips_extended_when_validation_insufficient():
    state = {"validation": {"status": "insufficient"}, "resume_text": "resume"}
    assert route_extended(state) == "__end__"


def test_route_runs_extended_when_passed_and_resume_present():
    state = {"validation": {"status": "passed"}, "resume_text": "resume"}
    assert route_extended(state) == "evaluate_f8_f9_f10"
