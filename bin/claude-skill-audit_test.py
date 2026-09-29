"""One regression detector for the skill-frontmatter audit."""


def make_skill(tmp_path, name, frontmatter_body):
    d = tmp_path / name
    d.mkdir()
    (d / "SKILL.md").write_text(f"---\n{frontmatter_body}\n---\n\n# {name}\n")
    return d


def test_audit_flags_missing_thin_first_person_and_overlap(tmp_path, load_script):
    app = load_script("claude-skill-audit")

    make_skill(tmp_path, "good-skill",
               'name: good-skill\ndescription: "Use when the user asks for this thing across several scenarios and cases."')
    make_skill(tmp_path, "no-description", "name: no-description")
    make_skill(tmp_path, "thin-skill", 'name: thin-skill\ndescription: "Does stuff."')
    make_skill(tmp_path, "chatty-skill",
               'name: chatty-skill\ndescription: "I will help you do your task, use your own judgement."')
    make_skill(tmp_path, "paseo", 'name: paseo\ndescription: "Use when managing paseo projects and workspaces."')
    make_skill(tmp_path, "paseo-advisor",
               'name: paseo-advisor\ndescription: "Use when advising on paseo workspace configuration."')

    report = app.build_report(tmp_path, min_words=6)

    assert "no-description" in report and "missing_description" in report
    assert "thin-skill" in report and "thin_description" in report
    assert "chatty-skill" in report and "first_person" in report
    assert "**paseo**: paseo, paseo-advisor" in report
    assert "good-skill" not in report.split("## Errors")[1].split("## Warnings")[0]


def test_audit_reports_zero_issues_for_clean_directory(tmp_path, load_script):
    app = load_script("claude-skill-audit")
    make_skill(tmp_path, "good-skill",
               'name: good-skill\ndescription: "Use when the user asks for this thing across several scenarios."')

    report = app.build_report(tmp_path, min_words=6)

    assert "0 errors, 0 warnings" in report
