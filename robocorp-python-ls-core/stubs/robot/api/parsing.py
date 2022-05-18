from typing import Tuple, Optional, List
from robot.api import Token


class LibraryImport:
    type: str

    @property
    def name(self) -> Optional[str]:
        pass

    @property
    def args(self) -> Tuple[str, ...]:
        pass

    @property
    def alias(self) -> Optional[str]:
        pass

    lineno: int
    end_lineno: int
    col_offset: int
    end_col_offset: int
    tokens: List[Token]

    def get_token(self, name: str) -> Optional[Token]:
        pass

    def get_tokens(self, name: str) -> List[Token]:
        pass
