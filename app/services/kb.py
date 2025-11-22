import json
from rank_bm25 import BM25Okapi
from app.schemas import KBEntry

class KnowledgeBaseService:
    def __init__(self, file_path: str):
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        self.entries = [KBEntry(**e) for e in data]

        self.corpus = [
            (f"{e.title} {e.category} {' '.join(e.symptoms)}").lower().split()
            for e in self.entries
        ]

        self.bm25 = BM25Okapi(self.corpus)

    def search(self, query: str, top_k: int = 3):
        tokens = query.lower().split()
        return self.bm25.get_top_n(tokens, self.entries, n=top_k)
