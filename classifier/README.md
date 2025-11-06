# Classifier Element

## Overview

The Classifier element uses Large Language Models (LLMs) to classify text into user-defined categories. It accepts text input and returns classification results with confidence scores, making it useful for sentiment analysis, content categorization, intent detection, and other text classification tasks.

## Features

- **Flexible Categories**: Define custom categories for classification
- **LLM-Powered**: Uses LLMs for accurate text understanding and classification
- **Confidence Scores**: Returns confidence scores for each classification
- **Multiple Providers**: Supports API-based LLMs (via upstream LLM element), OpenAI, and Anthropic
- **Custom Prompts**: Optional custom system prompts for specialized classification tasks
- **Confidence Thresholding**: Filter results below a minimum confidence threshold

## Configuration

### Element Settings

| Setting | Type | Default | Description |
|---------|------|---------|-------------|
| `categories` | Text | `"positive, negative, neutral"` | Comma-separated list of categories to classify into |
| `system_prompt` | Text | `""` | Optional custom system prompt for the LLM |
| `llm_provider` | Text | `"api"` | LLM provider: 'api' (upstream LLM element), 'openai', or 'anthropic' |
| `api_key` | Text | `""` | API key for external LLM providers (required if not using 'api') |
| `temperature` | Number | `0.1` | Controls randomness (0.0-1.0). Lower = more deterministic |
| `min_confidence` | Number | `0.5` | Minimum confidence threshold (0.0-1.0) |

### Input

- **in1**: Accepts Frame input with text in `frame.other_data["message"]` or `frame.other_data["api"]`

### Output

- **out1**: Outputs Frame with classification results in `frame.other_data`:
  - `classification`: The classified category name
  - `confidence`: Confidence score (0.0-1.0)
  - `all_categories`: List of all available categories
  - `raw_classification_response`: Raw LLM response
  - `below_threshold`: Boolean indicating if confidence was below threshold

## Usage Examples

### Example 1: Sentiment Analysis

**Settings:**
- Categories: `positive, negative, neutral`
- LLM Provider: `api` (using upstream LLM element)
- Temperature: `0.1`

**Input Text:** "I love this product! It works perfectly."

**Output:**
```json
{
  "classification": "positive",
  "confidence": 0.95,
  "all_categories": ["positive", "negative", "neutral"]
}
```

### Example 2: Priority Classification

**Settings:**
- Categories: `urgent, high, normal, low`
- System Prompt: `"You are a priority classification assistant. Classify support tickets by urgency."`
- LLM Provider: `openai`
- Min Confidence: `0.7`

**Input Text:** "The server is down and customers cannot access the service."

**Output:**
```json
{
  "classification": "urgent",
  "confidence": 0.92,
  "all_categories": ["urgent", "high", "normal", "low"]
}
```

### Example 3: Content Moderation

**Settings:**
- Categories: `safe, inappropriate, spam, harmful`
- Temperature: `0.0` (more deterministic)
- Min Confidence: `0.8`

**Input Text:** "This is a legitimate product review."

**Output:**
```json
{
  "classification": "safe",
  "confidence": 0.95,
  "all_categories": ["safe", "inappropriate", "spam", "harmful"]
}
```

### Example 4: Intent Detection

**Settings:**
- Categories: `question, complaint, compliment, request, other`
- System Prompt: `"Classify user messages by their intent."`

**Input Text:** "How do I reset my password?"

**Output:**
```json
{
  "classification": "question",
  "confidence": 0.88,
  "all_categories": ["question", "complaint", "compliment", "request", "other"]
}
```

## Workflow Integration

### Using with LLM Element (API Provider)

1. Connect **LLM Element** → **Classifier Element**
2. Set classifier `llm_provider` to `"api"`
3. LLM element processes the text and classifier extracts classification from response

### Using with External APIs

1. Set `llm_provider` to `"openai"` or `"anthropic"`
2. Provide API key in `api_key` setting
3. Classifier will call the external API directly

### Using with Routing Element

1. Connect **Classifier** → **Routing Element**
2. Use classification result in routing function:
   ```python
   classification = frame.other_data.get("classification", "")
   if classification == "urgent":
       return "route1"
   else:
       return "route2"
   ```

## Best Practices

1. **Category Names**: Use clear, distinct category names. Avoid overlapping categories.

2. **Temperature Settings**:
   - Use low temperature (0.0-0.3) for consistent, deterministic classifications
   - Use higher temperature (0.7-1.0) if you want more varied interpretations

3. **Confidence Thresholds**: Set appropriate `min_confidence` based on your use case:
   - High-stakes decisions: 0.8+
   - General classification: 0.5-0.7
   - Exploratory analysis: 0.3-0.5

4. **System Prompts**: Provide clear, specific system prompts for better results:
   - Define what each category means
   - Provide examples if helpful
   - Specify the format you want (JSON)

5. **Category Count**: Keep the number of categories reasonable (3-10) for best accuracy.

## Troubleshooting

**Low Confidence Scores:**
- Check if categories are too similar or overlapping
- Increase temperature slightly for more varied responses
- Improve system prompt with clearer category definitions

**Incorrect Classifications:**
- Review and refine category names
- Add more context in system prompt
- Adjust temperature settings

**API Errors:**
- Verify API key is correct (for external providers)
- Check network connectivity
- Ensure API provider is set correctly

**Empty Responses:**
- Verify text is present in `frame.other_data["message"]` or `frame.other_data["api"]`
- Check LLM element is connected (for API provider)
- Review logs for specific error messages

## Notes

- The element extracts text from `frame.other_data["message"]` or `frame.other_data["api"]`
- For API provider, ensure an LLM element is connected upstream
- Classification results are added to `frame.other_data` without removing original data
- The element handles multimodal API messages by extracting text content
- Confidence scores are normalized to 0.0-1.0 range
