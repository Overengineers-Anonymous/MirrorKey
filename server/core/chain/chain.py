from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class ChainStage(Protocol): ...


class Chain[T: ChainStage]:
    def __init__(self, name: str, stage_class: type[T]) -> None:
        self.name = name
        self.stage_class = stage_class
        self.stages: list[T] = []

    def add_stage(self, stage: T) -> None:
        if not isinstance(stage, self.stage_class):
            raise TypeError(
                "Stage must be an instance of the specified ChainStage protocol."
            )
        self.stages.append(stage)

    def get_stages(self, index: int) -> T:
        return self.stages[index]

    def get_stage_index(self, stage: T) -> int:
        for idx, s in enumerate(self.stages):
            if s is stage:
                return idx
        raise ValueError("Stage not found in chain.")

    def __len__(self) -> int:
        return len(self.stages)


@runtime_checkable
class ChainStageBuilder[T: ChainStage](Protocol):
    def build(self, config: Any, chain: Chain[T]) -> T: ...
