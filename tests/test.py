import vertexai
from vertexai.generative_models import GenerativeModel
import os
from dotenv import load_dotenv
load_dotenv()

PROJECT_ID = os.getenv("GOOGLE_PROJECT_ID")
GEMINI_MODEL_NAME = os.getenv("GEMINI_MODEL_NAME")

vertexai.init(
    project=PROJECT_ID,
    location="us-central1"
)

model = GenerativeModel(GEMINI_MODEL_NAME)

print(model.generate_content("Say hello").text)