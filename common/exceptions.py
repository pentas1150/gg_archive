"""
Custom exceptions for the application.
"""
from common.const import TypeErrorCode


class ReplayAnalysisError(Exception):
    """리플레이 분석 관련 예외.

    Attributes:
        error_code: 에러 코드 (TypeErrorCode)
        detail: 상세 정보 (선택)
    """

    def __init__(self, error_code: TypeErrorCode, detail: str = ""):
        self.error_code = error_code
        self.detail = detail
        super().__init__(self._build_message())

    def _build_message(self) -> str:
        """에러 메시지 생성."""
        if self.detail:
            return f"{self.error_code.get_user_message()}: {self.detail}"
        return self.error_code.get_user_message()

    def is_skip(self) -> bool:
        """정상 스킵인지 확인 (편의 메서드)."""
        return self.error_code.is_skip()
