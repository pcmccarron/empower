"""Plant lookup failures should return tool feedback, not abort the chat turn."""

import json

import pytest

from app.tools.plant_base_info import plant_base_info_tool
from app.utils import validate_plant_advice, validate_plant_info


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "flag, message",
    [
        (validate_plant_advice, "Could not get plant advice: File not found"),
        (validate_plant_info, "Could not get plant basic info: Unknown plant"),
    ],
)
async def test_lookup_failure_returns_tool_feedback(flag, message, caplog):
    token = flag.set(True)
    try:
        result = await plant_base_info_tool.on_invoke_tool(
            None, json.dumps({"plant_names": ["rose"]})
        )
    finally:
        flag.reset(token)

    assert result == f"Error getting plant advice: {message}"
    assert message in caplog.text


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "plant_names, expected",
    [
        ([" ROSE "], "**Watering**: Water regularly"),
        (["sunflower", "tulip"], "**Tulip Basic Info**"),
        (["unknown"], "No specific information available."),
        ([], "Please provide plant names to get care advice."),
    ],
)
async def test_plant_advice_without_failure_flags(plant_names, expected):
    result = await plant_base_info_tool.on_invoke_tool(
        None, json.dumps({"plant_names": plant_names})
    )

    assert expected in result
