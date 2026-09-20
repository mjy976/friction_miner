from friction_miner.llm.client import get_llm_client

client, model_name = get_llm_client()
print(f"Using model: {model_name}\n")

response = client.chat.completions.create(
    model=model_name,
    messages=[
        {"role": "user", "content": "Reply with exactly one word: pong"}
    ],
    max_tokens=20,
    extra_body={"thinking": {"type": "disabled"}},
)

choice = response.choices[0]
print(f"finish_reason: {choice.finish_reason}")
print(f"content: {choice.message.content!r}")
print(f"reasoning_content: {getattr(choice.message, 'reasoning_content', None)!r}")
print(f"usage: {response.usage}")