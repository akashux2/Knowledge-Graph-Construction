# test_extract.py

from openrouter_client import extract_knowledge
import json

if __name__ == "__main__":
    text = "Elon Musk founded SpaceX and is the CEO of Tesla."
    result = extract_knowledge(text)
    print("\nRaw Result from AI:\n", result)

    try:
        parsed_result = json.loads(result)
        print("\nParsed JSON:\n", json.dumps(parsed_result, indent=2))
    except json.JSONDecodeError:
        print("\n⚠️ Couldn't parse JSON! Check model output formatting.")
