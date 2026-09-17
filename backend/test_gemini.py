from google import genai
from app.core.config import get_settings

settings = get_settings()

if not settings.gemini_api_key:
    raise RuntimeError("GEMINI_API_KEY is missing")

client = genai.Client(
    api_key=settings.gemini_api_key
)

response = client.models.generate_content(
    model=settings.llm_model,
    contents="Explain P/E ratio in one simple sentence."
)

print(response.text)