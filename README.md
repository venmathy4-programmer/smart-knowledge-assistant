# Smart Personal Knowledge Management Assistant

This project is a simple local knowledge base built with Python and Streamlit. It lets you:

- save handwritten notes
- upload TXT, PDF, and DOCX files
- search notes by keyword
- ask questions about stored knowledge
- create automatic summaries
- find related notes
- get suggested tags
- view a dashboard
- export and restore backups

## Project structure

- `app.py` — main Streamlit app
- `src/database.py` — SQLite database handling
- `src/knowledge.py` — parsing, search, summarization, tag suggestions, and question answering
- `data/` — database and uploaded files
- `backups/` — JSON backup exports
- `requirements.txt` — Python dependencies

## Run on Windows

Open PowerShell in the project folder and run:

```powershell
cd "C:\Users\venmathy\OneDrive\Desktop\smart-knowledge-assistant"
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
streamlit run app.py
```

Then open the URL shown in the terminal, usually:

http://localhost:8501

## Basic usage

1. Add a note manually in the sidebar.
2. Upload a PDF, DOCX, or TXT document.
3. Search the knowledge base in the main area.
4. Ask a question in the question box.
5. Use the dashboard to see note counts and tag activity.
6. Click the backup button to export a JSON backup.

## Notes

This project is designed to work locally and does not require an external API key.

It uses lightweight local algorithms for search, summarization, and Q&A.
