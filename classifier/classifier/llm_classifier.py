"""
LLM-based text classifier module.

Provides functionality to classify text using Large Language Models
with user-defined categories and labels.
"""

import json
import re
from typing import Any, Dict, List, Optional, Tuple


def extract_classification_from_response(response: str, categories: List[str]) -> Tuple[str, float]:
    """
    Extract classification result from LLM response.

    Args:
        response: The LLM response text
        categories: List of valid category names

    Returns:
        Tuple of (category_name, confidence_score)
    """
    response_lower = response.lower().strip()

    # Try to find JSON format: {"category": "...", "confidence": 0.95}
    json_match = re.search(r"\{[^}]+\}", response)
    if json_match:
        try:
            data = json.loads(json_match.group())
            category = data.get("category", "").strip()
            confidence = float(data.get("confidence", 0.5))
            if category.lower() in [c.lower() for c in categories]:
                return category, max(0.0, min(1.0, confidence))
        except (json.JSONDecodeError, ValueError, KeyError):
            pass

    # Try to find category name directly in response
    for category in categories:
        if category.lower() in response_lower:
            # Try to extract confidence score
            confidence_match = re.search(r"(\d+\.?\d*)", response_lower)
            confidence = float(confidence_match.group(1)) / 100.0 if confidence_match else 0.8
            if confidence > 1.0:
                confidence = confidence / 100.0
            return category, max(0.0, min(1.0, confidence))

    # Try to find "Category: X" or "Class: X" pattern
    pattern_match = re.search(
        r"(?:category|class|label|classification)[\s:]+([a-zA-Z0-9\s]+)",
        response_lower,
    )
    if pattern_match:
        found_category = pattern_match.group(1).strip()
        for category in categories:
            if category.lower() == found_category.lower():
                return category, 0.8

    # Default: return first category with low confidence
    if categories:
        return categories[0], 0.5

    return "unknown", 0.0


def create_classification_prompt(
    text: str, categories: List[str], system_prompt: Optional[str] = None
) -> str:
    """
    Create a prompt for LLM-based classification.

    Args:
        text: The text to classify
        categories: List of category names
        system_prompt: Optional custom system prompt

    Returns:
        Formatted prompt string
    """
    if system_prompt:
        base_prompt = system_prompt
    else:
        base_prompt = (
            "You are a text classification assistant. "
            "Classify the given text into one of the provided categories. "
            "Respond with a JSON object containing 'category' and 'confidence' fields."
        )

    categories_str = ", ".join([f'"{cat}"' for cat in categories])

    prompt = f"""{base_prompt}

Categories: [{categories_str}]

Text to classify:
{text}

Respond with a JSON object in this format:
{{"category": "category_name", "confidence": 0.95}}

Classification:"""

    return prompt


def parse_classification_result(response: str, categories: List[str]) -> Dict[str, Any]:
    """
    Parse LLM response into classification result.

    Args:
        response: LLM response text
        categories: List of valid categories

    Returns:
        Dictionary with 'category', 'confidence', and 'raw_response'
    """
    category, confidence = extract_classification_from_response(response, categories)

    return {
        "category": category,
        "confidence": confidence,
        "raw_response": response,
        "all_categories": categories,
    }
