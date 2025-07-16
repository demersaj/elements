from uuid import UUID
from typing import AsyncIterator, Set
import time
import requests

from webai_element_sdk.comms.messages import Frame
from webai_element_sdk import Context, Element
from webai_element_sdk.element.settings import (
    ElementSettings,
    NumberSetting,
    TextSetting,
)
from webai_element_sdk.element.variables import ElementInputs, Input


class Inputs(ElementInputs):
    input_1 = Input[AsyncIterator[Frame]]()

class Settings(ElementSettings):
    api_token = TextSetting(
        name="api_token",
        display_name="API Token",
        description="",
        default="",
    )
    device_id = TextSetting(
        name="device_id",
        display_name="Device ID",
        description="ID of the device you want to control",
        default="",
    )

element = Element(
    id=UUID("d30339fa-ab45-432b-b9aa-a6f431728148"),
    name="garage_opener",
    display_name="Garage Opener",
    version="0.1.4",
    description="Open garage door based on frame input.",
    framework_version="0.9",
    inputs=Inputs(),
    outputs=None,
    settings=Settings(),
    is_inference=True,
)


@element.executor
async def main(ctx: Context[Inputs, None, Settings]) -> None:
    input_frame = ctx.inputs.input_1.value
    api_token: str = ctx.settings.api_token.value
    device_id : str = ctx.settings.device_id.value

    if input_frame is None:
        raise Exception("No input frame provided")
    
    payload = {
    "commands": 
    [

        {
            "component": "main",
            "capability": "doorControl",
            "command": "open"
        }
    ]
    }

    headers: dict[str, str] = {
        "Content-Type": "application/json",
        "Authorization": "Bearer " + api_token,
    }

    response = requests.post(
        "https://api.smartthings.com/v1/devices/" + device_id + "/commands",
        json=payload,
        headers=headers,
    )

    response.raise_for_status()
    last_send = time.time()
