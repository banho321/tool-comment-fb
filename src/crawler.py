import asyncio
import random
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
        max_retries = 3
        retry_count = 0
        
        while retry_count < max_retries:
            try:
                async with async_playwright() as p:
                    # Use Firefox instead of Chromium for better Facebook compatibility
                    browser = await p.firefox.launch(
                        headless=self.config['settings'].get('headless_browser', True),
                        args=[
                            '--no-sandbox',
                            '--disable-setuid-sandbox',
                            '--disable-dev-shm-usage'
                        ]
                    )
                    context = await browser.new_context(
                        storage_state=self.storage_state_path,
                        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/121.0",
                        viewport={'width': 1920, 'height': 1080}
                    )
                    page = await context.new_page()
                    
                    # Thêm event listeners để xử lý lỗi
                    page.on("pageerror", lambda error: logging.error(f"Page error: {error}"))
                    page.on("crash", lambda: logging.error("Page crashed"))
                    page.on("close", lambda: logging.warning("Page closed unexpectedly"))

                    logging.info(f"Bắt đầu quét cho tài khoản: {self.account_id}")

                    for group_id in self.groups:
                        try:
                            await self._crawl_group(page, group_id.strip())
                        except Exception as e:
                            logging.error(f"Lỗi khi crawl group {group_id}: {e}")
                            # Tiếp tục với group tiếp theo thay vì dừng toàn bộ
                            continue

                    await context.close()
                    await browser.close()
                    logging.info("Hoàn tất quá trình quét.")
                    break  # Thành công, thoát khỏi retry loop
                    
            except Exception as e:
                retry_count += 1
                logging.error(f"Lỗi trong lần thử {retry_count}/{max_retries}: {e}")
                if retry_count < max_retries:
                    logging.info(f"Chờ 30 giây trước khi thử lại...")
                    await asyncio.sleep(30)
                else:
                    logging.error("Đã thử tối đa số lần, dừng crawler.")
                    raise

    async def _crawl_group(self, page: Page, group_id: str):
        """Quét một group cụ thể."""
        group_url = f"{self.base_url}/groups/{group_id}/"
        logging.info(f"Đang quét group: {group_url}")

        try:
            # Navigate to group
            await page.goto(group_url, wait_until="domcontentloaded", timeout=30000)
            
            # Wait for page to load
            await asyncio.sleep(5)
            
            # Check for redirects
            current_url = page.url
            if "login" in current_url or "facebook.com/groups" not in current_url:
                logging.warning(f"Bị redirect về {current_url}, có thể session đã hết hạn")
                return
            
            # Check for errors
            error_selectors = [
                'div[data-testid="error"]',
                'div[role="alert"]',
                'div[class*="error"]',
                'div[class*="blocked"]',
                'div[class*="restricted"]',
                'div[class*="unavailable"]'
            ]
            
            for error_selector in error_selectors:
                try:
                    if await page.locator(error_selector).count() > 0:
                        error_text = await page.locator(error_selector).first.inner_text()
                        logging.error(f"Group {group_id} bị chặn: {error_text}")
                        return
                except Exception:
                    continue
            
            # Check for join requirements
            try:
                join_buttons = await page.locator('button:has-text("Tham gia"), button:has-text("Join"), button:has-text("Request to join")').count()
                if join_buttons > 0:
                    logging.warning(f"Group {group_id} yêu cầu tham gia trước khi xem feed")
                    return
            except Exception:
                pass
            
            # Look for feed
            feed_selectors = [
                'div[role="feed"]',
                'div[data-pagelet="FeedUnit_0"]',
                'div[aria-label*="feed"]',
                'div[data-testid="fbfeed_story"]',
                'div[role="main"] div[role="article"]',
                'div[data-pagelet*="Feed"]'
            ]
            
            feed_found = False
            for selector in feed_selectors:
                try:
                    if await page.locator(selector).count() > 0:
                        logging.info(f"Tìm thấy feed với selector: {selector}")
                        feed_found = True
                        break
                except Exception:
                    continue
            
            if not feed_found:
                logging.warning(f"Không tìm thấy feed cho group {group_id}")
                return
            
            # Process posts
            await self._process_posts(page, group_id)
            
        except TimeoutError:
            logging.error(f"Timeout when accessing group {group_id}. The page took too long to load.")
        except Exception as e:
            if "Target page, context or browser has been closed" in str(e):
                logging.error(f"Browser closed unexpectedly for group {group_id}. Re-raising to trigger a restart.")
                raise  # Re-raise to be caught by the main retry loop
            logging.error(f"An unexpected error occurred while crawling group {group_id}: {e}")

    async def _process_posts(self, page: Page, group_id: str):
        """Xử lý các bài viết trong group."""
        max_posts = self.config['settings'].get('max_posts_to_scan_per_group', 20)
        
        # Scroll to load more posts with human-like behavior
        for i in range(5):  # Scroll up to 5 times
            scroll_amount = random.randint(500, 1500)  # Scroll a random amount
            await page.evaluate(f"window.scrollBy(0, {scroll_amount})")

            # Move mouse randomly
            await page.mouse.move(random.randint(100, 800), random.randint(100, 800))

            # Random delay
            await asyncio.sleep(random.uniform(1.5, 4.0))

            # 30% chance to scroll up a bit to simulate reading
            if random.random() < 0.3:
                await page.evaluate("window.scrollBy(0, -200)")
                await asyncio.sleep(random.uniform(0.5, 1.5))
        
        # Find posts
        post_selectors = [
            'div[role="article"]',
            'div[data-pagelet*="FeedUnit"]',
            'div[data-testid="fbfeed_story"]',
            'div[aria-label*="story"]'
        ]
        
        posts = []
        for selector in post_selectors:
            try:
                posts = await page.locator(selector).all()
                if posts:
                    logging.info(f"Tìm thấy {len(posts)} bài viết với selector: {selector}")
                    break
            except Exception:
                continue
        
        if not posts:
            logging.warning(f"Không tìm thấy bài viết nào trong group {group_id}")
            return
        
        # Process posts
        for i, post_element in enumerate(posts[:max_posts]):
            if page.is_closed():
                logging.error("Page was closed during post processing. Stopping crawl for this group.")
                break
            try:
                # Check if the element is still attached to the DOM
                if not await post_element.is_visible():
                    logging.warning("Post element is no longer visible, skipping.")
                    continue

                # Cố gắng tìm phần tử nội dung chính của bài đăng
                content_selector = 'div[data-ad-preview="message"]'
                try:
                    content_element = post_element.locator(content_selector).first
                    if await content_element.is_visible():
                        full_text = await content_element.inner_text()
                    else:
                        # Fallback nếu không tìm thấy bộ chọn cụ thể
                        full_text = await post_element.inner_text()
                except Exception:
                    # Fallback nếu có lỗi xảy ra
                    full_text = await post_element.inner_text()

                logging.info(f"--- CRAWLED POST CONTENT ---\n{full_text}\n--------------------------")
                if not full_text:
                    continue
                
                post_id = await self._extract_post_id(post_element, group_id)
                if not post_id:
                    continue
                
                post_data = {
                    "post_id": f"{group_id}_{post_id}",
                    "group_id": group_id,
                    "created_at": str(int(asyncio.get_event_loop().time())),
                    "full_text": full_text,
                    "normalized_text": normalize_text(full_text)
                }
                
                logging.info(f"Processed post: {post_data['post_id']}")
                db.add_post(post_data)
                
            except Exception as e:
                # Catch specific errors related to elements being detached or navigation
                if "Target page, context or browser has been closed" in str(e) or \
                   "Execution context was destroyed" in str(e):
                    logging.error(f"Browser context lost while processing post {i} in group {group_id}. Aborting group crawl.")
                    break # Exit the loop for this group
                else:
                    logging.warning(f"Could not process post {i} in group {group_id}: {e}")

    async def _extract_post_id(self, post_element, group_id: str) -> str:
        """Trích xuất post ID từ element."""
        try:
            link_selectors = [
                'a[href*="/posts/"]',
                'a[href*="/permalink/"]',
                'a[href*="/story.php"]'
            ]
            
            for selector in link_selectors:
                try:
                    link_element = post_element.locator(selector).first
                    if await link_element.count() > 0:
                        href = await link_element.get_attribute('href')
                        if href:
                            parsed_url = urlparse(href)
                            path_parts = parsed_url.path.strip('/').split('/')
                            if 'posts' in path_parts:
                                post_id_index = path_parts.index('posts') + 1
                                if post_id_index < len(path_parts):
                                    return path_parts[post_id_index]
                except Exception:
                    continue
        except Exception:
            pass
        
        return None

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