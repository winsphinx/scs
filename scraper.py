import requests
from bs4 import BeautifulSoup
import json
import time
from pathlib import Path

class ComplaintScraper:
    def __init__(self, base_url="http://xyz.net"):
        self.base_url = base_url
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        self.data_dir = Path("data")
        self.data_dir.mkdir(exist_ok=True)

    def scrape_complaints(self):
        try:
            response = requests.get(self.base_url, headers=self.headers)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, 'html.parser')
            complaints = []

            # 根据实际网站结构调整选择器
            for item in soup.select('.complaint-item'):
                complaint = {
                    'title': item.select_one('.title').text.strip(),
                    'content': item.select_one('.content').text.strip(),
                    'date': item.select_one('.date').text.strip(),
                    'category': item.select_one('.category').text.strip()
                }
                complaints.append(complaint)

            self._save_data(complaints)
            return complaints

        except Exception as e:
            print(f"Error occurred: {e}")
            return []

    def _save_data(self, data):
        output_file = self.data_dir / "raw_data.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    scraper = ComplaintScraper()
    scraper.scrape_complaints()