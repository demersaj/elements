from uuid import UUID

from webai_element_sdk.comms.messages import Frame
from webai_element_sdk.element import Context, Element
from webai_element_sdk.element.variables import ElementOutputs, Output, Input, ElementInputs
from webai_element_sdk.element.settings import ElementSettings



class Inputs(ElementInputs):
    """
    Each input can be either a single frame or a stream of frames.
    Inputs are how your element receives data from other elements.
    """
    input = Input[Frame]()


class Outputs(ElementOutputs):
    """
    Each output can be either a single frame or a stream of frames.
    Outputs are how your element sends data to other elements.
    """
    output = Output[Frame]()


class Settings(ElementSettings):
    """
    Settings allow users to configure your element's behavior.
    You can create Text, Number, or Boolean settings with validation rules.
    """
    None


element: Element = Element(
    id=UUID("aa72bb55-93d8-4bf3-85d0-e0a56e892f4a"),
    name="test_element",
    display_name="test element",
    description="",
    version="0.1.0",
    settings=Settings(),
    inputs=Inputs(),
    outputs=Outputs(),
)


@element.startup
async def startup(ctx: Context[Inputs, Outputs, Settings]):
    pass
    # Called when the element starts up.
    # Use this to initialize any resources your element needs.
    # This is a good place to set up connections, load models, or prepare data.


@element.shutdown
async def shutdown(ctx: Context[Inputs, Outputs, Settings]):
    pass
    # Called when the element shuts down.
    # Use this to clean up any resources your element created.
    # This is a good place to close connections, save state, or clean up.


@element.executor
async def run(ctx: Context[Inputs, Outputs, Settings]):
    # Main execution function that processes inputs and produces outputs.
    # Implement your element's core functionality here.
    input_frame = ctx.inputs.input.value
    
    yield ctx.outputs.output(input_frame)
    