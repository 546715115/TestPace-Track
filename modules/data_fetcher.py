import requests
import os
from datetime import datetime

class DataFetcher:
    def __init__(self, config: dict = None):
        self.config = config or {}
        self.session = requests.Session()

    def construct_download_url(self, bucket_id: str, doc_id: str) -> str:
        return f"https://onebox.huawei.com/perfect/share/getDocOnlineDownloadUrl/{bucket_id}/{doc_id}"

    def get_download_link(self, bucket_id: str, doc_id: str) -> str:
        """Call API to get actual download URL"""
        url = self.construct_download_url(bucket_id, doc_id)
        try:
            response = self.session.get(url)
            data = response.json()
            return data.get('data')
        except Exception as e:
            print(f"Error getting download link: {e}")
            return None

    def download_excel(self, bucket_id: str, doc_id: str, save_path: str) -> bool:
        """Download Excel file to save_path"""
        download_url = self.get_download_link(bucket_id, doc_id)
        if not download_url:
            return False

        try:
            response = self.session.get(download_url, stream=True)
            if response.status_code == 200:
                with open(save_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
                return True
            return False
        except Exception as e:
            print(f"Error downloading Excel: {e}")
            return False

    def save_to_cache(self, bucket_id: str, doc_id: str, version_name: str, cache_dir: str) -> str:
        """Download and save to cache with version-based naming"""
        os.makedirs(cache_dir, exist_ok=True)

        # Format: {version_name}_{date}.xlsx
        date_str = datetime.now().strftime('%Y%m%d')
        filename = f"{version_name}_{date_str}.xlsx"
        save_path = os.path.join(cache_dir, filename)

        if self.download_excel(bucket_id, doc_id, save_path):
            return save_path
        return None