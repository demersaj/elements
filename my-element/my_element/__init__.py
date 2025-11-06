from uuid import UUID

from webai_element_sdk.comms.messages import Frame
from webai_element_sdk.element import Context, Element
from webai_element_sdk.element.variables import ElementOutputs, Output, Input, ElementInputs
from webai_element_sdk.element.settings import ElementSettings



class Inputs(ElementInputs):
    input = Input[Frame]()


class Outputs(ElementOutputs):
    output = Output[Frame]()


class Settings(ElementSettings):
    None


element: Element = Element(
    id=UUID("928668fa-61ae-4403-bb83-a5ef2097a347"),
    name="my_element",
    display_name="My Element",
    description="",
    version="0.2.1",
    settings=Settings(),
    inputs=Inputs(),
    outputs=Outputs(),
)


@element.startup
async def startup(ctx: Context[Inputs, Outputs, Settings]):
    pass


@element.shutdown
async def shutdown(ctx: Context[Inputs, Outputs, Settings]):
    pass


@element.executor
async def run(ctx: Context[Inputs, Outputs, Settings]):
    input_frame = ctx.inputs.input.value
    
    yield ctx.outputs.output(input_frame)
    