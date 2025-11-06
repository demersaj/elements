# Prompt Chain Element

## Overview

The Prompt Chain element enables multi-step LLM workflows by chaining prompts together, where each step processes the output of the previous step. This element supports both local LLMs (via upstream LLM elements) and cloud-based models (OpenAI, Anthropic), making it ideal for building sophisticated multi-step applications like agents, complex content generation, and data analysis pipelines.

## Features

- **Multi-Step Chaining**: Decompose complex tasks into a sequence of steps (up to 10 steps)
- **Flexible Model Selection**: Each step can use a different model (local, OpenAI, Anthropic)
- **Prompt Templates**: Use `{input}` and `{previous}` placeholders to reference inputs and previous outputs
- **Intermediate Outputs**: Each step emits its own output for debugging and inspection
- **Transparent Execution**: See the exact prompt and response for every step
- **State Management**: Automatically passes output from one step to the next

## Configuration

### Element Settings

| Setting | Type | Default | Description |
|---------|------|---------|-------------|
| `num_steps` | Number | `2` | Number of steps in the chain (1-10) |
| `stepN_prompt` | Text | - | Prompt template for step N. Use `{input}` for initial input, `{previous}` for previous step output |
| `stepN_model` | Text | `"local"` | Model for step N: 'local', 'openai', or 'anthropic' |
| `stepN_api_key` | Text | `""` | API key for step N (required for cloud models) |
| `stepN_temperature` | Number | `0.7` | Temperature for step N (0.0-1.0) |

### Input

- **in1**: Accepts Frame input with text in `frame.other_data["message"]` or `frame.other_data["api"]`

### Outputs

- **step1** through **step10**: Intermediate outputs for each step (contains step output, prompt, and model info)
- **final**: Final output containing the result of the last step and complete chain history

## Usage Examples

### Example 1: Simple 2-Step Chain

**Settings:**

- Number of Steps: `2`
- Step 1 Prompt: `"Analyze the sentiment of this text: {input}"`
- Step 1 Model: `local`
- Step 2 Prompt: `"Based on this analysis: {previous}, provide recommendations"`
- Step 2 Model: `local`

**Input Text:** "I love this product! It works perfectly."

**Execution:**

1. Step 1 processes: "Analyze the sentiment of this text: I love this product! It works perfectly."
2. Step 1 output: "Sentiment: Positive (0.95 confidence)"
3. Step 2 processes: "Based on this analysis: Sentiment: Positive (0.95 confidence), provide recommendations"
4. Step 2 output: "Recommendations: Continue current approach, consider highlighting positive features"

**Final Output:** Contains Step 2 output plus complete chain history

### Example 2: Multi-Model Chain

**Settings:**

- Number of Steps: `3`
- Step 1 Prompt: `"Summarize: {input}"`
- Step 1 Model: `openai`
- Step 1 API Key: `sk-...`
- Step 2 Prompt: `"Extract key points from: {previous}"`
- Step 2 Model: `anthropic`
- Step 2 API Key: `sk-ant-...`
- Step 3 Prompt: `"Create action items from: {previous}"`
- Step 3 Model: `local`

**Use Case:** Use OpenAI for summarization, Anthropic for extraction, and local model for final formatting.

### Example 3: Content Generation Pipeline

**Settings:**

- Number of Steps: `4`
- Step 1: `"Generate ideas for: {input}"` (Model: local)
- Step 2: `"Expand on this idea: {previous}"` (Model: openai)
- Step 3: `"Refine and polish: {previous}"` (Model: local)
- Step 4: `"Add formatting: {previous}"` (Model: local)

**Result:** A complete content generation pipeline with multiple refinement steps.

## Prompt Template Syntax

### Placeholders

- `{input}`: Replaced with the initial input text
- `{previous}`: Replaced with the output from the previous step
  - In step 1, `{previous}` is replaced with `{input}` if no previous output exists

### Examples

```python
# Step 1: Use initial input
"Analyze: {input}"

# Step 2: Use previous step output
"Continue with: {previous}"

# Step 3: Combine both
"Compare {input} with {previous}"
```

## Workflow Integration

### Using with LLM Element (Local Model)

1. Connect **LLM Element** → **Chain Element**
2. Set chain step models to `"local"`
3. Chain element will use the upstream LLM for local steps

### Using with Cloud Models

1. Set step model to `"openai"` or `"anthropic"`
2. Provide API key in step settings
3. Chain element will call the cloud API directly

### Using with Routing Element

1. Connect **Chain Element** → **Routing Element**
2. Use chain output in routing logic:

   ```python
   chain_output = frame.other_data.get("chain_final_output", "")
   if "error" in chain_output.lower():
       return "route1"  # Error handling route
   else:
       return "route2"  # Success route
   ```

### Using with Classifier Element

1. Connect **Chain Element** → **Classifier Element**
2. Classify the final chain output into categories
3. Route to different handlers based on classification

## Best Practices

1. **Step Design**: Keep each step focused on a single task. This makes debugging easier and improves reliability.

2. **Model Selection**:
   - Use local models for simple transformations
   - Use cloud models for complex reasoning or when you need specific model capabilities
   - Consider cost when using cloud models in long chains

3. **Prompt Templates**:
   - Be explicit about what each step should do
   - Use clear instructions in prompts
   - Test prompts individually before chaining

4. **Error Handling**:
   - Monitor intermediate outputs for errors
   - Use routing elements after chains to handle different outcomes
   - Set appropriate temperature values (lower for deterministic steps)

5. **Debugging**:
   - Use intermediate step outputs to inspect each step's result
   - Check `chain_history` in final output to see all steps
   - Review prompts and outputs for each step

## Troubleshooting

**Empty Step Outputs:**

- Verify prompt template is configured
- Check API keys for cloud models
- Ensure upstream LLM element is connected (for local models)
- Review logs for specific error messages

**Incorrect Chain Results:**

- Inspect intermediate outputs to identify which step failed
- Verify prompt templates use correct placeholders
- Check that previous step outputs are being passed correctly
- Review temperature settings (may be too high/low)

**Local Model Not Working:**

- Ensure LLM element is connected upstream
- Verify LLM element is properly configured
- Check that local model is running and accessible

**Cloud API Errors:**

- Verify API keys are correct and have sufficient credits
- Check network connectivity
- Review API rate limits
- Ensure model names are correct

## Output Structure

### Step Outputs (step1-step10)

```json
{
  "chain_step": 1,
  "chain_output": "Step 1 result...",
  "chain_prompt": "Prompt used...",
  "chain_model": "local",
  "chain_history": [
    {
      "step": 1,
      "prompt": "...",
      "output": "...",
      "model": "local"
    }
  ]
}
```

### Final Output

```json
{
  "chain_final_output": "Final result...",
  "chain_steps": 3,
  "chain_complete": true,
  "chain_history": [
    {
      "step": 1,
      "prompt": "...",
      "output": "...",
      "model": "local"
    },
    {
      "step": 2,
      "prompt": "...",
      "output": "...",
      "model": "openai"
    },
    {
      "step": 3,
      "prompt": "...",
      "output": "...",
      "model": "local"
    }
  ]
}
```

## Notes

- The element automatically manages state between steps
- Each step's output becomes the input for the next step
- Intermediate outputs are available for debugging and inspection
- Chain execution stops if a step is not configured
- Maximum of 10 steps supported
- For local models, ensure an LLM element is connected upstream
- Cloud model API calls are made directly from the element

## Future Enhancements

Potential future features:

- Conditional step execution based on previous outputs
- Parallel step execution
- Step retry logic
- Custom step validation
- Step-level error handling
