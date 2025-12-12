import json
from typing import Any, Literal

import yaml
from core.chain.chain import ChainStageBuilder
from core.chain.controller import Chain, ForwardChainExecutor, ReverseChainExecutor
from interfaces.gsecret import (
    GSecretExecutor,
    GsecretFailure,
    Secret,
    Token,
    TokenID,
    UpdatedSecret,
    WriteSecret,
    gsecret_interface,
)
from pydantic import BaseModel, Field


class ParseSecretConfig(BaseModel):
    """Configuration for ParseSecret stage"""

    encode_on_write: Literal["none", "json", "yaml"] = Field(
        default="yaml", description="Encode secrets when writing (object -> string)"
    )
    parse_on_read: Literal["none", "json", "yaml", "auto"] = Field(
        default="auto", description="Parse secrets when reading (string -> object)"
    )
    parse_errors_as_string: bool = Field(
        default=True,
        description="Return unparseable secrets as strings instead of failing",
    )
    pretty_print: bool = Field(
        default=False, description="Pretty-print JSON/YAML output when encoding"
    )
    yaml_safe_load: bool = Field(
        default=True,
        description="Use safe_load for YAML parsing (recommended for security)",
    )


class ParseSecretGSecretExecutor(GSecretExecutor):
    """Executor that parses and encodes secrets as JSON/YAML"""

    def __init__(
        self,
        config: ParseSecretConfig,
        chain: Chain[GSecretExecutor],
    ):
        self.config = config
        self.chain = chain

    def _parse_secret_value(self, value: str | Any) -> Any:
        """Parse a secret value from string to object"""
        if self.config.parse_on_read == "none" or not isinstance(value, str):
            return value

        if self.config.parse_on_read == "auto":
            # Try JSON first, then YAML
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                try:
                    if self.config.yaml_safe_load:
                        return yaml.safe_load(value)
                    else:
                        return yaml.load(value, Loader=yaml.FullLoader)
                except yaml.YAMLError:
                    if self.config.parse_errors_as_string:
                        return value
                    raise ValueError("Failed to parse secret as JSON or YAML")
        else:
            try:
                if self.config.parse_on_read == "json":
                    return json.loads(value)
                elif self.config.parse_on_read == "yaml":
                    if self.config.yaml_safe_load:
                        return yaml.safe_load(value)
                    else:
                        return yaml.load(value, Loader=yaml.FullLoader)
            except (json.JSONDecodeError, yaml.YAMLError) as e:
                if self.config.parse_errors_as_string:
                    return value
                raise ValueError(
                    f"Failed to parse secret as {self.config.parse_on_read}: {e}"
                )

        return value

    def _encode_secret_value(self, value: Any) -> str | Any:
        """Encode a secret value from object to string"""
        if self.config.encode_on_write == "none":
            return str(value) if not isinstance(value, str) else value

        if isinstance(value, str):
            return value

        try:
            if self.config.encode_on_write == "json":
                if self.config.pretty_print:
                    return json.dumps(value, indent=2, ensure_ascii=False)
                else:
                    return json.dumps(value, ensure_ascii=False)
            elif self.config.encode_on_write == "yaml":
                return yaml.dump(
                    value,
                    default_flow_style=not self.config.pretty_print,
                    allow_unicode=True,
                )
        except (TypeError, ValueError):
            pass

        return value

    def get_secret_id(
        self, key_id: str, token: Token, next: ForwardChainExecutor["GSecretExecutor"]
    ) -> Secret | GsecretFailure:
        """Retrieve a secret by its ID and parse it"""
        executor = next.next()
        if executor:
            result = executor.get_secret_id(key_id, token, next)

            # Parse the secret value if successful
            if isinstance(result, Secret):
                try:
                    parsed_value = self._parse_secret_value(result.secret)
                    return Secret(
                        key_id=result.key_id,
                        key=result.key,
                        secret=parsed_value,
                        rate_limit=result.rate_limit,
                    )
                except ValueError as e:
                    return GsecretFailure(reason=str(e), code=500)

            return result

        return GsecretFailure(reason="Secret not found", code=404)

    def get_secret_key(
        self, key: str, token: Token, next: ForwardChainExecutor["GSecretExecutor"]
    ) -> Secret | GsecretFailure:
        """Retrieve a secret by its key and parse it"""
        executor = next.next()
        if executor:
            result = executor.get_secret_key(key, token, next)

            # Parse the secret value if successful
            if isinstance(result, Secret):
                try:
                    parsed_value = self._parse_secret_value(result.secret)
                    return Secret(
                        key_id=result.key_id,
                        key=result.key,
                        secret=parsed_value,
                        rate_limit=result.rate_limit,
                    )
                except ValueError as e:
                    return GsecretFailure(reason=str(e), code=500)

            return result

        return GsecretFailure(reason="Secret not found", code=404)

    def write_secret(
        self,
        secret: WriteSecret,
        token: Token,
        next: ForwardChainExecutor["GSecretExecutor"],
    ) -> Secret | GsecretFailure:
        """Encode secret value and write to next executor"""
        executor = next.next()
        if executor:
            # Encode the secret value before writing
            encoded_value = self._encode_secret_value(secret.secret)
            encoded_secret = WriteSecret(key=secret.key, secret=encoded_value)

            result = executor.write_secret(encoded_secret, token, next)

            # Parse the returned secret value
            if isinstance(result, Secret):
                try:
                    parsed_value = self._parse_secret_value(result.secret)
                    return Secret(
                        key_id=result.key_id,
                        key=result.key,
                        secret=parsed_value,
                        rate_limit=result.rate_limit,
                    )
                except ValueError as e:
                    return GsecretFailure(reason=str(e), code=500)

            return result

        return GsecretFailure(reason="Write operations not supported", code=501)

    def secret_updated(
        self,
        secrets: list[UpdatedSecret],
        token_hash: TokenID,
        priority: int,
        next: ReverseChainExecutor["GSecretExecutor"],
    ):
        """Handle secret update notifications and parse secret values"""
        # Parse secret values in the update
        parsed_secrets = []
        for secret in secrets:
            try:
                parsed_value = self._parse_secret_value(secret.secret)
                parsed_secrets.append(
                    UpdatedSecret(
                        key_id=secret.key_id,
                        key=secret.key,
                        secret=parsed_value,
                        rate_limit=secret.rate_limit,
                        api_id_relation=secret.api_id_relation,
                        api_key_relation=secret.api_key_relation,
                    )
                )
            except ValueError:
                # skip unparseable secrets
                pass

        # Pass to next executor in reverse chain
        executor = next.next()
        if executor:
            return executor.secret_updated(parsed_secrets, token_hash, priority, next)


class ParseSecretGSecretStageBuilder(ChainStageBuilder[GSecretExecutor]):
    """Builder for ParseSecret stage"""

    def build(self, config: Any, chain: Chain[GSecretExecutor]) -> GSecretExecutor:
        if config is None:
            config = {}
        parsed_config = ParseSecretConfig.model_validate(config)
        return ParseSecretGSecretExecutor(parsed_config, chain)


# Register the stage builder with the gsecret interface
builder = ParseSecretGSecretStageBuilder()
gsecret_interface.register_stage("parse_secret", builder)
