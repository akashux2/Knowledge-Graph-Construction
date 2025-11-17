# openrouter_client.py

from openai import OpenAI

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key="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",   # 🔥 replace with your API key
)

def extract_knowledge(text):
    completion = client.chat.completions.create(
        model="qwen/qwen2.5-vl-72b-instruct:free",
        messages=[
            {
                "role": "user",
                "content": f"""
Extract entities and relations from the following text:

\"{text}\"

Reply ONLY in this JSON format:
{{
  "entities": ["Entity1", "Entity2", ...],
  "relations": [["Entity1", "Relation", "Entity2"], ...]
}}
                """
            }
        ]
    )

    response_text = completion.choices[0].message.content
    return response_text
