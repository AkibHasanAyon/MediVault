from urllib.parse import parse_qs
from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from rest_framework_simplejwt.tokens import AccessToken
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError

User = get_user_model()

@database_sync_to_async
def get_user_from_token(token_string: str):
    """
    Validates a SimpleJWT access token and loads the associated User instance.
    Returns AnonymousUser() if token is invalid or user not found.
    """
    try:
        access_token = AccessToken(token_string)
        user_id = access_token.get('user_id')
        if not user_id:
            return AnonymousUser()
        return User.objects.select_related('patient_profile', 'doctor_profile').get(id=user_id)
    except (InvalidToken, TokenError, User.DoesNotExist, Exception):
        return AnonymousUser()


class JWTAuthMiddleware:
    """
    Custom JWT Authentication Middleware for Django Channels WebSockets.
    Authenticates WebSocket connections using SimpleJWT Bearer tokens via:
    1. Query parameters: ?token=<access_token>
    2. HTTP Headers: Authorization: Bearer <access_token>
    3. Sec-WebSocket-Protocol: bearer_<access_token>
    """
    def __init__(self, inner):
        self.inner = inner

    async def __call__(self, scope, receive, send):
        token = None

        # 1. Check query parameters
        query_string = scope.get('query_string', b'').decode('utf-8')
        query_params = parse_qs(query_string)
        if 'token' in query_params and query_params['token']:
            token = query_params['token'][0]

        # 2. Check Authorization header
        if not token:
            headers = dict(scope.get('headers', []))
            auth_header = headers.get(b'authorization', b'').decode('utf-8')
            if auth_header.startswith('Bearer '):
                token = auth_header.split('Bearer ', 1)[1].strip()

        # 3. Check Subprotocol header
        if not token:
            subprotocols = scope.get('subprotocols', [])
            for proto in subprotocols:
                if proto.startswith('bearer_'):
                    token = proto.replace('bearer_', '')
                    break

        if token:
            scope['user'] = await get_user_from_token(token)
        else:
            scope['user'] = AnonymousUser()

        return await self.inner(scope, receive, send)


def JWTAuthMiddlewareStack(inner):
    """Convenience wrapper for JWT-authenticated WebSocket scopes."""
    return JWTAuthMiddleware(inner)

