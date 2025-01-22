import json
from datetime import datetime

from google.cloud import storage


class ArticleRawDataRepository:
    HEADER = "raw_data"

    def save(self, crawl_result) -> str:
        save_file_path = f"{self.HEADER}/{datetime.now().strftime('%Y%m%d%H%M%S')}.json"

        with open(save_file_path, "w", encoding="utf-8") as f:
            json.dump(crawl_result, f, ensure_ascii=False, indent=4)

        return save_file_path


class CloudStorageArticleRawRepository:
    ARTICLE_RAW_DATA_BUCKET = "raw-article-data"

    def __init__(self):
        self.bucket = storage.Client().bucket(self.ARTICLE_RAW_DATA_BUCKET)

    def save_dict_to_json(self, dict_data: dict, file_name: str) -> None:
        try:
            json_byte = json.dumps(dict_data, ensure_ascii=False).encode("utf-8")
            blob = self.bucket.blob(file_name)
            blob.upload_from_string(json_byte, content_type="application/json")
        except Exception as e:
            raise e

    def load_json_to_dict(self, file_name: str) -> dict:
        blob = self.bucket.blob(file_name)
        json_data = json.loads(blob.download_as_bytes())

        return json_data
