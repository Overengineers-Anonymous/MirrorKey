
from core.interface.main import Interface

from .chain import Chain, ChainStage


class ChainExecutor[T: ChainStage]:
    def __init__(self, chain: Chain[T], current_index=0, reverse=False) -> None:
        self.chain = chain
        self.next_index = 1 if not reverse else -1
        self.current_index = current_index

    def next(self) -> T | None:
        if 0 <= self.current_index < len(self.chain):
            stage = self.chain.get_stages(self.current_index)
            self.current_index += self.next_index
            return stage
        return None


class ForwardChainExecutor[T: ChainStage](ChainExecutor[T]):
    def __init__(self, chain: Chain[T], current_index=0) -> None:
        super().__init__(chain, current_index, reverse=False)


class ReverseChainExecutor[T: ChainStage](ChainExecutor[T]):
    def __init__(self, chain: Chain[T], current_index=-1) -> None:
        if current_index == -1:
            current_index = len(chain) - 1
        super().__init__(chain, current_index, reverse=True)


class ChainController[T: ChainStage]:
    def __init__(self, interface: Interface[T]) -> None:
        self.stage_class = interface.stage_class
        self.chains: dict[str, Chain[T]] = {}

    def add_chain(self, chain: Chain[T]) -> None:
        if not isinstance(chain, Chain):
            raise TypeError("chain must be an instance of Chain.")
        if not issubclass(chain.stage_class, self.stage_class):
            raise TypeError(
                "Chain's state_class must be a subclass of the executor_class."
            )
        self.chains[chain.name] = chain

    def get_executor(self, chain: str) -> ForwardChainExecutor[T] | None:
        chain_instance = self.chains.get(chain)
        if chain_instance is not None:
            return ForwardChainExecutor(chain_instance)
        return None


