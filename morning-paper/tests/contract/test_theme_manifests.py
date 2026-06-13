"""Every theme manifest must validate against the schema, and every bundled font
must declare a license (so we never ship an unlicensed font)."""

import pytest

from morning_paper.render.themes import list_theme_ids, load_manifest

THEME_IDS = list_theme_ids()


def test_some_themes_exist():
    assert THEME_IDS, "no themes found under themes/"


@pytest.mark.parametrize("theme_id", THEME_IDS)
def test_manifest_validates(theme_id):
    m = load_manifest(theme_id)
    assert m.id == theme_id
    assert m.type.body_font
    assert m.grid.columns >= 1
    assert m.grid.max_lead >= 1


@pytest.mark.parametrize("theme_id", THEME_IDS)
def test_every_font_has_license(theme_id):
    m = load_manifest(theme_id)
    for font in m.fonts:
        assert font.license, f"{theme_id}: font {font.family} missing license"
        assert font.files, f"{theme_id}: font {font.family} declares no files"


@pytest.mark.parametrize("theme_id", THEME_IDS)
def test_css_variables_cover_core_keys(theme_id):
    m = load_manifest(theme_id)
    css_vars = m.css_variables()
    for key in ("--paper", "--ink", "--body-font", "--columns"):
        assert key in css_vars
