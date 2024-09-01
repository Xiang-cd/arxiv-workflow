from fastapi import FastAPI
from main import auto_fetch_workflow, make_bibtex, refresh_bib
import logging
from fastapi.responses import HTMLResponse, PlainTextResponse
logging.basicConfig(level=logging.INFO, filename="fetch.log", filemode="a", format="%(asctime)s - %(filename)s[line:%(lineno)d] - %(levelname)s: %(message)s")


app = FastAPI()


@app.get("/autofetch", response_class=PlainTextResponse)
def process_qeury(q:str):
    return auto_fetch_workflow(q)


@app.get("/bibtex", response_class=PlainTextResponse)
def get_bibtex_api(refresh:bool=False, all=False):
    if refresh:
        return refresh_bib(all=all)
    else:
        return make_bibtex()