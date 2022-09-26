import base64
import logging
from typing import TYPE_CHECKING, Union

from passlib.context import CryptContext
from starlite import NotAuthorizedException
from starlite_jwt import OAuth2PasswordBearerAuth

from app import db, services
from app.config import paths, settings
from app.utils.asyncer import run_async

if TYPE_CHECKING:
    from pydantic import SecretBytes, SecretStr

    from app.db.models import User

logger = logging.getLogger()


async def current_user_from_token(sub: str) -> "User":
    user = await services.user.get_by_email(db.db_session(), sub)
    if user and user.is_active:
        return user
    raise NotAuthorizedException("Invalid account name")


auth = OAuth2PasswordBearerAuth(  # nosec
    retrieve_user_handler=current_user_from_token,
    token_secret=settings.app.SECRET_KEY.get_secret_value().decode(),
    token_url=paths.urls.ACCESS_TOKEN,
    exclude=[
        paths.urls.OPENAPI_SCHEMA,
        paths.urls.HEALTH,
        paths.urls.ACCESS_TOKEN,
        paths.urls.SIGNUP,
        paths.urls.STATIC,
        paths.urls.INDEX,
    ],
)

password_crypt_context = CryptContext(schemes=["argon2"], deprecated="auto")


def get_encryption_key(secret: str) -> bytes:
    padded_secret = f"{secret:<32}"[0:32]
    return base64.urlsafe_b64encode(padded_secret.encode())


async def get_password_hash(password: Union["SecretBytes", "SecretStr"]) -> str:
    """Get password hash
    Args:
        password: Plain password
    Returns:
        Hashed password
    """
    pw_hash = await run_async(password_crypt_context.hash)(password.get_secret_value())
    return pw_hash


async def verify_password(plain_password: Union["SecretBytes", "SecretStr"], hashed_password: str) -> bool:
    """Verify password
    Args:
        plain_password: Plain password
        hashed_password: Hashed password
    Returns:
        True if password is correct
    """
    valid, _ = await run_async(password_crypt_context.verify_and_update)(
        plain_password.get_secret_value(),
        hashed_password,
    )
    return bool(valid)