import secrets
import string
from typing import Any

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


class GenerationConfig(BaseModel):
    """Configuration for secret generation"""

    # Length configuration
    length: int = Field(
        default=32, ge=1, le=1024, description="Length of the generated secret"
    )

    # Character set options
    include_uppercase: bool = Field(
        default=True, description="Include uppercase letters (A-Z)"
    )
    include_lowercase: bool = Field(
        default=True, description="Include lowercase letters (a-z)"
    )
    include_numbers: bool = Field(default=True, description="Include numbers (0-9)")
    include_symbols: bool = Field(
        default=False, description="Include symbols (!@#$%^&*()_+-=[]{}|;:,.<>?)"
    )
    custom_charset: str | None = Field(
        default=None,
        description="Custom character set to use instead of predefined sets",
    )

    # Symbol configuration
    symbol_set: str = Field(
        default="!@#$%^&*()_+-=[]{}|;:,.<>?",
        description="Set of symbols to use when include_symbols is True",
    )

    # Memorable password options (when strategy="memorable")
    word_count: int = Field(
        default=4, ge=2, le=10, description="Number of words for memorable passwords"
    )
    word_separator: str = Field(
        default="-", description="Separator between words in memorable passwords"
    )
    capitalize_words: bool = Field(
        default=True,
        description="Capitalize first letter of each word in memorable passwords",
    )
    add_number_suffix: bool = Field(
        default=True, description="Add random number suffix to memorable passwords"
    )

    # Exclusions
    exclude_ambiguous: bool = Field(
        default=False, description="Exclude ambiguous characters (0, O, l, 1, I)"
    )
    exclude_similar: bool = Field(
        default=False, description="Exclude similar characters (il1L, o0O)"
    )
    exclude_chars: str = Field(
        default="", description="Specific characters to exclude from generation"
    )


class GeneratorConfig(BaseModel):
    """Configuration for Generator stage"""

    generation: GenerationConfig = Field(
        default_factory=GenerationConfig, description="Secret generation configuration"
    )
    overwrite_existing: bool = Field(
        default=False,
        description="Overwrite existing secrets with newly generated ones",
    )


class GeneratorGSecretExecutor(GSecretExecutor):
    """Generator executor that creates secrets if they don't exist"""

    def __init__(
        self,
        config: GeneratorConfig,
        chain: Chain[GSecretExecutor],
    ):
        self.config = config
        self.chain = chain

    def _generate_secret(self) -> str:
        """Generate a secret based on configuration"""
        gen_config = self.config.generation

        # Build character set
        if gen_config.custom_charset:
            charset = gen_config.custom_charset
        else:
            charset = ""
            if gen_config.include_uppercase:
                charset += string.ascii_uppercase
            if gen_config.include_lowercase:
                charset += string.ascii_lowercase
            if gen_config.include_numbers:
                charset += string.digits
            if gen_config.include_symbols:
                charset += gen_config.symbol_set

        if not charset:
            return ""

        # Apply exclusions
        if gen_config.exclude_ambiguous:
            charset = "".join(c for c in charset if c not in "0Ol1I")
        if gen_config.exclude_similar:
            charset = "".join(c for c in charset if c not in "il1Lo0O")
        if gen_config.exclude_chars:
            charset = "".join(c for c in charset if c not in gen_config.exclude_chars)

        # Fallback: force constraints
        return "".join(secrets.choice(charset) for _ in range(gen_config.length))

    def get_secret_id(
        self, key_id: str, token: Token, next: ForwardChainExecutor["GSecretExecutor"]
    ) -> Secret | GsecretFailure:
        """Retrieve a secret by its ID, pass through to next executor"""
        stage = next.next()
        if stage:
            return stage.get_secret_id(key_id, token, next)
        return GsecretFailure(reason="Secret not found", code=404)

    def get_secret_key(
        self, key: str, token: Token, next: ForwardChainExecutor["GSecretExecutor"]
    ) -> Secret | GsecretFailure:
        """
        Retrieve a secret by its key, generate if not found.
        """
        # Try to get from chain
        stage = next.next()
        if stage:
            if not self.config.overwrite_existing:
                result = stage.get_secret_key(key, token, next.copy())

                if not isinstance(result, GsecretFailure) or result.code != 404:
                    return result

            generated_value = self._generate_secret()
            write_secret = WriteSecret(key=key, secret=generated_value)

            # Try to write the generated secret
            write_result = stage.write_secret(write_secret, token, next.copy())

            return write_result

        # No executor in chain
        return GsecretFailure(
            reason="Cannot generate secret: no write stage in chain", code=501
        )

    def write_secret(
        self,
        secret: WriteSecret,
        token: Token,
        next: ForwardChainExecutor["GSecretExecutor"],
    ) -> Secret | GsecretFailure:
        """Pass through write operations to next executor"""
        stage = next.next()
        if stage:
            return stage.write_secret(secret, token, next)
        return GsecretFailure(reason="Write operations not supported", code=501)

    def secret_updated(
        self,
        secrets: list[UpdatedSecret],
        token_hash: TokenID,
        priority: int,
        next: ReverseChainExecutor["GSecretExecutor"],
    ):
        """Handle secret update notifications in reverse chain"""
        # Pass to next executor in reverse chain
        stage = next.next()
        if stage:
            return stage.secret_updated(secrets, token_hash, priority, next)


class GeneratorGSecretStageBuilder(ChainStageBuilder[GSecretExecutor]):
    """Builder for Generator stage"""

    def build(self, config: Any, chain: Chain[GSecretExecutor]) -> GSecretExecutor:
        if config is None:
            config = {}
        parsed_config = GeneratorConfig.model_validate(config)
        return GeneratorGSecretExecutor(parsed_config, chain)


# Register the stage builder with the gsecret interface
builder = GeneratorGSecretStageBuilder()
gsecret_interface.register_stage("generator", builder)
