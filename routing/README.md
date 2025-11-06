# Routing Element

Routes input data to one of two outputs (route1 or route2) based on user-defined routing logic. This element allows a primary element to decide which pre-defined specialized model or prompt chain to call next, enabling dynamic workflow routing and conditional branching.

## Overview

The Routing element evaluates a routing function against incoming Frame data and routes it to one of two available outputs (route1 or route2) based on the routing decision. This enables conditional logic and dynamic workflow routing in your WebAI pipelines.

## Features

- **Flexible Input**: Accepts any valid Frame input from other elements
- **Dual Outputs**: Routes data to one of two outputs (route1 or route2) based on routing logic
- **Python Function Evaluation**: Write custom Python code to determine routing
- **Direct Frame Access**: Access Frame properties directly (e.g., `frame.rois`, `frame.other_data`)
- **Flexible Route Identifiers**: Return route names as strings ("route1", "route2") or integers (1-2)
- **Full Python Expressiveness**: Use any Python expression, operators, and logic

## Configuration

### Element Settings

| Setting | Type | Default | Description |
|---------|------|---------|-------------|
| `routing_function` | Text (Python) | `return "route1"` | Python code that evaluates to a route identifier. The code can reference `frame` variable and should return a string like "route1", "route2", or an integer 1-2 |

### Routing Function Format

The routing function is specified as Python code that evaluates to a route identifier. The code has access to a `frame` variable representing the incoming Frame object.

**Basic Structure:**

```python
return <route_identifier>
```

**Route Identifiers:**

- String format: `"route1"`, `"route2"`
- Integer format: `1`, `2` (will be converted to route1 or route2)
- The element will normalize various formats automatically

**Frame Access Examples:**

- `frame.rois` - Access the list of regions of interest
- `len(frame.rois)` - Get the number of ROIs
- `frame.other_data` - Access the other_data dictionary
- `frame.other_data.get("value", 0)` - Get a value with default
- `frame.other_data["message"]` - Direct dictionary access
- `frame.rois[0].classes[0].label` - Access nested structures

## Usage Examples

### Example 1: Route Based on ROI Count

Route frames with more than 5 detected objects to route2, otherwise route1:

```python
if len(frame.rois) > 5:
    return "route2"
else:
    return "route1"
```

### Example 2: Route Based on String Value

Route frames where the message contains "error" to route2:

```python
if "error" in frame.other_data.get("message", "").lower():
    return "route2"
return "route1"
```

### Example 3: Route Based on Numeric Value

Route frames based on score thresholds:

```python
score = frame.other_data.get("score", 0)
if score > 0.8:
    return "route1"  # High confidence - use specialized model
else:
    return "route2"  # Lower confidence - use standard model
```

### Example 4: Route Based on Object Classes

Route frames containing specific object classes:

```python
for roi in frame.rois:
    for cls in roi.classes:
        if cls.label == "person":
            return "route1"  # Person detection - use person-specific model
        elif cls.label == "vehicle":
            return "route2"  # Vehicle detection - use vehicle-specific model
return "route1"  # Default route
```

### Example 5: Using Integer Route Identifiers

You can also return integers directly:

```python
roi_count = len(frame.rois)
if roi_count > 5:
    return 1  # Will route to route1
else:
    return 2  # Will route to route2
```

### Example 6: Complex Multi-Condition Routing

Route based on multiple conditions:

```python
roi_count = len(frame.rois)
score = frame.other_data.get("score", 0)
message = frame.other_data.get("message", "")

if roi_count > 10 and score > 0.8:
    return "route1"  # High-quality detection - use premium model
elif "urgent" in message.lower():
    return "route1"  # Urgent message - use premium model
elif roi_count == 0:
    return "route2"  # No detections - use fallback
else:
    return "route2"  # Default processing
```

### Example 7: Route Based on Model Selection

Route to different specialized models based on content analysis:

```python
# Analyze frame content to determine which specialized model to use
content_type = frame.other_data.get("content_type", "")

if content_type == "image_classification":
    return "route1"  # Route to image classification model
else:
    return "route2"  # Route to general purpose model
```

### Example 8: Route LLM Requests Based on Message Content

Route LLM requests to different prompt chains or models based on the user's message:

```python
# Extract messages from frame (when coming from API element)
messages = frame.other_data.get("api", [])
if not messages:
    return "route1"  # Default route

# Get the last user message
last_message = None
for msg in reversed(messages):
    if isinstance(msg, dict) and msg.get("role") == "user":
        last_message = msg.get("content", "")
        break

if not last_message:
    return "route1"

# Route based on message content
message_lower = last_message.lower()

# Route technical questions to specialized technical LLM
if any(keyword in message_lower for keyword in ["code", "programming", "debug", "error", "function"]):
    return "route1"  # Technical LLM chain

# Route customer service questions to customer support LLM
elif any(keyword in message_lower for keyword in ["help", "support", "issue", "problem", "refund"]):
    return "route2"  # Customer support LLM chain

# Default to general purpose LLM
else:
    return "route1"  # General purpose LLM
```

### Example 9: Route Based on Message Length and Complexity

Route LLM requests based on message characteristics:

```python
messages = frame.other_data.get("api", [])
if not messages:
    return "route1"

# Get user message content
user_content = ""
for msg in messages:
    if isinstance(msg, dict) and msg.get("role") == "user":
        content = msg.get("content", "")
        if isinstance(content, str):
            user_content += content + " "

# Route short/simple questions to fast model
if len(user_content) < 100:
    return "route2"  # Fast, lightweight LLM

# Route complex/long questions to powerful model
else:
    return "route1"  # More capable LLM for complex reasoning
```

