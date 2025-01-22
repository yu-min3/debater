from langchain_google_genai import GoogleGenerativeAI

MODEL_NAME = "gemini-2.0-flash-exp"
gemini_model = GoogleGenerativeAI(model=MODEL_NAME)
