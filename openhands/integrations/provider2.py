from enum import Enum

from pydantic import BaseModel, SecretStr



class ProviderType(Enum):
    GITHUB = 'github'
    GITLAB = 'gitlab'


class ProviderToken(BaseModel):
    token: SecretStr | None
    user_id: str | None


PROVIDER_TOKEN_TYPE = dict[ProviderType, ProviderToken]
CUSTOM_SECRETS_TYPE = dict[str, SecretStr]

