import json

from google.cloud import firestore

from src.model.article import Article


class LocalArticleRepository:
    DATABASE_PATH = "articles/database.json"

    def load(self) -> dict:
        with open(self.DATABASE_PATH, encoding="utf-8") as f:
            data = json.load(f)
        return data

    def get_urls(self) -> list[str]:
        data = self.load()
        return list(data.keys())

    def save(self, url: str, data: dict):
        # JSONファイルを読み込む
        with open(self.DATABASE_PATH, encoding="utf-8") as f:
            database = json.load(f)
        database[url] = data
        with open(self.DATABASE_PATH, "w", encoding="utf-8") as f:
            json.dump(database, f, ensure_ascii=False, indent=4)


class FireStoreArticleRepository:
    def __init__(self):
        self.db = firestore.Client()
        self.article_collection = self.db.collection("article")

    def load(self, url: str) -> Article:
        key = self._translate_url_for_key(url)
        if not self.check_url_exists(key):
            raise ValueError(f"URL not found: {url}")
        article_content = self.article_collection.document(key).get().to_dict()

        return Article(**article_content)

    def save(self, url: str, article: Article) -> None:
        key = self._translate_url_for_key(url)
        data = article.model_dump()
        self.article_collection.document(key).set(data)

    def check_url_exists(self, url: str) -> bool:
        """既にURLが存在いればTrueを返す."""
        key = self._translate_url_for_key(url)
        return self.article_collection.document(key).get().exists

    def _translate_url_for_key(self, url: str) -> str:
        return url.replace("/", "_")
