import json
from typing import Type
from pydantic import BaseModel, ValidationError

def validate_json_with_model(json_string: str, model: Type[BaseModel]) -> str:
    """
    Validates a JSON string against a given Pydantic model.

    Args:
        json_string: The string content from an agent's message, expected to be JSON.
        model: The Pydantic model class to validate against (e.g., ResearchReport).

    Returns:
        A string indicating success or detailing the validation failure.
    """
    try:
        # Attempt to parse the string and validate it against the model's schema.
        # This single line is where Pydantic does its magic.
        model.model_validate_json(json_string)
        
        # If the line above doesn't raise an error, the JSON is valid.
        return f"VALIDATION_SUCCESS: The JSON is valid and conforms to the {model.__name__} schema."

    except ValidationError as e:
        # This error means the JSON was valid, but its structure or data types
        # did not match the Pydantic model's definition.
        return f"VALIDATION_FAILURE: The JSON structure is invalid. Errors:\n{e}"
        
    except json.JSONDecodeError as e:
        # This error means the string provided was not even a valid JSON.
        return f"VALIDATION_FAILURE: The message content is not a valid JSON string. Error: {e}"

    except Exception as e:
        # Catch any other unexpected errors.
        return f"VALIDATION_FAILURE: An unexpected error occurred during validation. Error: {e}"