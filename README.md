# arxiv auto workflow

This is a UI based workflow for manage arxiv papers with notion.

## background & motivation

- arxiv becoms a popular platform for sharing scientific papers, as a AI researcher, I get papers almost from arxiv
- there is no efficient way to manage papers for files, citations, notes, and other information. `Endnote` manage citations mainly, `readpaper` dones a good job for notes, files and inplace translations, but lacks of self-defined field and efficient search.
- some paper release with arxiv, but soon will be accepted by a conference or journal, how to update the bibtex and other information if you want to cite it in your paper?
- my solution is to build a visualized database for papers via notion, define my field and tags for papers, and use `readpaper` to read them.

The problem is:
when getting an interesting title of a new paper, I may do:
 
- opening url to search
- create a new page in **notion**
- copy and paste title, abstract, and other information manually
- manually download pdf and store to local directory
  
it is very time-consuming and error-prone.

## solution

build up a ui-based workflow，drop title or arxiv id，program will automatically search arxiv and get the paper information, then create a new page in notion with the information， and also download the pdf file and store it to local directory.

when find a paper in abs/pdf url, just modify url using predefined api, then your auto workflow will be launched:
| before | after |
| --- | --- |
| ![image](assets/before.png)  | ![image](assets/after.png) |

files will be downloaded, metainfos will be uploaded to notion!

## how to use

### prepare notion database and notion token
left to be explained

### from source code
```
pip install -r requirements.txt
export NOTION_TOKEN=<your_notion_token>
export NOTION_DATABASE_ID=<your_notion_database_id>
export DOWNLOAD_DIR=<your_download_directory>
fastapi run server.py
```

### using docker
```
docker build -t arxiv-workflow .

export NOTION_TOKEN=<your_notion_token>
export NOTION_DATABASE_ID=<your_notion_database_id>
export DOWNLOAD_DIR=<your_download_directory>

docker run -it --rm -e NOTION_TOKEN=$NOTION_TOKEN \
    -e NOTION_DATABASE_ID=$NOTION_DATABASE_ID \
    -e DOWNLOAD_DIR=/download \
    -v $DOWNLOAD_DIR:/download \
    -p 8000:8000 \
    arxiv-workflow
```

## TODOs

- [ ] release my notion database template
- [ ] bibtex auto refresh
- [ ] export bibtex file for all your papers, with alias you've added
- [ ] rest API documentation and CLI tools
- [ ] if system becomes complex, add config system

