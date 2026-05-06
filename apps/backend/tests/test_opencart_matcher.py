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
        files_text="ABC001-main.jpg\nDEF_002_product.webp",
        image_prefix="catalog/products/import/",
        settings=OpenCartMatchSettings(use_openrouter=False),
    )

    assert [(m.product_id, m.sku, m.filename, m.method.value) for m in report.matches] == [
        (123, "ABC-001", "ABC001-main.jpg", "normalized"),
        (124, "DEF-002", "DEF_002_product.webp", "normalized"),
    ]
    assert report.unmatched_products == []
    assert report.unused_files == []
    assert "UPDATE oc_product SET image = 'catalog/products/import/ABC001-main.jpg' WHERE product_id = 123;" in report.sql


def test_generate_uses_exact_match_when_source_keys_match():
    matcher = make_matcher()

    report = matcher.generate(
        products_text="123\tABC-001-main",
        files_text="ABC-001-main.jpg",
        image_prefix="catalog/products/",
        settings=OpenCartMatchSettings(use_openrouter=False),
    )

    assert [(m.product_id, m.sku, m.filename, m.method.value, m.confidence) for m in report.matches] == [
        (123, "ABC-001-main", "ABC-001-main.jpg", "exact", 1.0),
    ]
    assert report.unmatched_products == []
    assert report.unused_files == []


def test_generate_uses_fuzzy_match_above_threshold():
    matcher = make_matcher()

    report = matcher.generate(
        products_text="123\tABC-001",
        files_text="ABC-001A.jpg",
        image_prefix="catalog/products/",
        settings=OpenCartMatchSettings(use_openrouter=False, fuzzy_threshold=0.8),
    )

    assert [(m.product_id, m.sku, m.filename, m.method.value) for m in report.matches] == [
        (123, "ABC-001", "ABC-001A.jpg", "fuzzy"),
    ]
    assert report.matches[0].confidence >= 0.8
    assert report.unmatched_products == []
    assert report.unused_files == []


def test_generate_applies_and_validates_llm_matches():
    matcher = make_matcher()

    report = matcher.generate(
        products_text="200\tSUN-100\n201\tOAK-200\n202\tPINE-300\n203\tRAIN-400",
        files_text="moon-photo.jpg\nvalid-second.jpg",
        image_prefix="catalog/products/",
        settings=OpenCartMatchSettings(use_openrouter=True, fuzzy_threshold=0.78),
        llm_matches=[
            {"product_id": 200, "filename": "moon-photo.jpg", "confidence": 0.91, "reason": "visual fit"},
            {"product_id": 201, "filename": "moon-photo.jpg", "confidence": 0.9, "reason": "duplicate"},
            {"product_id": 202, "filename": "missing.jpg", "confidence": 0.9, "reason": "missing"},
            {"product_id": 999, "filename": "valid-second.jpg", "confidence": 0.9, "reason": "unknown"},
            {"product_id": 203, "filename": "valid-second.jpg", "confidence": 0.5, "reason": "too low"},
        ],
    )

    assert [(m.product_id, m.sku, m.filename, m.method.value, m.confidence, m.reason) for m in report.matches] == [
        (200, "SUN-100", "moon-photo.jpg", "llm", 0.91, "visual fit"),
    ]
    assert [(p.product_id, p.sku) for p in report.unmatched_products] == [
        (201, "OAK-200"),
        (202, "PINE-300"),
        (203, "RAIN-400"),
    ]
    assert report.unused_files == ["valid-second.jpg"]
    assert {(c.product_id, c.filename, c.message) for c in report.conflicts} == {
        (201, "moon-photo.jpg", "LLM reused a file"),
        (202, "missing.jpg", "LLM referenced unknown file"),
        (None, "valid-second.jpg", "LLM referenced unknown product_id"),
        (203, "valid-second.jpg", "LLM confidence below threshold"),
    }


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

    assert [(m.product_id, m.sku, m.filename, m.method.value) for m in report.matches] == [
        (123, "ABC-001", "ABC001.jpg", "exact"),
    ]
    assert [(p.product_id, p.sku) for p in report.unmatched_products] == [(124, "ABC001")]
    assert len(report.conflicts) == 1
    conflict = report.conflicts[0]
    assert (conflict.product_id, conflict.sku, conflict.filename) == (124, "ABC001", "ABC001.jpg")
    assert any(word in conflict.message.lower() for word in ["already", "duplicate", "reused"])
    assert report.sql.count("UPDATE oc_product SET image =") == 1


def test_sql_includes_comment_update_and_escapes_single_quotes():
    matcher = make_matcher()

    report = matcher.generate(
        products_text="123\tABC-001's",
        files_text="ABC001's.jpg",
        image_prefix="catalog/products/",
        settings=OpenCartMatchSettings(use_openrouter=False),
    )

    assert "-- SKU: ABC-001''s, file: ABC001''s.jpg, method: exact" in report.sql
    assert "UPDATE oc_product SET image = 'catalog/products/ABC001''s.jpg' WHERE product_id = 123;" in report.sql
    assert "ABC001''s.jpg" in report.sql
    assert "catalog/products/ABC001's.jpg" not in report.sql
    assert report.sql.count("UPDATE oc_product SET image =") == 1
