"""Turn low-level exceptions into messages that say what failed and how to fix it."""

from botocore.exceptions import (
    ClientError,
    ConnectTimeoutError,
    EndpointConnectionError,
    NoCredentialsError,
    ReadTimeoutError,
)

_CREDENTIAL_CODES = {
    "ExpiredTokenException",
    "UnrecognizedClientException",
    "InvalidSignatureException",
    "IncompleteSignature",
}


def _root_causes(exc: BaseException):
    """Yield the exception and everything it was raised from."""
    seen: set[int] = set()
    current: BaseException | None = exc
    while current is not None and id(current) not in seen:
        seen.add(id(current))
        yield current
        current = current.__cause__ or current.__context__


def describe_error(exc: BaseException) -> str:
    for err in _root_causes(exc):
        if isinstance(err, EndpointConnectionError | ConnectTimeoutError):
            return "Couldn't reach Amazon Bedrock. Check your internet connection (or VPN/proxy), then retry."
        if isinstance(err, ReadTimeoutError):
            return "Amazon Bedrock took too long to respond. Retry in a moment."
        if isinstance(err, NoCredentialsError):
            return (
                "No AWS credentials found. Set AWS_BEARER_TOKEN_BEDROCK in backend/.env "
                "(or run `aws configure`), then restart the API."
            )
        if isinstance(err, ClientError):
            code = err.response.get("Error", {}).get("Code", "")
            message = err.response.get("Error", {}).get("Message", "")
            if code in _CREDENTIAL_CODES:
                return (
                    "Bedrock rejected the credentials (expired or invalid). Create a new API key, "
                    "update AWS_BEARER_TOKEN_BEDROCK in backend/.env and restart the API."
                )
            if code == "AccessDeniedException":
                return (
                    "Bedrock denied access to the model. Enable model access in the Bedrock console "
                    f"(us-east-1) and check your IAM permissions. Details: {message}"
                )
            if code in {"ThrottlingException", "ServiceQuotaExceededException"}:
                return "Bedrock is throttling requests. Wait a minute, then retry."
            return f"Bedrock returned {code}: {message}"
    return f"Unexpected {type(exc).__name__}: {str(exc)[:200]}. Check the API logs for details."
