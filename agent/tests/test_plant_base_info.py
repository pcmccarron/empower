"""Plant lookup failures should return tool results rather than abort a turn."""

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
async def test_lookup_failure_returns_an_error_result(flag, message):
    token = flag.set(True)
    try:
        result = await plant_base_info_tool.on_invoke_tool(
            None, '{"plant_names": ["rose"]}'
        )
    finally:
        flag.reset(token)

    assert result == f"Error getting plant advice: {message}"


@pytest.mark.asyncio
async def test_supported_plant_returns_care_advice():
    result = await plant_base_info_tool.on_invoke_tool(
        None, '{"plant_names": ["rose"]}'
    )

    assert "**Rose Basic Info**" in result
    assert "**Watering**: Water regularly" in result
    assert "**Light**: Full sun" in result


@pytest.mark.asyncio
async def test_empty_plant_list_requests_plant_names():
    result = await plant_base_info_tool.on_invoke_tool(None, '{"plant_names": []}')

    assert result == "Please provide plant names to get care advice."
