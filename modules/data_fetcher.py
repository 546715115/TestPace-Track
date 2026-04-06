"""
数据获取模块 - 从 OneBox API 下载 Excel
"""
import requests
import os
import json
from datetime import datetime
from typing import Optional


def get_cookie_config():
    """加载Cookie配置"""
    config_path = os.path.join(os.path.dirname(__file__), '..', 'config', 'cookies.json')
    if os.path.exists(config_path):
        with open(config_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {"cookie": ""}


class DataFetcher:
    """从 OneBox API 获取 Excel 文件"""

    BASE_URL = "https://onebox.huawei.com/perfect/share/getDocOnlineDownloadUrl"

    def __init__(self):
        self.cookie = get_cookie_config().get('cookie', '')

    def construct_download_url(self, bucket_path: str, doc_id: str) -> str:
        """
        构建下载 URL
        bucket_path: /7223826/479248
        """
        bucket_path = bucket_path.lstrip('/')
        return f"{self.BASE_URL}/{bucket_path}/{doc_id}"

    def get_download_link(self, bucket_path: str, doc_id: str) -> Optional[str]:
        """调用 API 获取实际下载链接"""
        url = self.construct_download_url(bucket_path, doc_id)
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept': 'application/json'
            }
            if self.cookie:
                headers['Cookie'] = self.cookie
            response = requests.get(url, headers=headers, timeout=30)

            # 打印调试信息
            print(f"API Response Status: {response.status_code}")
            print(f"API Response Headers: {dict(response.headers)}")
            print(f"API Response Text (first 500 chars): {response.text[:500] if response.text else 'Empty'}")

            if response.status_code != 200:
                return None

            data = response.json()
            return data.get('data')
        except Exception as e:
            print(f"Error getting download link: {e}")
            print(f"Response text: {response.text if 'response' in dir() else 'N/A'}")
            return None

    def download_excel(self, bucket_path: str, doc_id: str, save_path: str) -> bool:
        """下载 Excel 文件到指定路径"""
        download_url = self.get_download_link(bucket_path, doc_id)
        if not download_url:
            return False

        try:
            headers = {}
            if self.cookie:
                headers['Cookie'] = self.cookie
            response = requests.get(download_url, headers=headers, stream=True, timeout=60)
            if response.status_code == 200:
                with open(save_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
                return True
            return False
        except Exception as e:
            print(f"Download error: {e}")
            return False

    def save_to_cache(self, bucket_path: str, doc_id: str, version_name: str, cache_dir: str) -> Optional[str]:
        """
        下载并保存到缓存
        命名格式: {version_name}_{date}.xlsx
        """
        os.makedirs(cache_dir, exist_ok=True)
        date_str = datetime.now().strftime('%Y%m%d')
        filename = f"{version_name}_{date_str}.xlsx"
        save_path = os.path.join(cache_dir, filename)

        if self.download_excel(bucket_path, doc_id, save_path):
            return save_path
        return None


if __name__ == '__main__':
    # 测试代码
    fetcher = DataFetcher()
    url = fetcher.construct_download_url('/7223826/479248', 'test_doc_id')
    print(f"Constructed URL: {url}")
