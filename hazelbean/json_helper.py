import json

class JsonSyntaxHelperError(Exception):
    def __init__(self, message, original_exception):
        super().__init__(message)
        self.original_exception = original_exception
        # Store details for potential later use
        self.msg = original_exception.msg
        self.doc = original_exception.doc
        self.pos = original_exception.pos
        self.lineno = original_exception.lineno
        self.colno = original_exception.colno

def parse_json_with_detailed_error(json_string):
    try:
        return json.loads(json_string)
    except json.JSONDecodeError as e:
        # --- Build the enhanced message ---
        lines = json_string.splitlines()
        error_line = lines[e.lineno - 1] if e.lineno <= len(lines) else ""
        pointer = " " * (e.colno - 1) + "^"

        # --- Heuristics for better explanation ---
        suggestion = ""
        char_at_error = json_string[e.pos] if e.pos < len(json_string) else None
        char_before_error = json_string[e.pos - 1] if e.pos > 0 else None

        if e.msg == "Expecting value":
            if char_at_error and char_at_error.isalpha():
                suggestion = "Did you forget double quotes around a string value?"
            elif char_before_error == ':':
                 suggestion = "Expecting a JSON value (string, number, object, array, true, false, null) after the colon."
            elif char_before_error == '[' or char_before_error == ',':
                 suggestion = "Expecting a JSON value (string, number, object, array, true, false, null) within an array."
        elif "Expecting property name enclosed in double quotes" in e.msg:
            suggestion = "Object keys (property names) must be enclosed in double quotes."
        elif "Expecting ',' delimiter" in e.msg:
            suggestion = "Did you forget a comma between elements or key-value pairs?"
        elif "Unterminated string starting at" in e.msg:
             suggestion = "Check if a string is missing its closing double quote."
        elif "Invalid control character" in e.msg:
            suggestion = "Check for unescaped control characters (like newlines) inside strings."
        elif "Extra data" in e.msg:
            suggestion = "There might be extra characters after the main JSON structure is closed."
        elif "Expecting ':'" in e.msg:
             suggestion = "Missing a colon ':' between a key and its value in an object."
        elif "Expecting '}'" in e.msg:
            suggestion = "Check for an unclosed object ('{'). Missing a closing '}'?"
        elif "Expecting ']'" in e.msg:
            suggestion = "Check for an unclosed array ('['). Missing a closing ']'?"

        # --- Format the final message ---
        enhanced_message = (
            f"JSON Parsing Error: {e.msg}\n"
            f"Location: Line {e.lineno}, Column {e.colno} (Character {e.pos})\n"
            f"Context:\n"
            f"  {error_line}\n"
            f"  {pointer}\n"
        )
        if suggestion:
            enhanced_message += f"Suggestion: {suggestion}\n"
        enhanced_message += f"Original String (check around char {e.pos}):\n{e.doc[:e.pos]} <--- ERROR ---> {e.doc[e.pos:]}"


        raise JsonSyntaxHelperError(enhanced_message, e) # from e # Optionally chain

# # --- Test Cases ---
# test_cases = [
#     '{"aggregation":"v11_s26_r50","counterfactual":bau_ignore_es"]}', # Missing quote around value
#     '{"key": "value" "key2": "value2"}', # Missing comma
#     "{'key': 'value'}", # Single quotes
#     '{"key": "value",}', # Trailing comma (allowed by some parsers, not standard JSON)
#     '{"key": value_no_quotes}', # Missing quotes around value
#     '{"key": "unterminated string', # Unterminated string
#     '{"key": "value"]', # Mismatched bracket
#     '{"key" "value"}', # Missing colon
#     '["item1", "item2"', # Missing closing bracket
#     '{"key": "value"} extra stuff' # Extra data
# ]

# for i, test_str in enumerate(test_cases):
#     print(f"\n--- Testing Case {i+1} ---")
#     print(f"Input: {test_str}")
#     try:
#         parse_json_with_detailed_error(test_str)
#         print("Result: Parsed Successfully (This shouldn't happen for these tests)")
#     except JsonSyntaxHelperError as e:
#         print(f"Caught Enhanced Error:\n{e}")
#     except Exception as e:
#          print(f"Caught Unexpected Error: {type(e).__name__}: {e}")