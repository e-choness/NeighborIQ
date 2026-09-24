"""
RS256 signing keys.

Production: set JWT_PRIVATE_KEY and JWT_PUBLIC_KEY (PEM) from your secret store;
nothing is written to the database.
Development: when they are absent, a key pair is generated once and kept in
auth_jwt_keys so tokens survive restarts. Storing a private key in the
application database is a dev convenience only.
"""

import logging
import os

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shared import JWTKeyPair, generate_rsa_keypair, get_key_id

logger = logging.getLogger(__name__)


class SigningKeys:
    private_pem: str = ""
    public_pem: str = ""
    key_id: str = ""


keys = SigningKeys()


async def load_signing_keys(db: AsyncSession) -> None:
    # PEMs in a one-line .env value carry literal "\n" sequences
    private_pem = os.getenv("JWT_PRIVATE_KEY", "").replace("\\n", "\n")
    public_pem = os.getenv("JWT_PUBLIC_KEY", "").replace("\\n", "\n")
    if private_pem and public_pem:
        logger.info("Using JWT keys from the environment")
    else:
        existing = (
            await db.execute(select(JWTKeyPair).where(JWTKeyPair.is_active == 1))
        ).scalar_one_or_none()
        if existing:
            private_pem, public_pem = existing.private_key_pem, existing.public_key_pem
        else:
            logger.warning("No JWT keys configured — generating a development key pair")
            private_pem, public_pem = generate_rsa_keypair()
            db.add(
                JWTKeyPair(
                    private_key_pem=private_pem,
                    public_key_pem=public_pem,
                    algorithm="RS256",
                    key_id=get_key_id(public_pem),
                    is_active=1,
                )
            )
            await db.commit()

    keys.private_pem, keys.public_pem = private_pem, public_pem
    keys.key_id = get_key_id(public_pem)
    # jwt_utils reads these when no key is passed explicitly
    os.environ["JWT_PRIVATE_KEY"], os.environ["JWT_PUBLIC_KEY"] = private_pem, public_pem
