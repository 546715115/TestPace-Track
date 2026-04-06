"""
数据获取模块 - 从 OneBox API 下载 Excel
"""
import requests
import os
import json
import re
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
    HOME_URL = "https://onebox.huawei.com/"

    def __init__(self):
        self.cookie = get_cookie_config().get('cookie', '')
        self.csrf_token = None
        self.session = requests.Session()

    def get_csrf_token(self) -> Optional[str]:
        """从 OneBox 首页获取 CSRF token"""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8'
            }
            if self.cookie:
                headers['Cookie'] = self.cookie

            response = self.session.get(self.HOME_URL, headers=headers, timeout=30)

            # 从页面中提取 CSRF token
            # 可能在 meta 标签或 JavaScript 中
            match = re.search(r'csrf["\']?\s*[:=]\s*["\']([^"\']+)["\']', response.text)
            if match:
                return match.group(1)

            # 也可能在 Cookie 中
            match = re.search(r'csrf_token=([^;]+)', self.cookie)
            if match:
                return match.group(1)

            # 或者从响应 Cookie 中获取
            for cookie in self.session.cookies:
                if 'csrf' in cookie.name.lower():
                    return cookie.value

            return None
        except Exception as e:
            print(f"Error getting CSRF token: {e}")
            return None

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

        # 先获取 CSRF token
        if not self.csrf_token:
            self.csrf_token = self.get_csrf_token()
            print(f"CSRF Token: {self.csrf_token[:50] + '...' if self.csrf_token else 'Not found'}")

        try:
            print(f"\n=== Download Request ===")
            print(f"URL: {url}")
            print(f"Cookie length: {len(self.cookie) if self.cookie else 0} chars")

            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'application/json, text/plain, */*',
                'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
                'Referer': f'https://onebox.huawei.com/perfect/share/doc/{doc_id}',
                'Origin': 'https://onebox.huawei.com'
            }
            if self.cookie:
                headers['Cookie'] = self.cookie
            if self.csrf_token:
                headers['X-CSRF-Token'] = self.csrf_token
                headers['x-csrf-token'] = self.csrf_token

            response = self.session.get(url, headers=headers, timeout=30)

            print(f"Status: {response.status_code}")
            print(f"Response: {response.text[:300] if response.text else 'Empty'}")

            if response.status_code != 200:
                return None

            data = response.json()
            return data.get('data')
        except Exception as e:
            print(f"Error: {e}")
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
