from channels.db import database_sync_to_async
from django.contrib.auth.models import AnonymousUser
from django.db import close_old_connections
from rest_framework.authtoken.models import Token


@database_sync_to_async
def get_user(token_key):
    try:
        token = Token.objects.get(key=token_key)
        user = token.user
    except Token.DoesNotExist:
        user = AnonymousUser()
    return user


class TokenAuthMiddleware:
    def __init__(self, inner):
        self.inner = inner

    async def __call__(self, scope, receive, send):
        close_old_connections()
        headers = dict(scope['headers'])
        if b'authorization' in headers:
            try:
                token_key = headers[b'authorization'].decode().split()[1]
                user = await get_user(token_key)
                if user.is_authenticated:
                    scope['user'] = user

            except Exception:
                pass

        return await self.inner(scope, receive, send)
