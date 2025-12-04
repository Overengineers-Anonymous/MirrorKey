from core.interface.main import Interface

from .chain import Chain, ChainStage


class ForwardChainExecutor[T: ChainStage]:
    def __init__(self, chain: Chain[T], current_index=0) -> None:
        self.chain = chain
        self.current_index = current_index

    def copy(self) -> "ForwardChainExecutor[T]":
        return ForwardChainExecutor(self.chain, self.current_index)

    def next(self) -> "T | None":
        if 0 <= self.current_index < len(self.chain):
            stage = self.chain.get_stages(self.current_index)
            self.current_index += 1
            return stage
        return None


class ReverseChainExecutor[T: ChainStage]:
    def __init__(self, chain: Chain[T], current_index=-1) -> None:
        self.chain = chain
        self.current_index = len(chain) - 1 if current_index == -1 else current_index

    def copy(self) -> "ReverseChainExecutor[T]":
        return ReverseChainExecutor(self.chain, self.current_index)

    def next(self) -> "T | None":
        if 0 <= self.current_index < len(self.chain):
            stage = self.chain.get_stages(self.current_index)
            self.current_index -= 1
            return stage
        return None


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
