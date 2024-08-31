"""
given title or arxiv id, search the paper using arxiv api,

"""

import os, re, logging
import arxiv
import requests
import rich.pretty
import json
import time
rich.pretty.install()
# formate with time, file:line number, message
logging.basicConfig(level=logging.INFO, filename="fetch.log", filemode="a", format="%(asctime)s - %(filename)s[line:%(lineno)d] - %(levelname)s: %(message)s")


def auto_fetch_workflow(text):
    result = search(text)
    if result:
        dirpath = os.environ.get("DOWNLOAD_DIR", "./papers")
        os.makedirs(dirpath, exist_ok=True)
        filename = result.entry_id.split("/")[-1] + ".pdf"
        if not os.path.exists(os.path.join(dirpath, filename)):
            result.download_pdf(dirpath=dirpath, filename=filename)
            download_log = f"downloaded {filename}"
        else:
            download_log = f"file {filename} already exists"
        logging.info(download_log)
        notion_log = push_to_notion(result)
        return "====".join([download_log, notion_log])
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


class IterNotionDatabase:
    def __init__(self, NOTION_TOKEN=None, NOTION_DATABASE_ID=None):
        self.NOTION_TOKEN = (
            NOTION_TOKEN if NOTION_TOKEN else os.environ.get("NOTION_TOKEN", None)
        )
        self.NOTION_DATABASE_ID = (
            NOTION_DATABASE_ID
            if NOTION_DATABASE_ID
            else os.environ.get("NOTION_DATABASE_ID", None)
        )
        assert self.NOTION_TOKEN is not None, "NOTION_TOKEN not found"
        assert self.NOTION_DATABASE_ID is not None, "NOTION_DATABASE_ID not found"
        self.query_url = (
            f"https://api.notion.com/v1/databases/{self.NOTION_DATABASE_ID}/query"
        )
        self.headers = {
            "Authorization": f"Bearer {self.NOTION_TOKEN}",
            "Content-Type": "application/json",
            "Notion-Version": "2022-06-28",
        }
        self.current_batch = None
        self.current_batch_index = 0
        self.current_response = None
        self.query()

    def query(self):
        if self.current_response is not None:
            if self.current_response.get("next_cursor", False):
                response = requests.post(
                    self.query_url,
                    headers=self.headers,
                    data=json.dumps(
                        {"start_cursor": self.current_response["next_cursor"]}
                    ),
                ).json()
                self.current_response = response
                self.current_batch = response["results"]
                self.current_batch_index = 0
            else:
                raise StopIteration
        else:
            response = requests.post(
                self.query_url, headers=self.headers, data=json.dumps({})
            ).json()
            self.current_response = response
            self.current_batch = response["results"]

    def __next__(self):
        if self.current_batch_index < len(self.current_batch):
            item = self.current_batch[self.current_batch_index]
            self.current_batch_index += 1
            return item
        else:
            self.query()
            return self.__next__()

    def __iter__(self):
        return self
    


refresh_thread = None

def refresh_bib_thread(all=False):
    for res in IterNotionDatabase():
        if not all and res['properties']["bib"]["rich_text"]:
            continue
        title = res['properties']["Name"]["title"][0]["plain_text"]
        semantic_search = semantic_scholar_search(title, sleep=30)
        if semantic_search:
            bib_str = semantic_search['citationStyles']['bibtex']
            item_data = {"bib": {"type": "rich_text", "rich_text": [{"type": "text", "text": {"content": bib_str}}]},}
            update_url = f"https://api.notion.com/v1/pages/{res['id']}"
            response = requests.patch(update_url, headers=IterNotionDatabase().headers, data=json.dumps({"properties": item_data}))
            if response.status_code == 200:
                logging.info(f"updated bib for {title} successfully")
            else:
                logging.error(f"update bib for {title} failed, {response.text}")


def refresh_bib(all=False):
    """create a new thread to refresh the bib for all items in notion database

    Args:
        all (bool, optional): if refresh all items in database. Defaults to False.
    """
    global refresh_thread
    import threading
    if refresh_thread and refresh_thread.is_alive():
        return "refresh thread already exists"
    else:
        refresh_thread = threading.Thread(target=refresh_bib_thread, args=(all,))
        refresh_thread.start()
        return "refresh thread started"


def make_bibtex():
    """makeing a bibtex string from notion database, return the bib string to webview
        return: the bibtex string
    """
    bib_ls = []
    for res in IterNotionDatabase():
        bib_item = res['properties']["bib"]["rich_text"]
        if bib_item:
            bib_ls.append(rich_text2str(bib_item))
    return "\n\n\n".join(bib_ls)

def rich_text2str(rich_text):
    plain_text_ls = []
    for item in rich_text:
        if item["type"] == "text":
            plain_text_ls.append(item['plain_text'])
    return "".join(plain_text_ls)


def semantic_scholar_title_search(text, sleep=10, max_retry=3):
    query_url = "https://api.semanticscholar.org/graph/v1/paper/search/match?query={query}"
    try:
        response = requests.get(query_url.format(query=text)).json()
        if response.get('data', False) and response['data']:
            logging.info(f"SS search title found for {text}, paper id is {response['data'][0]['paperId']}")
            return response['data'][0]["paperId"]
        elif response.get('error', False):
            logging.error(f"SS search title error: {response['error']} for {text}")
            return None
        elif response.get("message", False):
            logging.warning(f"SS search title error: {response['message']} for {text}")
            if "Too Many Requests" in response['message']:
                time.sleep(sleep)
                return semantic_scholar_title_search(text, sleep, max_retry-1) if max_retry > 0 else None
        else:
            return None
    except Exception as e:
        logging.error(f"SS search title error: {e} for {text}")
        return None

def semantic_scholar_get_paper(paperId, sleep=10, max_retry=3):
    try:
        detail_query = f'https://api.semanticscholar.org/graph/v1/paper/{paperId}?fields=citationStyles'
        detail_response = requests.get(detail_query).json()
        if detail_response.get('citationStyles', False):
            logging.info(f"SS citation found for {paperId}")
            return detail_response
        elif detail_response.get('message', False):
            logging.warning(f"SS error: {detail_response['message']} for {paperId}")
            if "Too Many Requests" in detail_response['message']:
                time.sleep(sleep)
                return semantic_scholar_search(paperId, sleep, max_retry-1) if max_retry > 0 else None
        else:
            logging.error(f"SS error: {detail_response} for {paperId}")
            return None
    except Exception as e:
        logging.error(f"semantic_scholar error: {e} for {paperId}")
        return None
        

def semantic_scholar_search(text, sleep=10, max_retry=3):
    """api doc
    https://api.semanticscholar.org/api-docs/graph#tag/Paper-Data/operation/get_graph_get_paper
    search title first to get paperId, then get the citationStyles
    """
    logging.info(f"semantic_scholar searching for {text}")
    paperId = semantic_scholar_title_search(text, sleep, max_retry)
    return semantic_scholar_get_paper(paperId, sleep, max_retry) if paperId else None



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

    # query if database already have items
    query = {
        "filter": {
            "property": "URL",
            "url": {"equals": result.entry_id},
        }
    }
    response = requests.post(query_url, headers=headers, data=json.dumps(query)).json()
    if len(response["results"]) > 0:
        notion_log = "already exists in notion"
        logging.info(notion_log)
        return notion_log

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
        notion_log = "pushed to notion successfully"
        logging.info(notion_log)
    else:
        notion_log = f"pushed to notion failed, {response.text}"
        logging.error(notion_log)
    return notion_log
