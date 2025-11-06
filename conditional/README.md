# Conditional Element

Routes input data to one of two outputs (true or false) based on user-defined evaluation logic. Similar to n8n's "If" node, this element allows you to create conditional branching in your workflows.

## Overview

The Conditional element evaluates a condition against incoming Frame data and routes it to either the `true` or `false` output based on whether the condition is met. This enables conditional logic and branching in your WebAI workflows.

## Features

- **Flexible Input**: Accepts any valid Frame input from other elements
- **Dual Outputs**: Routes data to `true` or `false` output based on condition evaluation
- **Python Function Evaluation**: Write custom Python code to evaluate conditions
- **Direct Frame Access**: Access Frame properties directly (e.g., `frame.rois`, `frame.other_data`)
- **Full Python Expressiveness**: Use any Python expression, operators, and logic

## Configuration

### Element Settings

| Setting | Type | Default | Description |
|---------|------|---------|-------------|
| `condition` | Text (Python) | `return len(frame.rois) > 0` | Python code that evaluates to a boolean. The code can reference `frame` variable and should return a boolean value |

### Condition Format

The condition is specified as Python code that evaluates to a boolean. The code has access to a `frame` variable representing the incoming Frame object.

**Basic Structure:**

```python
return <your_condition_expression>
```

**Frame Access Examples:**

- `frame.rois` - Access the list of regions of interest
- `len(frame.rois)` - Get the number of ROIs
- `frame.other_data` - Access the other_data dictionary
- `frame.other_data.get("value", 0)` - Get a value with default
- `frame.other_data["message"]` - Direct dictionary access
- `frame.rois[0].classes[0].label` - Access nested structures

## Usage Examples

### Example 1: Check ROI Count

Route frames with more than 5 detected objects to the true output:

```python
return len(frame.rois) > 5
```

### Example 2: Check String Value

Route frames where the message contains "error":

```python
return "error" in frame.other_data.get("message", "").lower()
```

### Example 3: Check Numeric Value

Route frames where the score equals a specific value:

```python
return frame.other_data.get("score", 0) == 0.95
```

### Example 4: Check if Empty

Route frames with no detected objects:

```python
return len(frame.rois) == 0
```

### Example 5: Complex Condition

Route frames with multiple conditions:

```python
roi_count = len(frame.rois)
score = frame.other_data.get("score", 0)
return roi_count > 5 and score > 0.8
```

### Example 6: Check ROI Classes

Route frames containing specific object classes:

```python
for roi in frame.rois:
    for cls in roi.classes:
        if cls.label == "person":
            return True
return False
```

## Navigator Usage

1. Drag the Conditional element onto your canvas
2. Connect any element's output to the Conditional element's input
3. Open the Conditional element's settings
4. Enter your condition as Python code in the "Condition Function" field
5. Connect the `true` and `false` outputs to downstream elements as needed

## Outputs

- **true**: Emits the input Frame when the condition evaluates to `true`
- **false**: Emits the input Frame when the condition evaluates to `false`

## Notes

- The condition code must be valid Python syntax
- The code should return a boolean value (or a value that can be converted to bool)
- You have full access to the `frame` object and all its properties
- The function is compiled once and cached for performance
- Non-boolean return values are automatically converted to boolean
- The original Frame data is passed through unchanged to the selected output
- You can use any Python expressions, operators, and control flow (if/else, loops, etc.)

## Troubleshooting

**Condition not working:**

- Verify the Python syntax is valid
- Ensure the code returns a boolean value (or a value convertible to bool)
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
