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
        self.csrf_token = self._extract_csrf_token()
        self.session = requests.Session()
        if self.csrf_token:
            self.session.cookies.set('wapcsrftoken', self.csrf_token)

    def _extract_csrf_token(self) -> Optional[str]:
        """从 Cookie 中提取 CSRF token"""
        if not self.cookie:
            return None

        # 尝试匹配 wapcsrftoken
        match = re.search(r'wapcsrftoken=([^;]+)', self.cookie)
        if match:
            return match.group(1)

        # 尝试其他可能的 CSRF token 字段名
        for pattern in [r'csrf_token=([^;]+)', r'csrf=([^;]+)', r'csrftoken=([^;]+)']:
            match = re.search(pattern, self.cookie, re.IGNORECASE)
            if match:
                return match.group(1)

        return None

    def init_session(self) -> bool:
        """初始化会话，先访问 OneBox 首页"""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            }
            if self.cookie:
                headers['Cookie'] = self.cookie

            response = self.session.get(self.HOME_URL, headers=headers, timeout=30)
            print(f"Init session status: {response.status_code}")
            print(f"Init session Set-Cookie: {response.headers.get('Set-Cookie', 'none')}")

            # 从响应头中提取更新后的 CSRF token
            set_cookie = response.headers.get('Set-Cookie', '')
            if set_cookie:
                match = re.search(r'wapcsrftoken=([^;]+)', set_cookie, re.IGNORECASE)
                if match:
                    new_csrf = match.group(1)
                    self.session.cookies.set('wapcsrftoken', new_csrf)
                    print(f"Updated CSRF from Set-Cookie: {new_csrf[:30]}...")

            return response.status_code == 200
        except Exception as e:
            print(f"Init session error: {e}")
            return False

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
            # 先初始化会话
            self.init_session()

            print(f"\n=== Download Request ===")
            print(f"URL: {url}")
            print(f"Cookie length: {len(self.cookie) if self.cookie else 0} chars")
            print(f"CSRF Token: {self.csrf_token[:30] + '...' if self.csrf_token else 'Not found'}")

            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'application/json, text/plain, */*',
                'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
                'Referer': f'https://onebox.huawei.com/perfect/share/doc/{bucket_path}/{doc_id}',
                'Origin': 'https://onebox.huawei.com',
                'X-Requested-With': 'XMLHttpRequest'
            }
            if self.cookie:
                headers['Cookie'] = self.cookie
            if self.csrf_token:
                headers['X-CSRF-Token'] = self.csrf_token

            response = self.session.get(url, headers=headers, timeout=30)

            print(f"Status: {response.status_code}")
            print(f"Content-Type: {response.headers.get('Content-Type', 'unknown')}")
            print(f"Content-Length: {response.headers.get('Content-Length', 'unknown')}")
            print(f"Response text: {response.text}")

            # 检查是否是文件下载（Content-Disposition 头）
            content_disposition = response.headers.get('Content-Disposition', '')
            if 'attachment' in content_disposition or 'download' in content_disposition:
                # 直接返回响应内容
                return response.content

            # 检查是否是 JSON 响应
            content_type = response.headers.get('Content-Type', '')
            if 'application/json' in content_type:
                data = response.json()
                return data.get('data')

            # 如果是 HTML 页面，尝试提取下载链接
            if 'text/html' in content_type:
                import re
                # 尝试从 HTML 中提取下载链接
                patterns = [
                    r"downloadUrl\s*[=:]\s*['\"]([^'\"]+)['\"]",
                    r"download_url\s*[=:]\s*['\"]([^'\"]+)['\"]",
                    r"url\s*[=:]\s*['\"]([^'\"]+\.xlsx?)['\"]",
                    r"href\s*=\s*['\"]([^'\"]+\.xlsx?)['\"]",
                    r"download\s*[=:]\s*['\"]([^'\"]+)['\"]",
                ]
                for pattern in patterns:
                    match = re.search(pattern, response.text, re.IGNORECASE)
                    if match:
                        download_url = match.group(1)
                        print(f"Found download URL in HTML: {download_url[:100]}...")
                        return download_url

                # 如果找不到，返回 None（无法解析）
                print(f"HTML response but no download URL found")
                return None

            return None
        except Exception as e:
            print(f"Error: {e}")
            return None

    def download_excel(self, bucket_path: str, doc_id: str, save_path: str) -> bool:
        """下载 Excel 文件到指定路径"""
        result = self.get_download_link(bucket_path, doc_id)

        # 如果返回的是 bytes（直接是文件内容），直接保存
        if isinstance(result, bytes):
            try:
                with open(save_path, 'wb') as f:
                    f.write(result)
                print(f"Saved {len(result)} bytes to {save_path}")
                return True
            except Exception as e:
                print(f"Save error: {e}")
                return False

        # 如果返回的是 URL，再下载
        download_url = result
        if not download_url:
            return False

        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Referer': 'https://onebox.huawei.com/'
            }
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

    def _get_available_path(self, save_path: str) -> str:
        """获取可用的文件路径，如果文件已存在则添加 (1), (2) 等后缀"""
        if not os.path.exists(save_path):
            return save_path

        dir_name = os.path.dirname(save_path)
        base_name = os.path.basename(save_path)
        name, ext = os.path.splitext(base_name)

        counter = 1
        while True:
            new_filename = f"{name} ({counter}){ext}"
            new_path = os.path.join(dir_name, new_filename)
            if not os.path.exists(new_path):
                return new_path
            counter += 1

    def download_from_url(self, download_url: str, version_name: str, cache_dir: str) -> Optional[str]:
        """
        直接从下载链接下载 Excel 到缓存
        命名格式: {version_name}_{date}.xlsx
        """
        os.makedirs(cache_dir, exist_ok=True)
        date_str = datetime.now().strftime('%Y%m%d')
        filename = f"{version_name}_{date_str}.xlsx"
        save_path = os.path.join(cache_dir, filename)

        # 处理重名文件
        save_path = self._get_available_path(save_path)
        print(f"Save path: {save_path}")

        try:
            print(f"\n=== Downloading from URL ===")
            print(f"URL: {download_url}")

            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Referer': 'https://onebox.huawei.com/'
            }
            if self.cookie:
                headers['Cookie'] = self.cookie

            response = requests.get(download_url, headers=headers, stream=True, timeout=60)
            print(f"Status: {response.status_code}")
            print(f"Content-Type: {response.headers.get('Content-Type', 'unknown')}")

            if response.status_code == 200:
                with open(save_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
                print(f"Saved to {save_path}")
                return save_path
            else:
                print(f"Download failed: {response.status_code}")
                return None
        except Exception as e:
            print(f"Download error: {e}")
            return None

    def save_to_cache(self, bucket_path: str, doc_id: str, version_name: str, cache_dir: str) -> Optional[str]:
        """
        下载并保存到缓存（旧接口，保留兼容）
        命名格式: {version_name}_{date}.xlsx
        """
        os.makedirs(cache_dir, exist_ok=True)
        date_str = datetime.now().strftime('%Y%m%d')
        filename = f"{version_name}_{date_str}.xlsx"
        save_path = os.path.join(cache_dir, filename)

        # 处理重名文件
        save_path = self._get_available_path(save_path)

        if self.download_excel(bucket_path, doc_id, save_path):
            return save_path
        return None


if __name__ == '__main__':
    # 测试代码
    fetcher = DataFetcher()
    url = fetcher.construct_download_url('/7223826/479248', 'test_doc_id')
    print(f"Constructed URL: {url}")
