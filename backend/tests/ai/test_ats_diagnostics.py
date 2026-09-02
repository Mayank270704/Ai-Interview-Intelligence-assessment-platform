"""Tests for structured, deterministic ATS diagnostics."""

from app.ai.ats.diagnostics import build_diagnostics
from app.ai.ats.scorer import score_resume
from app.schemas.resume import (
    CandidateIdentity,
    CandidateProfile,
    Claim,
    Education,
    Experience,
    Project,
    Skill,
)


def _profile(**overrides) -> CandidateProfile:
    base = dict(identity=CandidateIdentity(full_name="Jane Doe", email="jane@example.com", phone="555-0100"))
    base.update(overrides)
    return CandidateProfile(**base)


def test_missing_contact_info_is_flagged():
    profile = CandidateProfile(identity=CandidateIdentity(full_name="Jane Doe"))

    diagnostics = build_diagnostics(profile, [])

    matches = [d for d in diagnostics if d.type == "missing_contact_info"]
    assert len(matches) == 1
    assert "email" in matches[0].explanation
    assert "phone" in matches[0].explanation


def test_complete_contact_info_is_not_flagged():
    profile = _profile()

    diagnostics = build_diagnostics(profile, [])

    assert not [d for d in diagnostics if d.type == "missing_contact_info"]


def test_missing_standard_sections_are_reported_per_section():
    section_feedback = [
        "Skills section present.",
        "Missing or empty education section.",
        "Missing or empty projects section.",
    ]

    diagnostics = build_diagnostics(_profile(), section_feedback)

    types = {(d.type, d.section) for d in diagnostics}
    assert ("missing_standard_section", "education") in types
    assert ("missing_standard_section", "projects") in types


def test_date_format_inconsistency_detected_across_experience_entries():
    profile = _profile(
        experience=[
            Experience(company="A", position="Eng", start_date="2019", end_date="2020"),
            Experience(company="B", position="Eng", start_date="Jan 2021", end_date="Present"),
        ]
    )

    diagnostics = build_diagnostics(profile, [])

    matches = [d for d in diagnostics if d.type == "date_format_inconsistency" and d.section == "experience"]
    assert len(matches) == 1


def test_consistent_date_formats_are_not_flagged():
    profile = _profile(
        experience=[
            Experience(company="A", position="Eng", start_date="Jan 2019", end_date="Jan 2020"),
            Experience(company="B", position="Eng", start_date="Feb 2021", end_date="Present"),
        ]
    )

    diagnostics = build_diagnostics(profile, [])

    assert not [d for d in diagnostics if d.type == "date_format_inconsistency"]


def test_single_experience_entry_never_triggers_date_inconsistency():
    profile = _profile(
        experience=[Experience(company="A", position="Eng", start_date="2019", end_date="2020")]
    )

    diagnostics = build_diagnostics(profile, [])

    assert not [d for d in diagnostics if d.type == "date_format_inconsistency"]


def test_duplicate_skills_are_detected():
    profile = _profile(skills=[Skill(name="Python"), Skill(name="python")])

    diagnostics = build_diagnostics(profile, [])

    matches = [d for d in diagnostics if d.type == "duplicate_content" and d.section == "skills"]
    assert len(matches) == 1


def test_duplicate_experience_entries_are_detected():
    profile = _profile(
        experience=[
            Experience(company="Acme", position="Engineer"),
            Experience(company="Acme", position="Engineer"),
        ]
    )

    diagnostics = build_diagnostics(profile, [])

    assert [d for d in diagnostics if d.type == "duplicate_content" and d.section == "experience"]


def test_duplicate_project_names_are_detected():
    profile = _profile(
        projects=[Project(name="Recsys"), Project(name="Recsys")]
    )

    diagnostics = build_diagnostics(profile, [])

    assert [d for d in diagnostics if d.type == "duplicate_content" and d.section == "projects"]


def test_duplicate_claims_are_detected():
    profile = _profile(
        claims=[
            Claim(claim_text="Improved accuracy by 18%", category="quantitative", resume_evidence="e"),
            Claim(claim_text="Improved accuracy by 18%", category="quantitative", resume_evidence="e"),
        ]
    )

    diagnostics = build_diagnostics(profile, [])

    assert [d for d in diagnostics if d.type == "duplicate_content" and d.section == "achievements"]


def test_no_duplicates_produces_no_duplicate_diagnostics():
    profile = _profile(skills=[Skill(name="Python"), Skill(name="Go")])

    diagnostics = build_diagnostics(profile, [])

    assert not [d for d in diagnostics if d.type == "duplicate_content"]


def test_unusual_characters_replacement_char_is_detected():
    profile = _profile(professional_summary="Built a robust� system for data processing.")

    diagnostics = build_diagnostics(profile, [])

    matches = [d for d in diagnostics if d.type == "unusual_characters"]
    assert matches
    assert matches[0].affected_text is not None


def test_clean_text_has_no_unusual_character_diagnostic():
    profile = _profile(professional_summary="A clean, normal professional summary.")

    diagnostics = build_diagnostics(profile, [])

    assert not [d for d in diagnostics if d.type == "unusual_characters"]


