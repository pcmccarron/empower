import json
import logging

import pytest

from app.tools.plant_base_info import plant_base_info_tool
from app.utils import validate_plant_info


@pytest.mark.asyncio
@pytest.mark.parametrize("simulate_missing_info", [False, True])
async def test_basic_info_handles_missing_plants_without_errors(
    simulate_missing_info, caplog
):
    token = validate_plant_info.set(simulate_missing_info)
    try:
        with caplog.at_level(logging.ERROR):
            result = await plant_base_info_tool.on_invoke_tool(
                None,
                json.dumps({"plant_names": ["rose", "sunflower", "tulip", "unknown"]}),
            )
    finally:
        validate_plant_info.reset(token)

    for name in ["Rose", "Sunflower", "Tulip"]:
        if simulate_missing_info:
            assert f"🌸 **{name}**\n\nNo specific information available." in result
        else:
            assert f"🌸 **{name} Basic Info**" in result
    assert "🌸 **Unknown**\n\nNo specific information available." in result
    assert "Error getting plant advice" not in result
    assert not caplog.records


@pytest.mark.asyncio
async def test_basic_info_normalizes_plant_names():
    result = await plant_base_info_tool.on_invoke_tool(
        None, json.dumps({"plant_names": ["  ROSE  "]})
    )

    assert (
        "**Watering**: Water regularly, keep soil moist but not waterlogged" in result
    )
    assert "**Light**: Full sun (6+ hours daily)" in result


@pytest.mark.asyncio
@pytest.mark.parametrize("simulate_missing_info", [False, True])
async def test_basic_info_still_requests_empty_plant_names(simulate_missing_info):
    token = validate_plant_info.set(simulate_missing_info)
    try:
        result = await plant_base_info_tool.on_invoke_tool(
            None, json.dumps({"plant_names": []})
        )
    finally:
        validate_plant_info.reset(token)

    assert result == "Please provide plant names to get care advice."
