import pytest

from src.application.services.opencart_matcher import OpenCartImageMatcher
from src.domain.entities.opencart_image_match import OpenCartMatchSettings


def make_matcher() -> OpenCartImageMatcher:
    return OpenCartImageMatcher()


def test_parse_products_accepts_common_separators():
    matcher = make_matcher()

    products, errors = matcher.parse_products("123\tABC-001\n124;ABC-002\n125,ABC-003\n126   ABC-004")

    assert errors == []
    assert [(p.product_id, p.sku) for p in products] == [
        (123, "ABC-001"),
        (124, "ABC-002"),
        (125, "ABC-003"),
        (126, "ABC-004"),
    ]


def test_parse_products_reports_invalid_lines():
    matcher = make_matcher()

    products, errors = matcher.parse_products("123 ABC-001\nbad-line")

    assert [(p.product_id, p.sku) for p in products] == [(123, "ABC-001")]
    assert len(errors) == 1
    assert errors[0].line_number == 2
    assert "product_id" in errors[0].message


def test_parse_files_trims_blank_lines_and_keeps_order():
    matcher = make_matcher()

    files = matcher.parse_files("\nABC001.jpg\n abc-002-main.webp \n")

    assert files == ["ABC001.jpg", "abc-002-main.webp"]


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("ABC-001", "abc001"),
        ("ABC_001.jpg", "abc001"),
        ("abc 001 main.webp", "abc001"),
    ],
)
def test_normalize_for_match(value, expected):
    matcher = make_matcher()

    assert matcher.normalize_for_match(value, ignore_service_words=True) == expected


def test_generate_prefers_normalized_one_to_one_matches():
    matcher = make_matcher()

    report = matcher.generate(
        products_text="123\tABC-001\n124\tDEF-002",
        files_text="ABC001.jpg\nDEF_002.webp",
        image_prefix="catalog/products/import/",
        settings=OpenCartMatchSettings(use_openrouter=False),
    )

    assert [(m.product_id, m.sku, m.filename, m.method.value) for m in report.matches] == [
        (123, "ABC-001", "ABC001.jpg", "normalized"),
        (124, "DEF-002", "DEF_002.webp", "normalized"),
    ]
    assert report.unmatched_products == []
    assert report.unused_files == []
    assert "UPDATE oc_product SET image = 'catalog/products/import/ABC001.jpg' WHERE product_id = 123;" in report.sql


def test_generate_reports_unmatched_products_and_unused_files():
    matcher = make_matcher()

    report = matcher.generate(
        products_text="123\tABC-001\n124\tDEF-002",
        files_text="ABC001.jpg\nZZZ.jpg",
        image_prefix="catalog/products/",
        settings=OpenCartMatchSettings(use_openrouter=False),
    )

    assert [(m.product_id, m.filename) for m in report.matches] == [(123, "ABC001.jpg")]
    assert [(p.product_id, p.sku) for p in report.unmatched_products] == [(124, "DEF-002")]
    assert report.unused_files == ["ZZZ.jpg"]


def test_generate_rejects_duplicate_file_assignment():
    matcher = make_matcher()

    report = matcher.generate(
        products_text="123\tABC-001\n124\tABC001",
        files_text="ABC001.jpg",
        image_prefix="catalog/products/",
        settings=OpenCartMatchSettings(use_openrouter=False),
    )

    assert len(report.matches) == 1
    assert len(report.unmatched_products) == 1
    assert report.conflicts


def test_sql_escapes_single_quotes_in_paths():
    matcher = make_matcher()

    report = matcher.generate(
        products_text="123\tABC-001",
        files_text="ABC001's.jpg",
        image_prefix="catalog/products/",
        settings=OpenCartMatchSettings(use_openrouter=False),
    )

    assert "ABC001''s.jpg" in report.sql
