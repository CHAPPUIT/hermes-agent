"""PII anonymization/deanonymization — French-first, regex-based, no external deps."""

import re
from dataclasses import dataclass, field


@dataclass
class AnonymizationResult:
    anonymized_text: str
    entity_map: dict  # {placeholder: {"original": str, "type": str}}


class ConfidentialityLayer:
    # Order matters: longer/more specific patterns first to avoid partial matches
    PATTERNS = [
        ("NIR", r"\b[12]\s?\d{2}\s?\d{2}\s?\d{2}\s?\d{3}\s?\d{3}\s?\d{2}\b"),
        ("SIRET", r"\b\d{3}\s?\d{3}\s?\d{3}\s?\d{5}\b"),
        ("SIREN", r"\b\d{3}\s?\d{3}\s?\d{3}\b"),
        ("IBAN", r"\bFR\d{2}\s?\d{4}\s?\d{4}\s?\d{4}\s?\d{4}\s?\d{4}\s?\d{3}\b"),
        ("PHONE", r"\b(?:0|\+33\s?)[1-9](?:[\s.-]?\d{2}){4}\b"),
        ("EMAIL", r"\b[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\b"),
    ]

    def anonymize(self, text: str) -> AnonymizationResult:
        entity_map: dict[str, dict] = {}
        result = text
        counters: dict[str, int] = {}

        for entity_type, pattern in self.PATTERNS:
            for match in re.finditer(pattern, result):
                original = match.group()
                # Skip if already mapped
                if original in [v["original"] for v in entity_map.values()]:
                    continue
                counters[entity_type] = counters.get(entity_type, 0) + 1
                placeholder = f"[{entity_type}_{counters[entity_type]}]"
                entity_map[placeholder] = {"original": original, "type": entity_type}
                result = result.replace(original, placeholder)

        return AnonymizationResult(anonymized_text=result, entity_map=entity_map)

    def deanonymize(self, text: str, entity_map: dict) -> str:
        result = text
        for placeholder, meta in entity_map.items():
            result = result.replace(placeholder, meta["original"])
        return result
