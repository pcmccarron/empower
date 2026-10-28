"""Plant advice failures should return tool results rather than abort chat."""

import json

import pytest
from agents import RunContextWrapper

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
async def test_lookup_failure_returns_a_tool_result(flag, message, caplog):
    context = RunContextWrapper(None)
    arguments = json.dumps({"plant_names": ["rose"]})
    token = flag.set(True)
    try:
        result = await plant_base_info_tool.on_invoke_tool(context, arguments)
    finally:
        flag.reset(token)

    assert result == f"Error getting plant advice: {message}"
    assert message in caplog.text

    result = await plant_base_info_tool.on_invoke_tool(context, arguments)
    assert "**Rose Basic Info**" in result
    assert "**Watering**: Water regularly" in result


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "arguments, expected",
    [
        ('{"plant_names": ["rose"]}', "**Rose Basic Info**"),
        ('{"plant_names": ["fern"]}', "No specific information available."),
        ('{"plant_names": []}', "Please provide plant names to get care advice."),
        ("invalid json", "Error getting plant advice:"),
    ],
)
async def test_plant_advice_existing_results(arguments, expected):
    result = await plant_base_info_tool.on_invoke_tool(
        RunContextWrapper(None), arguments
    )

    assert expected in result
