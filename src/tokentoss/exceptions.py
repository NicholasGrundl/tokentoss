"""Custom exceptions for tokentoss."""


class TokenTossError(Exception):
    """Base exception for tokentoss."""

    pass


class NoCredentialsError(TokenTossError):
    """Raised when no valid credentials are found.

    This typically means:
    - No AuthManager was passed to IAPClient
    - tokentoss.CREDENTIALS module variable is not set
    - No token file exists at the default location
    - TOKENTOSS_TOKEN_FILE environment variable is not set or file doesn't exist

    To authenticate, use the GoogleAuthWidget:
        from tokentoss import GoogleAuthWidget
        widget = GoogleAuthWidget(client_secrets_path="./client_secrets.json")
        display(widget)
        # Click "Sign in with Google" and complete the flow
    """

    def __init__(self, message: str | None = None):
        if message is None:
            message = (
                "No valid credentials found. "
                "Use GoogleAuthWidget to authenticate or provide credentials explicitly."
            )
        super().__init__(message)


class TokenRefreshError(TokenTossError):
    """Raised when token refresh fails."""

    pass


class TokenExchangeError(TokenTossError):
    """Raised when authorization code exchange fails."""

    pass


class StorageError(TokenTossError):
    """Raised when token storage operations fail."""

    pass


class InsecureFilePermissionsWarning(UserWarning):
    """Warning issued when token file has insecure permissions."""

    pass
