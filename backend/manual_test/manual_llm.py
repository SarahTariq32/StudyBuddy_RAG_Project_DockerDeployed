from app.llm.factory import get_llm_client

llm = get_llm_client()
response = llm.generate("Say hello in one sentence.")
print(response)
