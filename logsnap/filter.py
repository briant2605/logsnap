"""Pattern-based line filter for log streams."""

import re
from typing import Iterable, Iterator, List, Optional


class LineFilter:
    """Filters log lines by one or more regex patterns.

    A line is accepted if it matches ALL include patterns and NONE of the
    exclude patterns.
    """

    def __init__(
        self,
        include: Optional[List[str]] = None,
        exclude: Optional[List[str]] = None,
        case_sensitive: bool = True,
    ) -> None:
        flags = 0 if case_sensitive else re.IGNORECASE
        self._include = [re.compile(p, flags) for p in (include or [])]
        self._exclude = [re.compile(p, flags) for p in (exclude or [])]

    def matches(self, line: str) -> bool:
        """Return True if *line* passes the filter criteria."""
        for pattern in self._exclude:
            if pattern.search(line):
                return False
        for pattern in self._include:
            if not pattern.search(line):
                return False
        return True

    def apply(self, lines: Iterable[str]) -> Iterator[str]:
        """Yield only lines that pass the filter."""
        for line in lines:
            if self.matches(line):
                yield line

    def __repr__(self) -> str:
        inc = [p.pattern for p in self._include]
        exc = [p.pattern for p in self._exclude]
        return f"LineFilter(include={inc}, exclude={exc})"
