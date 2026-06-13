from morning_paper.models import RENDER_SCHEMA_VERSION
from morning_paper.sample import sample_render_document


def test_sample_document_builds_for_each_theme():
    for theme in ("times-classic", "economist", "nyt-modern", "mono-minimal"):
        doc = sample_render_document(theme)
        assert doc.theme_id == theme
        assert doc.schema_version == RENDER_SCHEMA_VERSION
        # every grid slot resolves to a story view
        slot_ids = {s.story_id for s in doc.grid_plan.slots}
        assert slot_ids == set(doc.stories.keys())


def test_images_only_for_photo_slots():
    doc = sample_render_document("times-classic")
    photo_slot_ids = {s.story_id for s in doc.grid_plan.slots if s.with_photo}
    # images map keys are a subset of stories flagged with a photo
    for slot in doc.grid_plan.slots:
        view = doc.stories[slot.story_id]
        if not slot.with_photo:
            assert view.image_ref is None
    assert set(doc.images.keys()).issubset(photo_slot_ids | {None})


def test_masthead_populated():
    doc = sample_render_document("nyt-modern")
    assert doc.masthead.title == "The Morning Paper"
    assert doc.masthead.date  # ISO date string
