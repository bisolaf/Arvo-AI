import os
from openai import OpenAI
import json

def parse_deployment_request(nl_input: str):
    prompt = f"""
    Extract the following information from this deployment request:
    - Cloud provider (AWS, GCP, Azure)
    - Application framework/language (Flask, Django, Node.js, etc.)
    - Deployment type preference (VM, Serverless, Kubernetes)
    - Any resource preferences (CPU, RAM)

    Request: "{nl_input}"
    Return as JSON.
    """

    response = client.chat.completions.create(
        model="gpt-4o-mini",  
        messages=[{"role": "user", "content": prompt}],
        temperature=0,
    )

    try:
        content = response.choices[0].message.content
        result = json.loads(content)
        return result
    except Exception as e:
        print("Error parsing response:", e)
        return {}
