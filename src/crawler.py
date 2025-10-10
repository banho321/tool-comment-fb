import asyncio
from playwright.async_api import async_playwright, Page, TimeoutError
from pathlib import Path
import logging
import argparse
from urllib.parse import urlparse, parse_qs

# Import các module tự viết
from src.utils import load_config, load_text_file, normalize_text
import src.db as db

# Thiết lập logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class FacebookCrawler:
    def __init__(self, account_id: str, groups: list[str], config: dict):
        self.account_id = account_id
        self.groups = groups
        self.config = config
        self.base_url = "https://www.facebook.com"

        # Đường dẫn session
        self.storage_state_path = Path(__file__).parent.parent / "sessions" / self.account_id / "storage_state.json"
        if not self.storage_state_path.exists():
            raise FileNotFoundError(f"Không tìm thấy file session cho tài khoản '{self.account_id}'. Vui lòng chạy login_helper.py trước.")

    async def run(self):
        """Khởi chạy crawler."""
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=self.config['settings'].get('headless_browser', True)
            )
            context = await browser.new_context(
                storage_state=self.storage_state_path,
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/94.0.4606.81 Safari/537.36"
            )
            page = await context.new_page()

            logging.info(f"Bắt đầu quét cho tài khoản: {self.account_id}")

            for group_id in self.groups:
                await self._crawl_group(page, group_id.strip())

            await context.close()
            await browser.close()
            logging.info("Hoàn tất quá trình quét.")

    async def _crawl_group(self, page: Page, group_id: str):
        """Quét một group cụ thể."""
        group_url = f"{self.base_url}/groups/{group_id}/"
        logging.info(f"Đang quét group: {group_url}")

        try:
            await page.goto(group_url, wait_until="networkidle", timeout=60000)
            await page.wait_for_selector('div[role="feed"]', timeout=30000)
        except TimeoutError:
            logging.error(f"Không thể tải feed của group {group_id}. Có thể group không tồn tại hoặc cần quyền truy cập.")
            return
        except Exception as e:
            logging.error(f"Lỗi khi truy cập group {group_id}: {e}")
            return

        # Cuộn trang để tải thêm bài viết
        max_posts = self.config['settings'].get('max_posts_to_scan_per_group', 20)
        post_selectors = 'div[role="article"]'

        for _ in range(5): # Cuộn tối đa 5 lần
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await asyncio.sleep(5) # Chờ để bài viết mới tải
            if await page.locator(post_selectors).count() >= max_posts:
                break

        # Lấy các bài viết
        posts = await page.locator(post_selectors).all()
        logging.info(f"Tìm thấy {len(posts)} bài viết trong group {group_id}. Bắt đầu trích xuất...")

        for i, post_element in enumerate(posts[:max_posts]):
            try:
                full_text = await post_element.inner_text()
                if not full_text:
                    continue

                # Lấy link bài viết (permalink) để có post_id
                post_id = None
                # Selector cho link thời gian của bài viết, thường chứa permalink
                permalink_element = post_element.locator('a[href*="/posts/"]:not([role="button"])').first

                if await permalink_element.count() > 0:
                    href = await permalink_element.get_attribute('href')
                    # Trích xuất post_id từ URL
                    parsed_url = urlparse(href)
                    path_parts = parsed_url.path.strip('/').split('/')
                    if 'posts' in path_parts:
                        post_id_index = path_parts.index('posts') + 1
                        if post_id_index < len(path_parts):
                            post_id = path_parts[post_id_index]

                # Nếu không có post_id thì bỏ qua
                if not post_id:
                    logging.warning("Không tìm thấy post_id, bỏ qua bài viết.")
                    continue

                # Facebook đôi khi dùng fbid trong query string
                if post_id.isnumeric() == False:
                    parsed_url = urlparse(href)
                    query_params = parse_qs(parsed_url.query)
                    if 'story_fbid' in query_params:
                        post_id = query_params['story_fbid'][0]
                    else:
                         logging.warning(f"Post ID không hợp lệ: {post_id}, bỏ qua.")
                         continue

                # Lấy thời gian đăng bài
                # Thường nằm trong attribute `aria-label` hoặc text của permalink
                created_at = await permalink_element.text_content()

                post_data = {
                    "post_id": f"{group_id}_{post_id}", # Tạo ID duy nhất
                    "group_id": group_id,
                    "created_at": created_at,
                    "full_text": full_text,
                    "normalized_text": normalize_text(full_text)
                }

                logging.info(f"Đã xử lý bài viết: {post_data['post_id']}")
                db.add_post(post_data)

            except Exception as e:
                logging.error(f"Lỗi khi xử lý một bài viết trong group {group_id}: {e}")

def main():
    parser = argparse.ArgumentParser(description="Quét các bài viết mới từ group Facebook.")
    parser.add_argument("--account", required=True, help="ID của tài khoản để sử dụng session.")
    parser.add_argument("--groups", required=True, help="Đường dẫn tới file .txt chứa danh sách group ID.")

    args = parser.parse_args()

    config = load_config()
    if not config:
        logging.error("Không thể tải cấu hình. Thoát.")
        return

    groups = load_text_file(args.groups)
    if not groups:
        logging.error("Không có group nào để quét. Thoát.")
        return

    crawler = FacebookCrawler(account_id=args.account, groups=groups, config=config)
    try:
        asyncio.run(crawler.run())
    except FileNotFoundError as e:
        logging.error(e)
    except Exception as e:
        logging.error(f"Lỗi không xác định trong quá trình chạy crawler: {e}")

if __name__ == "__main__":
    # Ví dụ cách chạy:
    # python src/crawler.py --account acc1 --groups data/groups.txt
    # Cần phải chạy `python src/login_helper.py --account acc1` trước
    main()