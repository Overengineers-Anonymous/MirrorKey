from core.chain.controller import ChainController, ChainStage
from core.interface.main import ChainStageBuilder, Interface
from fastapi import APIRouter


class APIPlugin[T: ChainStage]:
    def __init__(
        self,
        name: str,
        chain_controller: ChainController[T],
        interface: Interface[T],
        router: APIRouter,
    ) -> None:
        self.name = name
        self.chain_controller = chain_controller
        self.interface = interface
        self.router = router

    @property
    def stage_class(self) -> type[ChainStage]:
        return self.chain_controller.stage_class

    @property
    def chain_stages(self) -> dict[str, ChainStageBuilder[T]]:
        return self.interface.stages
