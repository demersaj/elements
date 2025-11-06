from typing import Any, AsyncIterator, Callable
from uuid import UUID

from webai_element_sdk.comms.messages import Frame
from webai_element_sdk.element import Context, Element
from webai_element_sdk.element.settings import ElementSettings, TextSetting
from webai_element_sdk.element.variables import (
    ElementInputs,
    ElementOutputs,
    Input,
    Output,
)


class Inputs(ElementInputs):
    input_1 = Input[Frame]()


class Outputs(ElementOutputs):
    true = Output[Frame]()
    false = Output[Frame]()


class Settings(ElementSettings):
    condition = TextSetting(
        name="condition",
        display_name="Condition Function",
        description=(
            "Python function that evaluates the condition. The function should take 'frame' as a parameter "
            "and return a boolean. Example: 'return len(frame.rois) > 5' or "
            "'return frame.other_data.get(\"value\", 0) == 10'. "
            "The function body should contain the evaluation logic."
        ),
        default="return len(frame.rois) > 0",
        required=True,
    )


element = Element(
    id=UUID("84827dbd-a23a-4036-919e-f217b862ceb4"),
    name="conditional",
    display_name="Conditional",
    description="Routes input to true or false output based on evaluation logic",
    version="0.1.1",
    inputs=Inputs(),
    outputs=Outputs(),
    settings=Settings(),
)


def compile_condition_function(condition_code: str) -> Callable[[Frame], bool]:
    """
    Compile user-provided Python code into a callable function.

    Args:
        condition_code: Python code that should evaluate to a boolean.
                       The code can reference 'frame' variable.

    Returns:
        A callable function that takes a Frame and returns a boolean.

    Raises:
        SyntaxError: If the code is not valid Python syntax.
        ValueError: If the code doesn't return a boolean value.
    """
    # Wrap the user code in a function definition
    function_code = f"""
def evaluate(frame):
    {condition_code}
"""

    # Create a namespace for the function
    namespace: dict[str, Any] = {}

    try:
        # Compile and execute the function code
        compiled = compile(function_code, "<condition>", "exec")
        exec(compiled, namespace)
    except SyntaxError as e:
        raise SyntaxError(f"Invalid Python syntax in condition: {e}") from e

    # Get the function from the namespace
    evaluate_func = namespace.get("evaluate")
    if evaluate_func is None:
        raise ValueError("Could not compile condition function")

    return evaluate_func  # type: ignore


# Cache compiled functions to avoid recompiling on every execution
_condition_cache: dict[str, Callable[[Frame], bool]] = {}


@element.executor  # type: ignore
async def main(ctx: Context[Inputs, Outputs, Settings]) -> AsyncIterator[Any]:
    try:
        await ctx.logger.log("Starting conditional evaluation")

        frame = ctx.inputs.input_1.value

        if frame is None:
            await ctx.logger.log("Error: Received None frame input")
            raise Exception("Unexpected None frame input.")

        # Get condition code from settings
        condition_code = ctx.settings.condition.value

        # Compile and cache the condition function
        if condition_code not in _condition_cache:
            try:
                _condition_cache[condition_code] = compile_condition_function(condition_code)
                await ctx.logger.log(f"Compiled condition function: {condition_code[:50]}...")
            except (SyntaxError, ValueError) as e:
                await ctx.logger.log(f"Error compiling condition function: {str(e)}")
                raise ValueError(f"Invalid condition function: {str(e)}") from e

        # Evaluate condition
        evaluate_func = _condition_cache[condition_code]
        try:
            result = evaluate_func(frame)
            # Convert result to boolean (handles truthy/falsy values)
            result = bool(result)
        except Exception as e:
            await ctx.logger.log(f"Error evaluating condition: {str(e)}")
            raise ValueError(f"Error executing condition function: {str(e)}") from e

        await ctx.logger.log(f"Condition evaluated: {result}")

        # Route to appropriate output
        if result:
            yield ctx.outputs.true(frame)
        else:
            yield ctx.outputs.false(frame)

    except Exception as e:
        await ctx.logger.log(f"Error in conditional element: {str(e)}")
        raise
