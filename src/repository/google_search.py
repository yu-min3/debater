import os

from googleapiclient.discovery import build


class GoogleSearchRepository:
    def __init__(self):
        self.my_cse_id = os.environ.get("GOOGLE_SEARCH_ENGINE_ID")
        my_api_key = os.environ.get("GCP_API_KEY")
        self.service = build("customsearch", "v1", developerKey=my_api_key)

    def search(self, query: str, num: int = 10):
        try:
            items = []
            # ページネーション処理
            for start_index in range(
                1, num + 1, 10
            ):  # 1からnum_results_totalまで10刻みで繰り返す
                num_results_per_request = min(
                    10, num - (start_index - 1)
                )  # 各リクエストで取得する数

                res = (
                    self.service.cse()
                    .list(
                        q=query,
                        cx=self.my_cse_id,
                        num=num_results_per_request,
                        start=start_index,
                    )
                    .execute()
                )

                if res.get("items"):
                    items.extend(res["items"])  # 取得した結果をリストに追加
                else:
                    print(f"{start_index}以降の検索結果は見つかりませんでした。")
                    break  # 以降の結果がないためループを抜ける

        except Exception as e:
            print(f"エラーが発生しました: {e}")
            raise e

        else:
            return items

    def filter_text_items(self, items: dict):
        filtered_items = []
        for item in items:
            if "mime" not in item:
                filtered_items.append(item)
                continue
            if "text" in item["mime"] or "pdf" in item["mime"]:
                filtered_items.append(item)

        return filtered_items


# TODO: 生成AIでフィルタする
