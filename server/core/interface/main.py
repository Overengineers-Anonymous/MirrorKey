from core.chain.chain import ChainStage, ChainStageBuilder


class Interface[T: ChainStage]:
    def __init__(self, name: str, stage_class: type[T]):
        self.name = name
        self.stage_class = stage_class
        self.stages: dict[str, ChainStageBuilder[T]] = {}

    def register_stage(self, name: str, stage: ChainStageBuilder[T]) -> None:
        if name in self.stages:
            raise ValueError(f"Stage '{name}' is already registered.")
        if not isinstance(stage, ChainStageBuilder):
            raise TypeError(
                "Stage must be an instance of the specified ChainStage protocol."
            )
        self.stages[name] = stage