### Example 10: Route Based on Conversation Context

Route based on conversation history and context:

```python
messages = frame.other_data.get("api", [])
if not messages:
    return "route1"

# Count messages to determine conversation stage
message_count = len([m for m in messages if isinstance(m, dict)])

# Route initial messages to onboarding chain
if message_count <= 2:
    return "route2"  # Onboarding/setup prompt chain

# Route ongoing conversations to main chain
else:
    return "route1"  # Main conversation chain
```

## LLM Integration Example

Here's a complete workflow example showing how to use the Routing element with LLMs:

### Workflow Setup

1. **API Element** → Receives LLM requests and creates frames with messages in `frame.other_data["api"]`
2. **Routing Element** → Analyzes the messages and routes to appropriate LLM chain
3. **Route1** → Connects to specialized LLM element (e.g., technical support model)
4. **Route2** → Connects to different LLM element (e.g., general purpose model)

### Routing Function for LLM Requests

```python
# Extract messages from the API element
messages = frame.other_data.get("api", [])

# If no messages, use default route
if not messages or not isinstance(messages, list):
    return "route1"

# Get the user's message content
user_message = ""
for msg in messages:
    if isinstance(msg, dict):
        role = msg.get("role", "")
        content = msg.get("content", "")

        # Handle both string and list content formats
        if isinstance(content, str):
            user_message = content
        elif isinstance(content, list):
            # Extract text from multimodal content
            text_parts = [item.get("text", "") for item in content if isinstance(item, dict) and item.get("type") == "text"]
            user_message = " ".join(text_parts)

        if role == "user" and user_message:
            break

# Route based on message analysis
if not user_message:
    return "route1"

user_lower = user_message.lower()

# Route technical questions to specialized technical LLM (route1)
technical_keywords = ["code", "programming", "python", "javascript", "debug", "error",
                      "function", "algorithm", "api", "database", "sql", "git"]
if any(keyword in user_lower for keyword in technical_keywords):
    return "route1"

# Route customer service to support LLM (route2)
support_keywords = ["help", "support", "issue", "problem", "refund", "cancel",
                    "order", "payment", "account", "billing"]
if any(keyword in user_lower for keyword in support_keywords):
    return "route2"

# Default to general purpose LLM (route1)
return "route1"
```

### Use Case: Multi-Model LLM Routing

**Scenario**: You have two LLM elements configured:

- **LLM Element 1** (route1): Specialized technical assistant with code-focused prompts
- **LLM Element 2** (route2): General purpose assistant for everyday questions

**Setup**:

1. Connect API element output → Routing element input
2. Configure routing function to analyze message content
3. Connect Routing route1 → LLM Element 1
4. Connect Routing route2 → LLM Element 2

**Result**: Incoming requests are automatically routed to the appropriate LLM based on the content of the user's message, ensuring users get the most relevant responses.

## Navigator Usage

1. Drag the Routing element onto your canvas
2. Connect any element's output to the Routing element's input
3. Open the Routing element's settings
4. Enter your routing function as Python code in the "Routing Function" field
5. Connect the desired route outputs (route1 or route2) to downstream elements (specialized models or prompt chains)
6. Each route can connect to a different specialized model or processing chain

## Outputs

- **route1**: Emits the input Frame when routing function returns route1 (or 1)
- **route2**: Emits the input Frame when routing function returns route2 (or 2)

## Use Cases

### Specialized Model Routing

Route frames to different specialized models based on content analysis:

- Route1: High-precision model for critical detections
- Route2: Fast model for real-time processing or fallback

### Prompt Chain Selection

Route to different prompt chains based on input characteristics:

- Route1: Technical documentation chain
- Route2: Customer support chain

### Conditional Processing

Route frames through different processing pipelines:

- Route1: Full analysis pipeline
- Route2: Quick analysis pipeline

## Notes

- The routing function code must be valid Python syntax
- The function should return a route identifier (string "route1" or "route2", or integer 1-2)
- You have full access to the `frame` object and all its properties
- The function is compiled once and cached for performance
- Route identifiers are automatically normalized (e.g., "Route1", "route1", 1 all map to route1)
- If an invalid route identifier is returned, the element defaults to route1
- The original Frame data is passed through unchanged to the selected output
- You can use any Python expressions, operators, and control flow (if/else, loops, etc.)
- Only one output will receive the frame per execution (exclusive routing)

## Troubleshooting

**Routing not working:**

- Verify the Python syntax is valid
- Ensure the code returns a route identifier (string or integer)
- Check that you're accessing frame properties correctly
- Review the logs for compilation and execution errors

**Syntax errors:**

- Make sure your Python code is properly formatted
- Remember to use `return` statement
- Check for missing quotes, parentheses, or brackets

**Runtime errors:**

- Ensure frame properties exist before accessing them (use `.get()` for dictionaries)
- Handle None values appropriately
- Check the logs for specific error messages

**Unexpected routing:**

- Verify your routing logic returns the expected route identifier
- Check that route identifiers are in the correct format (route1-route2 or 1-2)
- Review logs to see which route was selected

## Comparison with Conditional Element

The Routing element is similar to the Conditional element but provides more flexibility:

- **Conditional**: Routes to exactly 2 outputs (true/false) with boolean logic
- **Routing**: Routes to 2 outputs (route1/route2) with flexible routing logic that can return strings or integers

Use Routing when you want more expressive routing logic or need to route based on complex conditions beyond simple boolean evaluation.
