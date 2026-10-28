import json
import logging

import pytest

from app.tools.plant_base_info import get_plant_basic_info, plant_base_info_tool
from app.utils import validate_plant_advice, validate_plant_info


@pytest.mark.parametrize("validation_enabled", [False, True])
@pytest.mark.parametrize(
    "plant_names",
    [
        ["rose", "sunflower", "tulip"],
        ["lowlight plants"],
        [" ROSE ", "unknown"],
        [],
    ],
)
def test_basic_info_is_not_blocked_by_validation_flag(validation_enabled, plant_names):
    expected = get_plant_basic_info(plant_names)
    token = validate_plant_info.set(validation_enabled)
    try:
        assert get_plant_basic_info(plant_names) == expected
    finally:
        validate_plant_info.reset(token)


@pytest.mark.asyncio
@pytest.mark.parametrize("validation_enabled", [False, True])
async def test_tool_returns_info_and_unknown_fallback(validation_enabled, caplog):
    token = validate_plant_info.set(validation_enabled)
    try:
        with caplog.at_level(logging.ERROR):
            result = await plant_base_info_tool.on_invoke_tool(
                None, json.dumps({"plant_names": ["rose", "lowlight plants"]})
            )
        assert "**Rose Basic Info**" in result
        assert "**Watering**: Water regularly" in result
        assert "**Lowlight Plants**\n\nNo specific information available." in result
        assert not caplog.records
    finally:
        validate_plant_info.reset(token)


@pytest.mark.asyncio
async def test_advice_failure_trigger_is_preserved():
    token = validate_plant_advice.set(True)
    try:
        with pytest.raises(
            Exception, match="Could not get plant advice: File not found"
        ):
            await plant_base_info_tool.on_invoke_tool(
                None, json.dumps({"plant_names": ["rose"]})
            )
    finally:
        validate_plant_advice.reset(token)
