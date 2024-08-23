from fastapi import FastAPI
from main import auto_fetch_workflow


app = FastAPI()


@app.get("/autofetch")
def process_qeury(q:str):
    return auto_fetch_workflow(q)
