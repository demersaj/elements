from typing import Any, AsyncIterator, Callable
from uuid import UUID

from webai_element_sdk.comms.messages import Frame
from webai_element_sdk.element import Context, Element
from webai_element_sdk.element.settings import (
    ElementSettings,
    NumberSetting,
    TextSetting,
)
from webai_element_sdk.element.variables import (
    ElementInputs,
    ElementOutputs,
    Input,
    Output,
)


class Inputs(ElementInputs):
    input_1 = Input[Frame]()


class Outputs(ElementOutputs):
    route1 = Output[Frame]()
    route2 = Output[Frame]()
    route3 = Output[Frame]()
    route4 = Output[Frame]()
    route5 = Output[Frame]()
    route6 = Output[Frame]()
    route7 = Output[Frame]()
    route8 = Output[Frame]()
    route9 = Output[Frame]()
    route10 = Output[Frame]()


class Settings(ElementSettings):
    num_outputs = NumberSetting[int](
        name="num_outputs",
        display_name="Number of Outputs",
        description=(
            "The number of output routes to create. The routing function should return "
            "a route identifier between 1 and this number (or 'route1' through 'routeN'). "
            "Minimum: 2, Maximum: 10."
        ),
        default=2,
        min_value=2,
        max_value=10,
        required=True,
    )

    routing_function = TextSetting(
        name="routing_function",
        display_name="Routing Function",
        description=(
            "Python function that determines which route to use. The function should take 'frame' as a parameter "
            "and return a route identifier (string like 'route1', 'route2', etc., or integer 1-N where N is the number of outputs). "
            "Example: 'return \"route1\"' or 'return 1' or "
            '\'return "route2" if len(frame.rois) > 5 else "route1"\'. '
            "The function body should contain the routing logic. "
            "The route number must be between 1 and the configured number of outputs."
        ),
        default='return "route1"',
        required=True,
    )


element = Element(
    id=UUID("a1b2c3d4-e5f6-7890-abcd-ef1234567890"),
    name="routing",
    display_name="Routing",
    description="Routes input to one of multiple outputs (2-10) based on routing logic",
    version="0.1.5",
    inputs=Inputs(),
    outputs=Outputs(),
    settings=Settings(),
)


def compile_routing_function(routing_code: str) -> Callable[[Frame], str]:
    """
    Compile user-provided Python code into a callable routing function.

    Args:
        routing_code: Python code that should return a route identifier.
                     The code can reference 'frame' variable.
                     Should return a string like 'route1', 'route2', etc., or integer 1-N.

    Returns:
        A callable function that takes a Frame and returns a route identifier.

    Raises:
        SyntaxError: If the code is not valid Python syntax.
        ValueError: If the code doesn't return a valid route identifier.
    """
    # Wrap the user code in a function definition
    function_code = f"""
def route(frame):
    {routing_code}
"""

    # Create a namespace for the function
    namespace: dict[str, Any] = {}

    try:
        # Compile and execute the function code
        compiled = compile(function_code, "<routing>", "exec")
        exec(compiled, namespace)
    except SyntaxError as e:
        raise SyntaxError(f"Invalid Python syntax in routing function: {e}") from e

    # Get the function from the namespace
    route_func = namespace.get("route")
    if route_func is None:
        raise ValueError("Could not compile routing function")

    return route_func  # type: ignore


def normalize_route_identifier(route_value: Any, num_outputs: int) -> str:
    """
    Normalize route identifier to a standard format (route1, route2, ..., routeN).

    Args:
        route_value: Route identifier from user function (string, int, etc.)
        num_outputs: Maximum number of outputs configured

    Returns:
        Normalized route identifier string (route1 through routeN)
    """
    # Handle string inputs
    if isinstance(route_value, str):
        route_str = route_value.lower().strip()
        # If already in routeN format, extract the number
        if route_str.startswith("route"):
            try:
                route_num = int(route_str[5:])
                if 1 <= route_num <= num_outputs:
                    return f"route{route_num}"
            except ValueError:
                pass
        # Try to match numeric strings
        try:
            route_num = int(route_str)
            if 1 <= route_num <= num_outputs:
                return f"route{route_num}"
        except ValueError:
            pass
        # Default to route1 if not recognized
        return "route1"

    # Handle integer inputs
    if isinstance(route_value, int):
        if 1 <= route_value <= num_outputs:
            return f"route{route_value}"
        # Clamp to valid range
        if route_value < 1:
            return "route1"
        return f"route{num_outputs}"

    # Handle boolean (convert to route1 or route2, but respect num_outputs)
    if isinstance(route_value, bool):
        if num_outputs >= 2:
            return "route1" if route_value else "route2"
        return "route1"

    # Default fallback
    return "route1"


# Cache compiled functions to avoid recompiling on every execution
_routing_cache: dict[str, Callable[[Frame], Any]] = {}


@element.executor  # type: ignore
async def main(ctx: Context[Inputs, Outputs, Settings]) -> AsyncIterator[Any]:
    try:
        await ctx.logger.log("Starting routing evaluation")

        frame = ctx.inputs.input_1.value

        if frame is None:
            await ctx.logger.log("Error: Received None frame input")
            raise Exception("Unexpected None frame input.")

        # Get number of outputs from settings
        num_outputs = ctx.settings.num_outputs.value

        # Get routing code from settings
        routing_code = ctx.settings.routing_function.value

        # Create cache key that includes num_outputs to handle changes
        cache_key = f"{routing_code}:{num_outputs}"

        # Compile and cache the routing function
        if cache_key not in _routing_cache:
            try:
                _routing_cache[cache_key] = compile_routing_function(routing_code)
                await ctx.logger.log(f"Compiled routing function: {routing_code[:50]}...")
            except (SyntaxError, ValueError) as e:
                await ctx.logger.log(f"Error compiling routing function: {str(e)}")
                raise ValueError(f"Invalid routing function: {str(e)}") from e

        # Evaluate routing function
        route_func = _routing_cache[cache_key]
        try:
            route_result = route_func(frame)
            # Normalize route identifier with num_outputs
            route_id = normalize_route_identifier(route_result, num_outputs)
        except Exception as e:
            await ctx.logger.log(f"Error evaluating routing function: {str(e)}")
            raise ValueError(f"Error executing routing function: {str(e)}") from e

        await ctx.logger.log(f"Routing to: {route_id} (out of {num_outputs} outputs)")

        # Build route map dynamically based on num_outputs
        route_map: dict[str, Any] = {}
        for i in range(1, num_outputs + 1):
            route_name = f"route{i}"
            # Use getattr to dynamically access the output attribute
            route_map[route_name] = getattr(ctx.outputs, route_name, None)
            if route_map[route_name] is None:
                await ctx.logger.log(
                    f"Warning: Output {route_name} not found, defaulting to route1"
                )
                route_id = "route1"
                break

        # Route to appropriate output
        output_func = route_map.get(route_id, ctx.outputs.route1)
        if output_func is None:
            output_func = ctx.outputs.route1

        yield output_func(frame)

    except Exception as e:
        await ctx.logger.log(f"Error in routing element: {str(e)}")
        raise
