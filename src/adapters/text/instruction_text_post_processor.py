from __future__ import annotations

import re

from src.adapters.logging_utils import get_adapter_logger


class InstructionTextPostProcessor:
    A_TOKEN = r"(?:a|\u00e0|\u00c3\u00a0|\u00c3\u0192\u00c2\u00a0)"

    def __init__(self) -> None:
        self._logger = get_adapter_logger("instruction_text_post_processor")
        self._logger.info("init.success")

    def process(self, text: str) -> str:
        self._logger.info("process.start chars=%s", len(text or ""))
        if not text:
            self._logger.info("process.success chars=0 empty=true")
            return ""

        formatted = self._normalize_mojibake(text)
        if not self._has_dictation_markers(formatted):
            return formatted.strip()

        # Basic dictation instructions.
        formatted = re.sub(r"\bpoint\s+virgule\b", ";", formatted, flags=re.IGNORECASE)
        formatted = re.sub(r"\bdeux\s+points\b", ":", formatted, flags=re.IGNORECASE)
        formatted = re.sub(r"\bvirgule\b", ",", formatted, flags=re.IGNORECASE)
        formatted = re.sub(r"\bpoint\s+d[' ]interrogation\b", "?", formatted, flags=re.IGNORECASE)
        formatted = re.sub(r"\bpoint\s+d[' ]exclamation\b", "!", formatted, flags=re.IGNORECASE)

        # Newline instructions.
        formatted = re.sub(
            rf"\bpoint\s*,?\s*{self.A_TOKEN}\s+la\s+ligne\s*,?\s*[.;:!?]?",
            ".\n\n",
            formatted,
            flags=re.IGNORECASE,
        )
        formatted = re.sub(
            rf"\bpoint\s*,?\s*(?:retour\s+)?{self.A_TOKEN}\s+la\s+ligne\s*,?\s*[.;:!?]?",
            ".\n\n",
            formatted,
            flags=re.IGNORECASE,
        )
        formatted = re.sub(
            rf"\b(?:retour\s+)?{self.A_TOKEN}\s+la\s+ligne\s*,?\s*[.;:!?]?",
            "\n\n",
            formatted,
            flags=re.IGNORECASE,
        )
        formatted = re.sub(r"\bnouveau\s+paragraphe\b", "\n\n", formatted, flags=re.IGNORECASE)

        # Remaining standalone "point".
        formatted = re.sub(
            rf"\bpoint\b(?!\s*,?\s*(?:retour\s+)?{self.A_TOKEN}\s+la\s+ligne)",
            ".",
            formatted,
            flags=re.IGNORECASE,
        )

        # Cleanup punctuation duplicates.
        formatted = re.sub(r"\.\s*point\b", ".", formatted, flags=re.IGNORECASE)
        formatted = re.sub(r",\s*virgule\b", ",", formatted, flags=re.IGNORECASE)
        formatted = re.sub(r"\?\s*point\s+d[' ]interrogation\b", "?", formatted, flags=re.IGNORECASE)
        formatted = re.sub(r"!\s*point\s+d[' ]exclamation\b", "!", formatted, flags=re.IGNORECASE)
        formatted = re.sub(r",\s*point\b", ".", formatted, flags=re.IGNORECASE)

        formatted = re.sub(r"\.[ \t]*\.[ \t]*", ".", formatted)
        formatted = re.sub(r",[ \t]*,[ \t]*", ",", formatted)
        formatted = re.sub(r"\?[ \t]*\?[ \t]*", "?", formatted)
        formatted = re.sub(r"![ \t]*![ \t]*", "!", formatted)
        formatted = re.sub(r"\.[ \t]*,", ".", formatted)
        formatted = re.sub(r"\.[ \t]+\.", ".", formatted)
        formatted = re.sub(r",[ \t]*\.", ".", formatted)
        formatted = re.sub(r";[ \t]*\.", ".", formatted)
        formatted = re.sub(r"\n\n\.", "\n\n", formatted)

        # Spacing and line formatting.
        formatted = re.sub(r"([,;:!?])(?=[^\s\n])", r"\1 ", formatted)
        formatted = re.sub(r"\.(?=[^\s\n])", ". ", formatted)
        formatted = re.sub(r"\s+([,;:.!?])", r"\1", formatted)

        paragraphs = formatted.split("\n\n")
        unique_paragraphs: list[str] = []
        previous: str | None = None
        for paragraph in paragraphs:
            candidate = paragraph.strip()
            if not candidate:
                continue
            if candidate == previous:
                continue
            unique_paragraphs.append(candidate)
            previous = candidate
        formatted = "\n\n".join(unique_paragraphs)

        formatted = formatted.replace("\r\n", "\n")
        formatted = re.sub(r"[ \t]+", " ", formatted)
        formatted = re.sub(r"[ \t]*\n[ \t]*", "\n", formatted)
        formatted = re.sub(r"\n{3,}", "\n\n", formatted)
        formatted = self._capitalize_sentences(formatted.strip())
        self._logger.info("process.success chars=%s has_markers=%s", len(formatted), self._has_dictation_markers(text))
        return formatted

    @classmethod
    def _has_dictation_markers(cls, text: str) -> bool:
        lower = text.lower()
        markers = [
            r"\bpoint\b",
            r"\bvirgule\b",
            r"\bdeux\s+points\b",
            r"\bpoint\s+virgule\b",
            r"\bpoint\s+d[' ]interrogation\b",
            r"\bpoint\s+d[' ]exclamation\b",
            rf"\b{cls.A_TOKEN}\s+la\s+ligne\b",
            rf"\bretour\s+{cls.A_TOKEN}\s+la\s+ligne\b",
            r"\bnouveau\s+paragraphe\b",
        ]
        return any(re.search(pattern, lower, flags=re.IGNORECASE) for pattern in markers)

    @staticmethod
    def _normalize_mojibake(text: str) -> str:
        # Repair common UTF-8/Latin-1 mojibake if present.
        if "\u00c3" not in text:
            return text
        try:
            return text.encode("latin-1").decode("utf-8")
        except UnicodeError:
            return text

    @staticmethod
    def _capitalize_sentences(text: str) -> str:
        def capitalize_match(match: re.Match[str]) -> str:
            prefix = match.group(1)
            char = match.group(2)
            return f"{prefix}{char.upper()}"

        return re.sub(r"(^|[.!?]\s+|\n+)([a-z\u00e0-\u00ff])", capitalize_match, text)
