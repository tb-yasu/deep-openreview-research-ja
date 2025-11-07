class BaseError(Exception):
    """Custom exception for base errors."""

    def __init__(self, subject: str, object: str, message: str) -> None:
        error_message = f"{subject} | {object} | {message}"
        super().__init__(error_message)


class ApiClientError(Exception):
    """Custom exception for API client errors."""

    def __init__(self, service_name: str, status_code: int, message: str) -> None:
        error_message = f"{service_name} | {status_code} | {message}"
        super().__init__(error_message)


class ChainError(Exception):
    """Custom exception for chain errors."""

    def __init__(self, chain_name: str, message: str) -> None:
        error_message = f"{chain_name} | {message}"
        super().__init__(error_message)
