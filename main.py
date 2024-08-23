"""
given title or arxiv id, search the paper using arxiv api,

"""

import os, re, logging
import arxiv
import gradio as gr
import requests
import rich.pretty
import json

logging.basicConfig(level=logging.INFO)

rich.pretty.install()


def auto_fetch_workflow(text):
    result = search(text)
    if result:
        dirpath = os.environ.get("DOWNLOAD_DIR", "./papers")
        filename = result.entry_id.split("/")[-1] + ".pdf"
        if not os.path.exists(os.path.join(dirpath, filename)):
            result.download_pdf(dirpath=dirpath, filename=filename)
            logging.info(f"downloaded {filename}")
        else:
            logging.info(f"file {filename} already exists")
        push_to_notion(result)
        return f"found {result.title}, push to notion successfully"
    else:
        return f"not found {text}"


def search(text):
    """given title or arxiv id, search the paper using arxiv api,

    Args:
        text(str): the query

    Returns:
        reults type or None
    """
    client = arxiv.Client()
    logging.info(f"searching for {text}")
    if re.match(r".+?(abs|pdf|html)\/\d+.\w+", text):
        # case of url, abs/arxiv_id or pdf/arxiv_id
        arxiv_id = re.search(r"\d+.\w+", text).group()
        search_by_id = arxiv.Search(id_list=[arxiv_id])
        results = client.results(search_by_id)
    else:
        search = arxiv.Search(
            query=text, max_results=1, sort_by=arxiv.SortCriterion.Relevance
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

    query_url = f"https://api.notion.com/v1/databases/{NOTION_DATABASE_ID}/query"
    shema_url = f"https://api.notion.com/v1/databases/{NOTION_DATABASE_ID}"
    create_url = "https://api.notion.com/v1/pages"
    headers = {
        "Authorization": f"Bearer {NOTION_TOKEN}",
        "Content-Type": "application/json",
        "Notion-Version": "2022-06-28",
    }

    # 手动构建mapping, 即arxiv search res的相应信息对应我们需要上传数据库的哪些字段, 此时需要查询数据库的shema, 通过以下query即可
    # properties = requests.get(shema_url, headers=headers).json()["properties"]

    item_data = {
        "Date": {"type": "date", "date": {"start": str(result.updated.date())}},
        "level": {
            "type": "select",
            "select": None,
        },
        "abs": {
            "type": "rich_text",
            "rich_text": [{"type": "text", "text": {"content": result.summary}}],
        },
        "alias": {"type": "rich_text", "rich_text": []},
        "bib": {"type": "rich_text", "rich_text": []},
        "my summary": {
            "type": "rich_text",
            "rich_text": [],
        },
        "review": {"type": "url", "url": None},
        "URL": {"type": "url", "url": result.entry_id},
        "pub": {"type": "rich_text", "rich_text": []},
        "Tags": {
            "type": "multi_select",
            "multi_select": [],
        },
        "path": {
            "type": "rich_text",
            "rich_text": [
                {
                    "type": "text",
                    "text": {"content": result.entry_id.split("/")[-1] + ".pdf"},
                }
            ],
        },
        "status": {
            "type": "select",
            "select": {
                "name": "toread",
                "color": "pink",
                "description": None,
            },
        },
        "Name": {
            "type": "title",
            "title": [{"type": "text", "text": {"content": result.title}}],
        },
    }

    response = requests.post(
        create_url,
        headers=headers,
        data=json.dumps(
            {
                "parent": {"type": "database_id", "database_id": NOTION_DATABASE_ID},
                "properties": item_data,
            }
        ),
    )
    
    if response.status_code == 200:
        logging.info(f"pushed to notion successfully")
    else:
        logging.error(f"pushed to notion failed, {response.text}")


with gr.Blocks() as demo:
    string = gr.Text()
    string.submit(fn=auto_fetch_workflow, inputs=string, outputs=[])

demo.queue().launch()
