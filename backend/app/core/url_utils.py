from app.core.logging import get_logger
from fastapi import Request

logger = get_logger("app.core.url_utils")


def get_base_url(request: Request) -> str:
    """
    Get the base URL for the application, respecting proxy headers.

    This function checks for X-Forwarded-Proto header to determine if the
    original request was HTTPS (when behind a reverse proxy like nginx).

    Args:
        request: FastAPI Request object

    Returns:
        Base URL with correct scheme (http/https)
    """
    # Check if we're behind a proxy with forwarded protocol
    forwarded_proto = request.headers.get("x-forwarded-proto", "").lower()

    if forwarded_proto == "https":
        scheme = "https"
        logger.debug("Using HTTPS scheme from X-Forwarded-Proto header")
    elif forwarded_proto == "http":
        scheme = "http"
        logger.debug("Using HTTP scheme from X-Forwarded-Proto header")
    else:
        # Fall back to request URL scheme
        scheme = request.url.scheme
        logger.debug(f"Using scheme from request URL: {scheme}")

    # Get host from headers (forwarded) or request
    host = request.headers.get("host", request.url.hostname)
    if request.url.port and request.url.port not in (80, 443):
        host = f"{host}:{request.url.port}"

    base_url = f"{scheme}://{host}"
    logger.debug(f"Generated base URL: {base_url}")

    return base_url


def build_url(request: Request, endpoint_name: str, **path_params) -> str:
    """
    Build a URL for an endpoint, respecting proxy headers for HTTPS.

    Args:
        request: FastAPI Request object
        endpoint_name: Name of the endpoint to generate URL for
        **path_params: Path parameters for the URL

    Returns:
        Complete URL with correct scheme
    """
    # Generate the URL using FastAPI's url_for
    url = request.url_for(endpoint_name, **path_params)

    # Check if we need to modify the scheme
    forwarded_proto = request.headers.get("x-forwarded-proto", "").lower()

    if forwarded_proto == "https" and url.scheme == "http":
        # Replace http with https
        https_url = url.replace(scheme="https")
        logger.debug(f"Converted URL from HTTP to HTTPS: {url} -> {https_url}")
        return str(https_url)

    logger.debug(f"Generated URL: {url}")
    return str(url)
