"""One regression detector for the skill-frontmatter audit."""


def make_skill(tmp_path, name, frontmatter_body, body=None):
    d = tmp_path / name
    d.mkdir()
    body_text = body if body is not None else f"\n\n# {name}\n"
    (d / "SKILL.md").write_text(f"---\n{frontmatter_body}\n---\n{body_text}")
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


def test_audit_flags_skill_too_long(tmp_path, load_script):
    app = load_script("claude-skill-audit")
    long_body = "\n" + "\n".join(f"line {i}" for i in range(600)) + "\n"
    make_skill(tmp_path, "long-skill",
               'name: long-skill\ndescription: "Use when the user needs this for long documents across cases."',
               body=long_body)

    report = app.build_report(tmp_path, min_words=6)

    errors_section = report.split("## Errors")[1].split("## Warnings")[0]
    assert "skill_too_long" in errors_section
    assert "long-skill" in errors_section


def test_audit_flags_forbidden_doc_files(tmp_path, load_script):
    app = load_script("claude-skill-audit")
    d = make_skill(tmp_path, "docs-skill",
                    'name: docs-skill\ndescription: "Use when the user wants this thing across many scenarios."')
    (d / "README.md").write_text("hi")
    (d / "CHANGELOG.md").write_text("hi")

    report = app.build_report(tmp_path, min_words=6)

    errors_section = report.split("## Errors")[1].split("## Warnings")[0]
    assert "forbidden_doc_file" in errors_section
    assert "README.md" in errors_section
    assert "CHANGELOG.md" in errors_section


def test_audit_flags_bad_and_nested_subdirectories(tmp_path, load_script):
    app = load_script("claude-skill-audit")
    d = make_skill(tmp_path, "struct-skill",
                    'name: struct-skill\ndescription: "Use when the user wants this thing across many scenarios."')
    (d / "extra").mkdir()
    (d / "references").mkdir()
    (d / "references" / "nested").mkdir()

    report = app.build_report(tmp_path, min_words=6)

    errors_section = report.split("## Errors")[1].split("## Warnings")[0]
    assert "bad_subdirectory" in errors_section and "extra" in errors_section
    assert "nested_subdirectory" in errors_section and "nested" in errors_section


def test_audit_reports_error_handling_summary_count(tmp_path, load_script):
    app = load_script("claude-skill-audit")
    make_skill(tmp_path, "with-eh",
               'name: with-eh\ndescription: "Use when the user wants this thing across many scenarios."',
               body="\n\n## Error Handling\nDo the thing.\n")
    make_skill(tmp_path, "without-eh",
               'name: without-eh\ndescription: "Use when the user wants this other thing across scenarios."',
               body="\n\n## Steps\nDo the thing.\n")

    report = app.build_report(tmp_path, min_words=6)

    assert "1/2 skills have an Error Handling section" in report


def test_audit_flags_first_person_body_prose(tmp_path, load_script):
    app = load_script("claude-skill-audit")
    make_skill(tmp_path, "chatty-body",
               'name: chatty-body\ndescription: "Use when the user wants this thing across many scenarios."',
               body="\n\nYou should run your own checks. I will not help you otherwise.\n")

    report = app.build_report(tmp_path, min_words=6)

    warns_section = report.split("## Warnings")[1].split("## Overlap")[0]
    assert "first_person_body" in warns_section
    assert "chatty-body" in warns_section


def test_audit_flags_missing_jit_instruction(tmp_path, load_script):
    app = load_script("claude-skill-audit")
    body = "\n\nSee references/auth-flow.md for the error codes.\nMore context in references/notes.md.\n"
    make_skill(tmp_path, "jit-skill",
               'name: jit-skill\ndescription: "Use when the user wants this thing across many scenarios."',
               body=body)

    report = app.build_report(tmp_path, min_words=6)

    warns_section = report.split("## Warnings")[1].split("## Overlap")[0]
    assert warns_section.count("missing_jit_instruction") == 1
    assert "notes.md" in warns_section
    assert "auth-flow.md" not in warns_section
