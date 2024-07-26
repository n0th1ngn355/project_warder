from fastapi import FastAPI
from transformers import pipeline
from pydantic import BaseModel
import torch
from gigachat import GigaChat
import os
from dotenv import load_dotenv

load_dotenv()
AUTH_DATA_GIGACHAT = os.getenv('AUTH_DATA_GIGACHAT')

app = FastAPI()


class Dialog(BaseModel):
    dialog: str

class Summaries(BaseModel):
    summaries: str


preprompt = """Необходимо создать отчёт по проекту, используя данные из нижеперечисленных текстов. В отчёте нужно указать участников проекта, планы по проекту(если они есть). Если нужной информации нет, то не придумывай что-то новое. Вот тексты:
"""


device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
print("Запущено на:", device)
summarizer = pipeline("summarization", model='d0rj/rut5-base-summ', device=device, max_length=10000)


@app.post("/summarize")
def summarize(dialog: Dialog):
    summary = summarizer(dialog.dialog)
    return {"summary": summary[0]['summary_text']}

@app.post("/report")
def report(summaries: Summaries):
    prompt = preprompt+"\n"+summaries.summaries
    print(prompt)
    with GigaChat(credentials=AUTH_DATA_GIGACHAT+"==", verify_ssl_certs=False) as giga:
        response = giga.chat(prompt)        
    return {"report":response.choices[0].message.content}
