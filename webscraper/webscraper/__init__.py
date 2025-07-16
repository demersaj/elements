from typing import AsyncIterator
from uuid import UUID

from webai_element_sdk.comms.messages import TextFrame
from webai_element_sdk.element import Context, Element
from webai_element_sdk.element.variables import ElementOutputs, Output, Input, ElementInputs
from webai_element_sdk.element.settings import (
    ElementSettings,
    BoolSetting,
    NumberSetting,
    TextSetting,
)


class Inputs(ElementInputs):
    default_in1 = Input[TextFrame]()
    default_in2 = Input[AsyncIterator[TextFrame]]()


class Outputs(ElementOutputs):
    default_out = Output[TextFrame]()


class Settings(ElementSettings):  # More information on settings: https://github.com/thewebAI/webai-cli?tab=readme-ov-file#element-settings
    setting1 = TextSetting(
        name="setting1",
        display_name="Setting 1",
        valid_values=["a", "b", "c"],  # Providing valid values is optional
        default="b",
    )
    setting2 = NumberSetting[float](  # You can also use '[int]'
        name="setting2",
        display_name="Setting 2",
        default=0.4,
        min_value=0,
        max_value=1,
        step=0.01
    )
    setting3 = BoolSetting(
        name="setting3",
        display_name="Setting 3",
        default=True
    )


element = Element(
    id=UUID("f3183797-8904-480a-a075-ec938f6d5ed5"),
    name="webscraper",
    display_name="web-scraper",
    description="",
    version="0.1.0",
    settings=Settings(),
    inputs=Inputs(),
    outputs=Outputs(),
)


@element.startup
async def startup(ctx: Context[Inputs, Outputs, Settings]):
    print("Starting...")


@element.shutdown
async def shutdown(ctx: Context[Inputs, Outputs, Settings]):
    print("Shutting Down...")


@element.executor
async def run(
    ctx: Context[Inputs, Outputs, Settings]
) -> AsyncIterator[Output[TextFrame]]:

    print("Running...")

    setting1: str = ctx.settings.setting1.value
    setting2: float = ctx.settings.setting2.value
    setting3: bool = ctx.settings.setting3.value

    # Example of retrieving a single Frame per execution
    input_frame: TextFrame = ctx.inputs.default_in1.value

    # Setting Example 1: Modify text based on setting1
    prefix_map: dict[str, str] = {
        "a": "Option A: ",
        "b": "Option B: ",
        "c": "Option C: "
    }
    modified_text: str = f"{prefix_map[setting1]}{input_frame.text}"

    # Setting Example 2: Use setting2 to control text transformation
    # If setting2 is > 0.5, convert to uppercase, otherwise lowercase
    if setting2 > 0.5:
        modified_text = modified_text.upper()
    else:
        modified_text = modified_text.lower()

    # ... do some work
    output_value: TextFrame = TextFrame(text=modified_text)
    # Setting Example 3: Use setting3 to control output frame
    # If setting3 is True, use the input frame as the output frame
    if setting3:
        output_value = input_frame

    # Example of retrieving a generator to loop over
    input_generator: AsyncIterator[TextFrame] = ctx.inputs.default_in2.value

    for frame in input_generator:
        print(frame)
        # ... do some work

    # yield the output frame
    yield ctx.outputs.default_out(output_value)
