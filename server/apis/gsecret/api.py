from typing import Annotated

from core import ChainController
from core.api.manager import APIPlugin, plugin_manager
from core.chain.controller import ForwardChainExecutor
from fastapi import APIRouter, Depends, Header, HTTPException, Path
from interfaces.gsecret import GSecretExecutor, Token, WriteSecret, gsecret_interface

router = APIRouter()


chain_controller = ChainController(gsecret_interface)


def get_chain_executor(
    chain: Annotated[str, Path(description="Chain name")],
) -> ForwardChainExecutor[GSecretExecutor]:
    """Dependency to get and validate chain executor."""
    chain_executor = chain_controller.get_executor(chain)
    if not chain_executor:
        raise HTTPException(status_code=404, detail="Chain not found")
    return chain_executor


def get_first_executor(
    chain_executor: Annotated[
        ForwardChainExecutor[GSecretExecutor], Depends(get_chain_executor)
    ],
) -> GSecretExecutor:
    """Dependency to get the first executor from the chain."""
    executor = chain_executor.next()
    if not executor:
        raise HTTPException(status_code=404, detail="Chain has no stages")
    return executor


def get_token(
    authorization: Annotated[str | None, Header()] = None,
) -> Token:
    """Dependency to extract and validate token from Authorization header."""
    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization header required")

    # Support "Bearer <token>" format
    if authorization.startswith("Bearer "):
        token_value = authorization[7:]
    else:
        token_value = authorization

    return Token(token=token_value)


@router.get("/{chain}/key/{key}")
async def get_secret(
    key: str,
    chain_executor: Annotated[
        ForwardChainExecutor[GSecretExecutor], Depends(get_chain_executor)
    ],
    executor: Annotated[GSecretExecutor, Depends(get_first_executor)],
    token: Annotated[Token, Depends(get_token)],
):
    secret = executor.get_secret_key(key, token, chain_executor)
    if not secret:
        raise HTTPException(status_code=404, detail="Secret not found")
    return secret


@router.get("/{chain}/id/{key_id}")
async def get_secret_by_id(
    key_id: str,
    chain_executor: Annotated[
        ForwardChainExecutor[GSecretExecutor], Depends(get_chain_executor)
    ],
    executor: Annotated[GSecretExecutor, Depends(get_first_executor)],
    token: Annotated[Token, Depends(get_token)],
):
    secret = executor.get_secret_id(key_id, token, chain_executor)
    if not secret:
        raise HTTPException(status_code=404, detail="Secret not found")
    return secret


@router.post("/{chain}/write")
async def write_secret(
    secret: WriteSecret,
    chain_executor: Annotated[
        ForwardChainExecutor[GSecretExecutor], Depends(get_chain_executor)
    ],
    executor: Annotated[GSecretExecutor, Depends(get_first_executor)],
    token: Annotated[Token, Depends(get_token)],
):
    return executor.write_secret(secret, token, chain_executor)


gsecret_plugin = plugin_manager.register_plugin(
    APIPlugin(
        name="gsecret",
        chain_controller=chain_controller,
        interface=gsecret_interface,
        router=router,
    )
)
