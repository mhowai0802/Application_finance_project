import requests
import config


def generate_ai_response(prompt, context=None, template_name='financial_analysis'):
    """
    Generate a response from the Llama model via Ollama.

    Args:
        prompt (str): The user's query
        context (str, optional): Additional context information
        template_name (str): The prompt template to use

    Returns:
        str: The AI-generated response
    """
    concise_instruction = "Answer concisely and concretely. Do not provide unnecessary detail."

    # Get the appropriate prompt template
    template = config.AI_PROMPT_TEMPLATES.get(template_name, '{prompt}')

    # Prepare the full prompt with context if provided
    if context:
        full_prompt = template.format(context=context, prompt=prompt)
    else:
        full_prompt = prompt

    # Insert the concise instruction
    full_prompt = f"{concise_instruction}\n{full_prompt}"

    # Prepare the request to Ollama
    payload = {
        "model": config.OLLAMA_MODEL,
        "prompt": full_prompt,
        "stream": False,
        "temperature": config.AI_TEMPERATURE,
        "max_tokens": config.AI_MAX_TOKENS
    }

    try:
        response = requests.post(config.OLLAMA_API_URL, json=payload)
        if response.status_code == 200:
            result = response.json()
            return result.get('response', 'No response generated')
        else:
            return f"Error: Received status code {response.status_code} from Ollama"
    except Exception as e:
        return f"Error connecting to Ollama: {str(e)}"