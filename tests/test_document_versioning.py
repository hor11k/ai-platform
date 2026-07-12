from app.core.document_versioning import (
    extract_file_date,
    extract_version_number,
    is_exact_filename_match,
    version_group_key,
)


def test_version_group_key_groups_versions() -> None:
    older = version_group_key("20200828 Справка -МСТК УК Динамо.docx")
    newer = version_group_key("20200828 Справка -МСТК УК Динамо_v_3.docx")
    assert older == newer


def test_extract_file_date_and_version() -> None:
    assert extract_file_date("20230419 Справка _МСТК Динамо ФИНАЛ[1].docx") == 20230419
    assert extract_file_date("Договор займа Химки 2024.docx") == 20241231
    assert extract_version_number("20200828 Справка -МСТК УК Динамо_v_3.docx") == 3


def test_exact_filename_match_requires_all_terms() -> None:
    assert is_exact_filename_match(
        "Договор займа Химки 2024.docx",
        ["договор", "химки"],
    )
    assert not is_exact_filename_match(
        "Договор займа Химки 2024.docx",
        ["договор", "втб"],
    )
