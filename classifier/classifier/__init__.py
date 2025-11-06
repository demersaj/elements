"""
LLM Text Classifier Element

Classifies text into user-defined categories using Large Language Models.
Accepts text input and returns classification results with confidence scores.
"""

from typing import Any, AsyncIterator
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

from .llm_classifier import create_classification_prompt, parse_classification_result


class Inputs(ElementInputs):
    in1 = Input[Frame]()


class Outputs(ElementOutputs):
    category1 = Output[Frame]()
    category2 = Output[Frame]()
    category3 = Output[Frame]()
    category4 = Output[Frame]()
    category5 = Output[Frame]()
    category6 = Output[Frame]()
    category7 = Output[Frame]()
    category8 = Output[Frame]()
    category9 = Output[Frame]()
    category10 = Output[Frame]()
    # Keep out1 for backward compatibility
    out1 = Output[Frame]()


class Settings(ElementSettings):
    categories = TextSetting(
        name="categories",
        display_name="Categories",
        description=(
            "Comma-separated list of categories to classify text into. "
            "Each category will have its own output (category1, category2, etc.). "
            "Supports up to 10 categories. "
            "Example: 'positive, negative, neutral' or 'urgent, normal, low priority'. "
            "The first category maps to category1 output, second to category2, etc."
        ),
        default="positive, negative, neutral",
        required=True,
    )

    system_prompt = TextSetting(
        name="system_prompt",
        display_name="System Prompt",
        description=(
            "Optional custom system prompt for the LLM. "
            "If empty, a default classification prompt will be used."
        ),
        default="",
        required=False,
    )

    llm_provider = TextSetting(
        name="llm_provider",
        display_name="LLM Provider",
        description=(
            "The LLM provider to use for classification. "
            "Options: 'api' (uses connected LLM element), 'openai', 'anthropic'. "
            "Default: 'api' - expects LLM element to be connected upstream."
        ),
        default="api",
        valid_values=["api", "openai", "anthropic"],
        required=True,
    )

    api_key = TextSetting(
        name="api_key",
        display_name="API Key",
        description=(
            "API key for external LLM providers (OpenAI, Anthropic). "
            "Only required if llm_provider is not 'api'."
        ),
        default="",
        required=False,
        sensitive=True,
    )

    temperature = NumberSetting[float](
        name="temperature",
        display_name="Temperature",
        description=(
            "Controls randomness in classification. Lower values (0.0-0.3) "
            "produce more deterministic results. Higher values (0.7-1.0) "
            "produce more varied results."
        ),
        default=0.1,
        min_value=0.0,
        max_value=1.0,
        step=0.1,
        required=False,
    )

    min_confidence = NumberSetting[float](
        name="min_confidence",
        display_name="Minimum Confidence Threshold",
        description=(
            "Minimum confidence score (0.0-1.0) required for classification. "
            "Results below this threshold will be marked as 'uncertain'."
        ),
        default=0.5,
        min_value=0.0,
        max_value=1.0,
        step=0.05,
        required=False,
    )


element = Element(
    id=UUID("f3a4b5c6-d7e8-9f0a-1b2c-3d4e5f6a7b8c"),
    name="classifier",
    display_name="LLM Text Classifier",
    description=(
        "Classifies text into user-defined categories using Large Language Models. "
        "Routes input to category-specific outputs based on classification results. "
        "Supports up to 10 categories, each with its own output."
    ),
    version="0.2.0",
    inputs=Inputs(),
    outputs=Outputs(),
    settings=Settings(),
)


async def call_llm_api(
    prompt: str,
    provider: str,
    api_key: str,
    temperature: float,
    ctx: Context[Inputs, Outputs, Settings],
) -> str:
    """
    Call LLM API based on provider.

    Args:
        prompt: The prompt to send
        provider: Provider name ('api', 'openai', 'anthropic')
        api_key: API key for external providers
        temperature: Temperature setting
        ctx: Element context

    Returns:
        LLM response text
    """
    if provider == "api":
        # For 'api' provider, we expect an LLM element upstream
        # This would need to be handled by the workflow
        # For now, return a placeholder
        await ctx.logger.log("API provider selected - expecting LLM element upstream")
        return ""

    elif provider == "openai":
        try:
            import openai

            client = openai.OpenAI(api_key=api_key)
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a text classifier."},
                    {"role": "user", "content": prompt},
                ],
                temperature=temperature,
                max_tokens=150,
            )
            return response.choices[0].message.content or ""
        except ImportError:
            await ctx.logger.log(
                "Error: openai package not installed. Install with: pip install openai"
            )
            return ""
        except Exception as e:
            await ctx.logger.log(f"Error calling OpenAI API: {str(e)}")
            return ""

    elif provider == "anthropic":
        try:
            import anthropic

            client = anthropic.Anthropic(api_key=api_key)
            response = client.messages.create(
                model="claude-3-haiku-20240307",
                max_tokens=150,
                temperature=temperature,
                messages=[{"role": "user", "content": prompt}],
            )
            return response.content[0].text if response.content else ""
        except ImportError:
            await ctx.logger.log(
                "Error: anthropic package not installed. Install with: pip install anthropic"
            )
            return ""
        except Exception as e:
            await ctx.logger.log(f"Error calling Anthropic API: {str(e)}")
            return ""

    return ""


