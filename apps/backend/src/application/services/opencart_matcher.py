from __future__ import annotations

import json
import re
from difflib import SequenceMatcher
from pathlib import PurePosixPath, PureWindowsPath
from typing import Any

from src.domain.entities.opencart_image_match import (
    OpenCartImageMatch,
    OpenCartMatchConflict,
    OpenCartMatchMethod,
    OpenCartMatchReport,
    OpenCartMatchSettings,
    OpenCartParseError,
    OpenCartProductInput,
)


class OpenCartImageMatcher:
    _service_words = {"main", "photo", "image", "img", "foto", "product"}
    _product_splitter = re.compile(r"^\s*(\d+)\s*(?:[\t;,]|\s+)\s*(\S.*?)\s*$")

    def parse_products(self, products_text: str) -> tuple[list[OpenCartProductInput], list[OpenCartParseError]]:
        products: list[OpenCartProductInput] = []
        errors: list[OpenCartParseError] = []

        for line_number, raw_line in enumerate(products_text.splitlines(), start=1):
            line = raw_line.strip()
            if not line:
                continue

            match = self._product_splitter.match(line)
            if not match:
                errors.append(
                    OpenCartParseError(
                        line_number=line_number,
                        line=raw_line,
                        message="Expected numeric product_id followed by SKU",
                    )
                )
                continue

            products.append(
                OpenCartProductInput(
                    product_id=int(match.group(1)),
                    sku=match.group(2).strip(),
                    line_number=line_number,
                )
            )

        return products, errors

    def parse_files(self, files_text: str) -> list[str]:
        return [line.strip() for line in files_text.splitlines() if line.strip()]

    def normalize_for_match(self, value: str, *, ignore_service_words: bool = True) -> str:
        stem = self._filename_stem(value)
        parts = re.findall(r"[a-z0-9]+", stem.lower())
        if ignore_service_words:
            parts = [part for part in parts if part not in self._service_words]
        return "".join(parts)

    def generate(
        self,
        products_text: str,
        files_text: str,
        image_prefix: str,
        settings: OpenCartMatchSettings,
        llm_matches: list[dict[str, Any]] | None = None,
    ) -> OpenCartMatchReport:
        products, parse_errors = self.parse_products(products_text)
        files = self.parse_files(files_text)

        report = OpenCartMatchReport(parse_errors=parse_errors)
        matched_product_ids: set[int] = set()
        used_files: set[str] = set()

        self._match_by_key(
            products=products,
            files=files,
            image_prefix=image_prefix,
            report=report,
            matched_product_ids=matched_product_ids,
            used_files=used_files,
            method=OpenCartMatchMethod.EXACT,
            ignore_service_words=False,
        )
        self._match_by_key(
            products=products,
            files=files,
            image_prefix=image_prefix,
            report=report,
            matched_product_ids=matched_product_ids,
            used_files=used_files,
            method=OpenCartMatchMethod.NORMALIZED,
            ignore_service_words=settings.ignore_service_words,
        )
        self._match_fuzzy(
            products=products,
            files=files,
            settings=settings,
            image_prefix=image_prefix,
            report=report,
            matched_product_ids=matched_product_ids,
            used_files=used_files,
        )

        if llm_matches:
            self._apply_llm_matches(
                products=products,
                files=files,
                settings=settings,
                image_prefix=image_prefix,
                llm_matches=llm_matches,
                report=report,
                matched_product_ids=matched_product_ids,
                used_files=used_files,
            )

        report.unmatched_products = [product for product in products if product.product_id not in matched_product_ids]
        report.unused_files = [filename for filename in files if filename not in used_files]
        report.low_confidence_matches = [
            match for match in report.matches if match.confidence < settings.low_confidence_threshold
        ]
        report.sql = self.generate_sql(report.matches)
        return report

    def generate_sql(self, matches: list[OpenCartImageMatch]) -> str:
        lines: list[str] = []
        for match in matches:
            lines.append(
                f"-- SKU: {self._escape_sql(match.sku)}, file: {self._escape_sql(match.filename)}, "
                f"method: {match.method.value}"
            )
            lines.append(
                "UPDATE oc_product SET image = "
                f"'{self._escape_sql(match.image_path)}' WHERE product_id = {match.product_id};"
            )
        return "\n".join(lines)

    def parse_llm_json(self, value: str) -> list[dict[str, Any]]:
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError:
            parsed = self._extract_json_array(value)
        if isinstance(parsed, dict):
            parsed = parsed.get("matches", [])
        if not isinstance(parsed, list):
            return []
        return [item for item in parsed if isinstance(item, dict)]

    def _match_by_key(
        self,
        *,
        products: list[OpenCartProductInput],
        files: list[str],
        image_prefix: str,
        report: OpenCartMatchReport,
        matched_product_ids: set[int],
        used_files: set[str],
        method: OpenCartMatchMethod,
        ignore_service_words: bool,
    ) -> None:
        file_keys = {filename: self.normalize_for_match(filename, ignore_service_words=ignore_service_words) for filename in files}

        for product in products:
            if product.product_id in matched_product_ids:
                continue

            product_key = self.normalize_for_match(product.sku, ignore_service_words=ignore_service_words)
            matching_files = [filename for filename in files if file_keys[filename] == product_key]
            available_files = [filename for filename in matching_files if filename not in used_files]

            if len(available_files) == 1:
                self._add_match(
                    report=report,
                    product=product,
                    filename=available_files[0],
                    image_prefix=image_prefix,
                    method=method,
                    confidence=1.0,
                    reason=f"{method.value} key match",
                    matched_product_ids=matched_product_ids,
                    used_files=used_files,
                )
            elif len(available_files) > 1:
                report.conflicts.append(
                    OpenCartMatchConflict(
                        product_id=product.product_id,
                        sku=product.sku,
                        filename=", ".join(available_files),
                        message="Multiple files match product key",
                    )
                )
            elif matching_files:
                self._add_conflict_once(
                    report,
                    OpenCartMatchConflict(
                        product_id=product.product_id,
                        sku=product.sku,
                        filename=matching_files[0],
                        message="File already matched by another product",
                    ),
                )

    def _match_fuzzy(
        self,
        *,
        products: list[OpenCartProductInput],
        files: list[str],
        settings: OpenCartMatchSettings,
        image_prefix: str,
        report: OpenCartMatchReport,
        matched_product_ids: set[int],
        used_files: set[str],
    ) -> None:
        for product in products:
            if product.product_id in matched_product_ids:
                continue

            product_key = self.normalize_for_match(product.sku, ignore_service_words=settings.ignore_service_words)
            scored = [
                (
                    SequenceMatcher(
                        None,
                        product_key,
                        self.normalize_for_match(filename, ignore_service_words=settings.ignore_service_words),
                    ).ratio(),
                    filename,
                )
                for filename in files
                if filename not in used_files
            ]
            candidates = [(score, filename) for score, filename in scored if score >= settings.fuzzy_threshold]
            if not candidates:
                continue

            best_score = max(score for score, _filename in candidates)
            best_files = [filename for score, filename in candidates if score == best_score]
            if len(best_files) > 1:
                report.conflicts.append(
                    OpenCartMatchConflict(
                        product_id=product.product_id,
                        sku=product.sku,
                        filename=", ".join(best_files),
                        message="Multiple fuzzy files tied for product",
                    )
                )
                continue

            self._add_match(
                report=report,
                product=product,
                filename=best_files[0],
                image_prefix=image_prefix,
                method=OpenCartMatchMethod.FUZZY,
                confidence=best_score,
                reason="fuzzy key match",
                matched_product_ids=matched_product_ids,
                used_files=used_files,
            )

    def _apply_llm_matches(
        self,
        *,
        products: list[OpenCartProductInput],
        files: list[str],
        settings: OpenCartMatchSettings,
        image_prefix: str,
        llm_matches: list[dict[str, Any]],
        report: OpenCartMatchReport,
        matched_product_ids: set[int],
        used_files: set[str],
    ) -> None:
        products_by_id = {product.product_id: product for product in products}
        known_files = set(files)

        for row in llm_matches:
            product_id = row.get("product_id")
            filename = row.get("filename")
            confidence = float(row.get("confidence", 0.0) or 0.0)
            product = products_by_id.get(product_id)

            if product is None:
                report.conflicts.append(
                    OpenCartMatchConflict(
                        product_id=None,
                        sku=None,
                        filename=filename,
                        message="LLM referenced unknown product_id",
                    )
                )
            elif filename not in known_files:
                report.conflicts.append(
                    OpenCartMatchConflict(
                        product_id=product.product_id,
                        sku=product.sku,
                        filename=filename,
                        message="LLM referenced unknown file",
                    )
                )
            elif product.product_id in matched_product_ids:
                report.conflicts.append(
                    OpenCartMatchConflict(
                        product_id=product.product_id,
                        sku=product.sku,
                        filename=filename,
                        message="LLM referenced already matched product",
                    )
                )
            elif filename in used_files:
                report.conflicts.append(
                    OpenCartMatchConflict(
                        product_id=product.product_id,
                        sku=product.sku,
                        filename=filename,
                        message="LLM reused a file",
                    )
                )
            elif confidence < settings.fuzzy_threshold:
                report.conflicts.append(
                    OpenCartMatchConflict(
                        product_id=product.product_id,
                        sku=product.sku,
                        filename=filename,
                        message="LLM confidence below threshold",
                    )
                )
            else:
                self._add_match(
                    report=report,
                    product=product,
                    filename=filename,
                    image_prefix=image_prefix,
                    method=OpenCartMatchMethod.LLM,
                    confidence=confidence,
                    reason=str(row.get("reason") or ""),
                    matched_product_ids=matched_product_ids,
                    used_files=used_files,
                )

    def _add_match(
        self,
        *,
        report: OpenCartMatchReport,
        product: OpenCartProductInput,
        filename: str,
        image_prefix: str,
        method: OpenCartMatchMethod,
        confidence: float,
        reason: str,
        matched_product_ids: set[int],
        used_files: set[str],
    ) -> None:
        report.matches.append(
            OpenCartImageMatch(
                product_id=product.product_id,
                sku=product.sku,
                filename=filename,
                image_path=self._join_image_path(image_prefix, filename),
                method=method,
                confidence=confidence,
                reason=reason,
            )
        )
        matched_product_ids.add(product.product_id)
        used_files.add(filename)

    def _add_conflict_once(self, report: OpenCartMatchReport, conflict: OpenCartMatchConflict) -> None:
        key = (conflict.product_id, conflict.sku, conflict.filename, conflict.message)
        if any((item.product_id, item.sku, item.filename, item.message) == key for item in report.conflicts):
            return
        report.conflicts.append(conflict)

    def _filename_stem(self, value: str) -> str:
        normalized = value.strip().replace("\\", "/")
        filename = PurePosixPath(normalized).name
        windows_name = PureWindowsPath(filename).name
        return windows_name.rsplit(".", 1)[0] if "." in windows_name else windows_name

    def _join_image_path(self, image_prefix: str, filename: str) -> str:
        return f"{image_prefix.rstrip('/')}/{filename}"

    def _extract_json_array(self, value: str) -> Any:
        start = value.find("[")
        end = value.rfind("]")
        if start == -1 or end == -1 or end < start:
            return []
        try:
            return json.loads(value[start : end + 1])
        except json.JSONDecodeError:
            return []

    def _escape_sql(self, value: str) -> str:
        return value.replace("'", "''")
