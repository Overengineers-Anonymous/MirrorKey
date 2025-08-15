from re import S
import sys
from typing import Any, Protocol, Sequence, Type, TypedDict
from fastapi.background import P
from pydantic import BaseModel
import pytest
from pathlib import Path
from unittest.mock import call, patch, MagicMock
from shatter_api.core.config.config import ConfigParser
from shatter_api.core.config.structure import Config, ApiDescriptor
from shatter_api.tests import parametrise, Param


def test_load_config_file():
    # with patch.object(ConfigParser._validate_config) as mock:
    with patch("shatter_api.core.config.config.ConfigParser._validate_config") as mock:
        config = ConfigParser()
        config.load_config(Path(__file__).parent / "fixtures" / "test_config.yml")

        mock.assert_called_with({"test": "test"})


def test_validate_config():
    config = ConfigParser()
    config._validate_config({"api_descriptors": {"api_desr": None}})

    assert config.config is not None
    assert config.config.api_descriptors is not None
    assert config.config.api_descriptors["api_desr"] is None


def test_invalid_config():
    with patch("shatter_api.core.config.config.ConfigParser.parse_errors") as mock:
        config = ConfigParser()
        config._validate_config({"api_descriptors": {"api_desr": "invalid"}})
        mock.assert_called()


def test_api_descriptor_parser_required():
    config = ConfigParser()
    config.config = Config(api_descriptors={"bws_cache": ApiDescriptor(config={"org_id": "test"})})

    class TestParser(BaseModel):
        org_id: str

    config = config.api_descriptor("bws_cache", TestParser, True)
    assert config.org_id == "test"


test_data = [
    Param(
        [Config(api_descriptors={}), "API descriptor bws_cache not found in config file, please add it"], "required missing"
    ),
    Param(
        [Config(api_descriptors={"bws_cache": None}), "API descriptor bws_cache has no config section, please add it"],
        "required missing config section",
    ),
    Param(
        [
            Config(api_descriptors={"bws_cache": ApiDescriptor(config={})}),
            "API descriptor bws_cache config section is empty, please add it",
        ],
        "required missing config empty",
    ),
]


@parametrise(test_data)
def test_api_descriptor_parser_error(cfg_data: Config, expected: str):
    with patch("shatter_api.core.config.config.logger.error") as mock:
        config = ConfigParser()
        config.config = cfg_data

        class TestParser(BaseModel):
            org_id: str

        with pytest.raises(SystemExit):
            config = config.api_descriptor("bws_cache", TestParser, True)
        mock.assert_called_with(expected)


def mock_exit(*args, **kwargs):
    sys.exit(1)


test_missing_data = [
    Param([Config(api_descriptors=None)], "null_api_descriptors"),
    Param([Config(api_descriptors={})], "empty_api_descriptors"),
    Param([Config(api_descriptors={"bws_cache": None})], "null_bws_cache"),
    Param([Config(api_descriptors={"bws_cache": ApiDescriptor(config=None)})], "empty_bws_cache_config"),
]


@parametrise(test_missing_data)
def test_api_descriptor_parser_missing(cfg_value: Config):
    config = ConfigParser()
    config.config = cfg_value

    class TestParser(BaseModel):
        org_id: str

    assert config.api_descriptor("bws_cache", TestParser, False) is None


invalid_data = [
    Param([True], "invalid_data_required"),
    Param([False], "invalid_data_not_required"),
]


@parametrise(invalid_data)
def test_api_descriptor_parser_required_missing_config_invalid(required: bool):
    with patch("shatter_api.core.config.config.ConfigParser.parse_errors", wraps=mock_exit) as mock:
        config = ConfigParser()
        config.config = Config(api_descriptors={"bws_cache": ApiDescriptor(config={"org_id": 0})})

        class TestParser(BaseModel):
            org_id: str

        with pytest.raises(SystemExit):
            config = config.api_descriptor("bws_cache", TestParser, required)
        mock.assert_called()


class ValidationErrorValue(TypedDict):
    loc: Sequence[str | int | Any]
    msg: str


class TestValidationError:
    def __init__(self, errors: list[ValidationErrorValue]):
        self._errors = errors

    def errors(self) -> Sequence[ValidationErrorValue]:
        return self._errors


test_parse_errors_data = [
    Param(
        [
            TestValidationError([ValidationErrorValue(loc=["field"], msg="test_err_msg")]),
            [call("error name: test_err_msg: field at .base_path")],
        ],
        "error",
    ),
    Param(
        [
            TestValidationError(
                [
                    ValidationErrorValue(loc=["field"], msg="test_err_msg"),
                    ValidationErrorValue(loc=["field2"], msg="test_err_msg2"),
                ]
            ),
            [
                call("error name: test_err_msg: field at .base_path"),
                call("error name: test_err_msg2: field2 at .base_path"),
            ],
        ],
        "multiple_errors",
    ),
    Param(
        [
            TestValidationError([ValidationErrorValue(loc=["field", 0], msg="test_err_msg")]),
            [call("error name: test_err_msg: index 0 at .base_path.field")],
        ],
        "error_with_index_last",
    ),
    Param(
        [
            TestValidationError([ValidationErrorValue(loc=[0, "field"], msg="test_err_msg")]),
            [call("error name: test_err_msg: field at .base_path[0]")],
        ],
        "error_with_index_first",
    ),
    Param(
        [
            TestValidationError([ValidationErrorValue(loc=[], msg="test_err_msg")]),
            [call("error name: test_err_msg at {unknown location}")],
        ],
        "error_with_empty_location",
    ),
]


@parametrise(test_parse_errors_data)
def test_parse_errors(tve, result):
    with patch("shatter_api.core.config.config.logger.error") as mock:
        config = ConfigParser()

        with pytest.raises(SystemExit):
            config.parse_errors(tve, "base_path", "error name")

        mock.assert_has_calls(result)


test_invalid_type = [
    Param([TestValidationError([ValidationErrorValue(loc=["field", 0.0], msg="test_err_msg")])], "float_first"),
    Param([TestValidationError([ValidationErrorValue(loc=[0.0, "field"], msg="test_err_msg")])], "float_last"),
]


@parametrise(test_invalid_type)
def test_parse_errors_with_invalid_type(tve):
    config = ConfigParser()
    with pytest.raises(TypeError):
        config.parse_errors(tve, "base_path", "error name")
