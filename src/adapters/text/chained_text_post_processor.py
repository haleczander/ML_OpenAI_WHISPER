from __future__ import annotations

from src.application.ports import TextPostProcessorPort


class ChainedTextPostProcessor:
    def __init__(self, *processors: TextPostProcessorPort) -> None:
        self._processors = processors

    def process(self, text: str) -> str:
        current = text
        for processor in self._processors:
            current = processor.process(current)
        return current
