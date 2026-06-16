from morning_paper.models import GridPlan, GridSlot


def test_valid_plan_has_no_violations():
    plan = GridPlan(
        page_format="a4",
        slots=[
            GridSlot(story_id="a", section="world", size="lead", columns=4),
            GridSlot(story_id="b", section="world", size="medium", columns=2),
        ],
    )
    assert plan.validate_against_theme(columns=4, max_lead=1) == []


def test_too_many_leads_flagged():
    plan = GridPlan(
        slots=[
            GridSlot(story_id="a", section="world", size="lead", columns=3),
            GridSlot(story_id="b", section="world", size="lead", columns=3),
        ]
    )
    problems = plan.validate_against_theme(columns=6, max_lead=1)
    assert any("lead" in p for p in problems)


def test_column_overflow_flagged():
    plan = GridPlan(slots=[GridSlot(story_id="a", section="world", size="medium", columns=8)])
    problems = plan.validate_against_theme(columns=4, max_lead=1)
    assert any("columns" in p for p in problems)
