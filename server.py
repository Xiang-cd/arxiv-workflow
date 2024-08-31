from fastapi import FastAPI
from main import auto_fetch_workflow, make_bibtex, refresh_bib


app = FastAPI()


@app.get("/autofetch")
def process_qeury(q:str):
    return auto_fetch_workflow(q)


@app.get("/bibtex")
def get_bibtex_api(refresh:bool=False, all=False):
    if refresh:
        return refresh_bib(all=all)
    else:
        return make_bibtex()