def test_broken_bullet_signal_detected_when_glyphs_are_glued_together():
    profile = _profile(
        experience=[
            Experience(
                company="Acme",
                position="Engineer",
                description="•Built the pipeline•Improved latency by 30%•Led the migration",
            )
        ]
    )

    diagnostics = build_diagnostics(profile, [])

    assert [d for d in diagnostics if d.type == "broken_bullet_or_extraction_signal"]


def test_normal_description_has_no_broken_bullet_signal():
    profile = _profile(
        experience=[
            Experience(company="Acme", position="Engineer", description="Built the pipeline and improved latency.")
        ]
    )

    diagnostics = build_diagnostics(profile, [])

    assert not [d for d in diagnostics if d.type == "broken_bullet_or_extraction_signal"]


def test_unclear_experience_structure_flags_incomplete_entries():
    profile = _profile(experience=[Experience(company="Acme", position="Engineer")])

    diagnostics = build_diagnostics(profile, [])

    matches = [d for d in diagnostics if d.type == "unclear_experience_structure"]
    assert matches
    assert "description" in matches[0].explanation


def test_no_experience_does_not_duplicate_the_missing_section_diagnostic():
    """Absence of experience is reported once, via missing_standard_section -- not
    also via a separate, redundant unclear_experience_structure diagnostic."""
    section_feedback = ["Missing or empty experience section."]

    diagnostics = build_diagnostics(_profile(), section_feedback)

    assert not [d for d in diagnostics if d.type == "unclear_experience_structure"]
    assert [
        d for d in diagnostics
        if d.type == "missing_standard_section" and d.section == "experience"
    ]


def test_unclear_project_structure_flags_incomplete_projects():
    profile = _profile(projects=[Project(name="Recsys")])

    diagnostics = build_diagnostics(profile, [])

    matches = [d for d in diagnostics if d.type == "unclear_project_structure"]
    assert matches
    assert "Recsys" in matches[0].affected_text


def test_well_structured_project_is_not_flagged():
    profile = _profile(
        projects=[Project(name="Recsys", description="A recommender.", technologies=["Python"])]
    )

    diagnostics = build_diagnostics(profile, [])

    assert not [d for d in diagnostics if d.type == "unclear_project_structure"]


def test_lack_of_measurable_impact_is_flagged_without_quantitative_claims():
    diagnostics = build_diagnostics(_profile(), [])

    assert [d for d in diagnostics if d.type == "lack_of_measurable_impact"]


def test_measurable_impact_present_suppresses_the_diagnostic():
    profile = _profile(
        claims=[Claim(claim_text="Improved accuracy by 18%", category="quantitative", resume_evidence="e")]
    )

    diagnostics = build_diagnostics(profile, [])

    assert not [d for d in diagnostics if d.type == "lack_of_measurable_impact"]


def test_missing_jd_keywords_and_skills_are_only_present_in_jd_mode():
    readiness_diagnostics = build_diagnostics(_profile(), [])
    jd_diagnostics = build_diagnostics(_profile(), [], missing_keywords=["docker"], missing_skills=["docker"])

    assert not [d for d in readiness_diagnostics if d.type in ("missing_jd_keywords", "missing_jd_skills")]
    assert [d for d in jd_diagnostics if d.type == "missing_jd_keywords"]
    assert [d for d in jd_diagnostics if d.type == "missing_jd_skills"]


def test_every_diagnostic_has_all_required_fields():
    profile = _profile(
        skills=[Skill(name="Python"), Skill(name="Python")],
        experience=[Experience(company="A", position="Eng", start_date="2019", end_date="2020"),
                    Experience(company="B", position="Eng", start_date="Jan 2021", end_date="Present")],
    )

    diagnostics = build_diagnostics(profile, [], missing_keywords=["kubernetes"], missing_skills=["kubernetes"])

    assert diagnostics
    for d in diagnostics:
        assert d.type
        assert d.section
        assert d.explanation
        assert d.actionable_fix


def test_diagnostics_do_not_alter_the_numeric_score():
    """A duplicate that trips a diagnostic but leaves every scored fraction unchanged
    (two identical, fully-complete project entries: completeness stays 1/1 == 2/2)
    must produce the same score as the non-duplicated version."""
    project = Project(name="Recsys", description="A recommender system.", technologies=["Python"])
    base_kwargs = dict(
        professional_summary="Clean summary.",
        skills=[Skill(name="Python")],
        experience=[Experience(company="A", position="Eng", start_date="2019", description="Did things.")],
        education=[Education(institution="MIT")],
        claims=[Claim(claim_text="Improved accuracy by 18%", category="quantitative", resume_evidence="e")],
    )
    clean_profile = _profile(projects=[project], **base_kwargs)
    duplicated_profile = _profile(projects=[project, project.model_copy()], **base_kwargs)

    clean_result = score_resume(clean_profile, None)
    duplicated_result = score_resume(duplicated_profile, None)

    assert any(d.type == "duplicate_content" and d.section == "projects" for d in duplicated_result.diagnostics)
    assert not any(d.type == "duplicate_content" for d in clean_result.diagnostics)
    assert clean_result.ats_score == duplicated_result.ats_score


def test_score_resume_populates_diagnostics_field():
    result = score_resume(_profile(), None)

    assert isinstance(result.diagnostics, list)
    assert result.diagnostics