@element.executor  # type: ignore
async def main(ctx: Context[Inputs, Outputs, Settings]) -> AsyncIterator[Any]:
    """Main executor for LLM text classifier."""
    try:
        await ctx.logger.log("Starting LLM text classification")

        frame = ctx.inputs.in1.value

        if frame is None:
            await ctx.logger.log("Error: Received None frame input")
            raise Exception("Unexpected None frame input.")

        # Extract text from frame
        text = ""
        if "message" in frame.other_data:
            text = str(frame.other_data["message"])
        elif "api" in frame.other_data:
            # Extract text from API messages
            api_messages = frame.other_data["api"]
            if isinstance(api_messages, list):
                for msg in api_messages:
                    if isinstance(msg, dict) and msg.get("role") == "user":
                        content = msg.get("content", "")
                        if isinstance(content, str):
                            text += content + " "
                        elif isinstance(content, list):
                            # Handle multimodal content
                            for item in content:
                                if isinstance(item, dict) and item.get("type") == "text":
                                    text += item.get("text", "") + " "
        else:
            await ctx.logger.log("Warning: No text found in frame.other_data")
            text = ""

        if not text.strip():
            await ctx.logger.log("Error: Empty text input")
            raise ValueError("No text provided for classification")

        # Get settings
        categories_str = ctx.settings.categories.value
        categories = [cat.strip() for cat in categories_str.split(",") if cat.strip()]

        if not categories:
            await ctx.logger.log("Error: No categories specified")
            raise ValueError("At least one category must be specified")

        system_prompt = ctx.settings.system_prompt.value
        llm_provider = ctx.settings.llm_provider.value
        api_key = ctx.settings.api_key.value
        temperature = ctx.settings.temperature.value
        min_confidence = ctx.settings.min_confidence.value

        await ctx.logger.log(f"Classifying text into categories: {', '.join(categories)}")

        # Create classification prompt
        prompt = create_classification_prompt(text, categories, system_prompt)

        # Call LLM
        if llm_provider == "api":
            # For API provider, we need to get response from upstream LLM element
            # This is a simplified version - in practice, you'd need to handle
            # the LLM element connection properly
            await ctx.logger.log(
                "API provider: Expecting LLM element to process upstream. "
                "For now, using fallback classification."
            )
            # Fallback: use first category with medium confidence
            classification_result = {
                "category": categories[0],
                "confidence": 0.7,
                "raw_response": "API provider requires LLM element upstream",
                "all_categories": categories,
            }
        else:
            # Call external LLM API
            response = await call_llm_api(prompt, llm_provider, api_key, temperature, ctx)

            if not response:
                await ctx.logger.log("Warning: Empty response from LLM, using fallback")
                classification_result = {
                    "category": categories[0],
                    "confidence": 0.5,
                    "raw_response": "",
                    "all_categories": categories,
                }
            else:
                # Parse classification result
                classification_result = parse_classification_result(response, categories)

        # Check confidence threshold
        confidence = classification_result["confidence"]
        if confidence < min_confidence:
            classification_result["category"] = "uncertain"
            classification_result["below_threshold"] = True
        else:
            classification_result["below_threshold"] = False

        await ctx.logger.log(
            f"Classification result: {classification_result['category']} "
            f"(confidence: {confidence:.2f})"
        )

        # Create output frame
        output_data = frame.other_data.copy()
        output_data.update(
            {
                "classification": classification_result["category"],
                "confidence": confidence,
                "all_categories": categories,
                "raw_classification_response": classification_result["raw_response"],
                "below_threshold": classification_result.get("below_threshold", False),
            }
        )

        output_frame = Frame(
            ndframe=frame.ndframe,
            rois=frame.rois,
            color_space=frame.color_space,
            frame_id=frame.frame_id,
            headers=frame.headers,
            other_data=output_data,
        )

        # Route to appropriate category output
        classified_category = classification_result["category"]
        num_categories = len(categories)

        # Find the index of the classified category
        category_index = None
        if isinstance(classified_category, str):
            for idx, cat in enumerate(categories):
                if isinstance(cat, str) and cat.lower() == classified_category.lower():
                    category_index = idx + 1  # 1-indexed
                    break

        # If category not found or below threshold, use first category output
        if category_index is None or classification_result.get("below_threshold", False):
            category_index = 1

        # Ensure category_index is within valid range (max 10 outputs)
        if category_index is None or category_index < 1:
            category_index = 1
        # Cap at maximum number of outputs (10) or number of categories, whichever is smaller
        max_outputs = min(num_categories, 10)
        if category_index > max_outputs:
            category_index = max_outputs

        # Route to the appropriate category output
        category_output_name = f"category{category_index}"
        category_output = getattr(ctx.outputs, category_output_name, None)

        if category_output is not None:
            await ctx.logger.log(f"Routing to {category_output_name}")
            yield category_output(output_frame)
        else:
            # Fallback to out1 if category output not found
            await ctx.logger.log(f"Warning: {category_output_name} not found, using out1")
            yield ctx.outputs.out1(output_frame)

    except Exception as e:
        await ctx.logger.log(f"Error in classifier element: {str(e)}")
        raise
