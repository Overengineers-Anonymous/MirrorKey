import sys
from typing import Any, Literal, Sequence, TextIO, overload
from pydantic import BaseModel, ValidationError
from .structure import Config
import yaml
import logging
import pathlib
from pathlib import Path
from typing import Protocol, TypedDict

logger = logging.getLogger(__name__)


class ConfigParser:
    def __init__(self):
        self.config: Config | None = None

    def parse_errors(self, e: ValidationError, base_path: str = "", error_name: str = "Schema errors") -> None:
        schema_errors = []
        for error in e.errors():
            # no location information
            if not error["loc"]:
                schema_errors.append(f"{error['msg'].lower()} at {{unknown location}}")
                continue

            # prepend base path in loc
            loc = (base_path, *error["loc"]) if base_path else error["loc"]

            # extract the last location as the field
            *loc_path, field,  = loc
            if isinstance(field, str):
                path =f"{field}"
            elif isinstance(field, int):
                path = f"index {field}"
            else:
                raise TypeError("Unexpected type")

            if loc_path:
                path += " at "

            # build the path
            for _, pos in enumerate(loc_path):
                if isinstance(pos, str):
                    path += f".{pos}"
                elif isinstance(pos, int):
                    path += f"[{pos}]"
                else:
                    raise TypeError("Unexpected type")

            schema_errors.append(f"{error['msg'].lower()}: {path}")
        for error in schema_errors:
            logger.error(f"{error_name}: {error}")
        sys.exit(1)

    def load_config(self, config_file: str | Path) -> None:
        with open(config_file, "r") as f:
            data = yaml.load(f, Loader=yaml.FullLoader)
        self._validate_config(data)

    def _validate_config(self, data: Any):
            try:
                self.config = Config.model_validate(data)
            except ValidationError as e:
                self.parse_errors(e, "", "Config file Error")

    @overload
    def api_descriptor[T: BaseModel](self, name: str, loader: type[T], required: Literal[False]) -> T | None: ...

    @overload
    def api_descriptor[T: BaseModel](self, name: str, loader: type[T], required: Literal[True]) -> T: ...

    def api_descriptor[T: BaseModel](self, name: str, loader: type[T], required: bool = False) -> T | None:
        if self.config and self.config.api_descriptors and name in self.config.api_descriptors:
            api_descriptor_conf = self.config.api_descriptors[name]
            if required:
                if not api_descriptor_conf:
                    logger.error(f"API descriptor {name} has no config section, please add it")
                    sys.exit(1)
                if not api_descriptor_conf.config:
                    logger.error(f"API descriptor {name} config section is empty, please add it")
                    sys.exit(1)
            if api_descriptor_conf and api_descriptor_conf.config:
                try:
                    return loader.model_validate(api_descriptor_conf.config)
                except ValidationError as e:
                    self.parse_errors(e, f"api_descriptors.{name}", f"API descriptor '{name}' Config Error")
            return None
        if required:
            logger.error(f"API descriptor {name} not found in config file, please add it")
            sys.exit(1)
        return None

config = ConfigParser()

