"""
given title or arxiv id, search the paper using arxiv api,

"""

import os, re, logging
import arxiv
import gradio as gr
import requests
import rich.pretty
logging.basicConfig(level=logging.INFO)

rich.pretty.install()

client = arxiv.Client()

def search(text):
    """given title or arxiv id, search the paper using arxiv api,

    Args:
        text(str): the query

    Returns:
        reults type or None   
    """
    logging.info(f"searching for {text}")
    if re.match(r".+?(abs|pdf|html)\/\d+.\w+", text):
        # case of url, abs/arxiv_id or pdf/arxiv_id
        arxiv_id = re.search(r"\d+.\w+", text).group()
        search_by_id = arxiv.Search(id_list=[arxiv_id])
        results = client.results(search_by_id)
    else:
        search = arxiv.Search(
            query = text,
            max_results = 1,
            sort_by = arxiv.SortCriterion.Relevance
        )
        results = client.results(search)
    
    try:
        result = next(results)
    except:
        return None
    return result



def push_to_notion(result):
    """push the result to notion

    Args:
        result (arxiv.Result): the result from arxiv api
    """
    NOTION_TOKEN = os.environ.get("NOTION_TOKEN", None)
    NOTION_DATABASE_ID = os.environ.get("NOTION_DATABASE_ID", None)
    assert NOTION_TOKEN, "NOTION_TOKEN not found"
    assert NOTION_DATABASE_ID, "NOTION_DATABASE_ID not found"
    
    url = f'https://api.notion.com/v1/databases/{NOTION_DATABASE_ID}/query'
    headers = {
        'Authorization': f'Bearer {NOTION_TOKEN}',
        'Content-Type': 'application/json',
        'Notion-Version': '2022-06-28'
    }
    
    # 空的 JSON 数据，根据需要可以修改为实际的查询参数
    data = {}
    response = requests.post(url, headers=headers, json=data)
    
    
    
 
with gr.Blocks() as demo:
    string = gr.Text()
    string.submit(
        fn=search,
        inputs=string,
        outputs=[]
    )
    
demo.queue().launch()