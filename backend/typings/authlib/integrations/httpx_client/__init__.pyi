"""Types for authlib's httpx2 integration, as far as ``app.auth.oidc`` uses it.

authlib ships no types of its own, so Pyright falls back to the typeshed stubs.
Those leave out that ``OAuth2Client`` inherits from ``httpx2.Client``, because
typeshed must not depend on httpx, and so Pyright rejects
``with OAuth2Client(...)`` although it works. This stub adds the base class
back. Every other authlib module keeps its typeshed stub.
"""

import httpx2
from authlib.integrations.base_client import OAuthError as OAuthError
from authlib.oauth2.client import OAuth2Client as _OAuth2Client

class OAuth2Client(_OAuth2Client, httpx2.Client):
    def __init__(
        self,
        client_id=None,
        client_secret=None,
        token_endpoint_auth_method=None,
        revocation_endpoint_auth_method=None,
        scope=None,
        redirect_uri=None,
        token=None,
        token_placement: str = "header",
        update_token=None,
        **kwargs,
    ) -> None: ...
