from app.prompts.analyze import SYSTEM_PROMPT, USER_PROMPT_TEMPLATE


def test_analyze_prompts_are_separate_from_services() -> None:
    assert "structured report" in USER_PROMPT_TEMPLATE
    assert "executive_summary" in USER_PROMPT_TEMPLATE
    assert "document analyst" in SYSTEM_PROMPT


def test_user_prompt_template_formats_document_text() -> None:
    prompt = USER_PROMPT_TEMPLATE.format(document_text="Sample contract")
    assert "Sample contract" in prompt
