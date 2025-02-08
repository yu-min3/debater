import os

from firecrawl import FirecrawlApp
from tavily import TavilyClient


class TavilyCrawlRepository:
    def __init__(self):
        self.tavily_client = TavilyClient(api_key=os.environ["TAVILY_API_KEY"])

    def extract(self, urls: list[str]) -> list[tuple[str, str, dict]]:
        response = self.tavily_client.extract(urls=urls)

        results = []
        for res in response["results"]:
            url = res["url"]
            text = res["raw_content"]
            results.append((url, text, res))
        return results


class FireCrawlRepository:
    def __init__(self):
        self.app = FirecrawlApp()

    def extract(self, urls: list[str]) -> list[tuple[str, str, dict]]:
        results = []
        for url in urls:
            try:
                result = self.app.crawl_url(
                    url,
                    params={"limit": 5, "scrapeOptions": {"formats": ["markdown"]}},
                    poll_interval=5,
                )

                full_text = result["data"][0]["markdown"]
                results.append((url, full_text, result))

            except Exception as e:
                print(f"Error: {e}")
                continue

        return results
