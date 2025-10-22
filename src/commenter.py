import asyncio
import logging
import argparse
import random
from pathlib import Path
from playwright.async_api import async_playwright, Page, TimeoutError

# Import các module tự viết
from src.utils import load_config, load_products, load_text_file
import src.db as db

# Thiết lập logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class FacebookCommenter:
    def __init__(self, account_id: str, config: dict, products: list, templates: list):
        self.account_id = account_id
        self.config = config
        self.products = {int(p['product_id']): p for p in products} # Chuyển thành dict để tra cứu nhanh
        self.templates = templates

        self.commenter_config = self.config.get('commenter', {})
        self.rate_limit_config = self.commenter_config.get('rate_limit', {})
        self.human_like_config = self.commenter_config.get('human_like_behavior', {})
        self.dry_run = self.config['settings'].get('dry_run', False)

        self.storage_state_path = Path(__file__).parent.parent / "sessions" / self.account_id / "storage_state.json"
        if not self.storage_state_path.exists():
            raise FileNotFoundError(f"Không tìm thấy file session cho tài khoản '{self.account_id}'. Vui lòng chạy login_helper.py trước.")

    async def run(self):
        """Khởi chạy tiến trình bình luận."""
        logging.info(f"Bắt đầu tiến trình bình luận cho tài khoản: {self.account_id}")
        if self.dry_run:
            logging.warning("CHẾ ĐỘ DRY-RUN ĐANG BẬT. SẼ KHÔNG CÓ BÌNH LUẬN NÀO ĐƯỢC ĐĂNG.")

        posts_to_comment = self._get_posts_to_comment()
        if not posts_to_comment:
            logging.info("Không có bài viết nào được đánh dấu để bình luận.")
            return

        logging.info(f"Tìm thấy {len(posts_to_comment)} bài viết để bình luận.")

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

            for post in posts_to_comment:
                await self._process_post(page, post)

            await context.close()
            await browser.close()
        logging.info("Hoàn tất tiến trình bình luận.")

    def _get_posts_to_comment(self) -> list[dict]:
        """Lấy danh sách bài viết có trạng thái 'matched' từ DB."""
        conn = db.get_db_connection()
        try:
            cursor = conn.execute("SELECT * FROM posts WHERE status = 'matched' ORDER BY crawled_at ASC")
            posts = cursor.fetchall()
            return [dict(row) for row in posts]
        except db.sqlite3.Error as e:
            logging.error(f"Lỗi khi lấy bài viết để bình luận: {e}")
            return []
        finally:
            if conn:
                conn.close()

    def _check_rate_limits(self) -> bool:
        """Kiểm tra xem tài khoản có vượt giới hạn bình luận không. Trả về True nếu OK."""
        max_per_hour = self.rate_limit_config.get('max_comments_per_hour', 5)
        max_per_day = self.rate_limit_config.get('max_comments_per_day', 50)

        comments_last_hour = db.get_comment_count_for_account(self.account_id, hours=1)
        comments_today = db.get_comment_count_for_account(self.account_id, days=1)

        if comments_last_hour >= max_per_hour:
            logging.warning(f"Đã đạt giới hạn {max_per_hour} comment/giờ. Tạm dừng.")
            return False
        if comments_today >= max_per_day:
            logging.warning(f"Đã đạt giới hạn {max_per_day} comment/ngày. Tạm dừng.")
            return False

        return True

    async def _process_post(self, page: Page, post: dict):
        """Xử lý việc bình luận cho một bài viết."""
        post_id = post['post_id']
        product_id = post['matched_product_id']
        product_info = self.products.get(product_id)

        if not product_info:
            logging.error(f"Không tìm thấy thông tin sản phẩm cho ID {product_id}. Bỏ qua bài viết {post_id}.")
            db.update_post_status(post_id, 'error')
            return

        if not self._check_rate_limits():
            return # Dừng nếu đã vi phạm giới hạn

        comment_text = random.choice(self.templates).format(link=product_info['shopee_link'])

        logging.info(f"Chuẩn bị bình luận vào bài viết {post_id} với nội dung: '{comment_text[:50]}...'")

        if self.dry_run:
            logging.info(f"[DRY-RUN] Giả lập bình luận vào bài viết {post_id}.")
            # Trong dry-run, ta vẫn cập nhật status để không bị lặp lại
            db.update_post_status(post_id, 'commented')
            await asyncio.sleep(2) # Giả lập thời gian chờ
            return

        # Bắt đầu bình luận thật
        try:
            # Tách group_id và post_id thực
            real_post_id = post_id.split('_')[-1]
            post_url = f"https://www.facebook.com/{real_post_id}"

            await page.goto(post_url, wait_until="networkidle", timeout=60000)

            # Hành vi giống người
            if self.human_like_config.get('scrolling_enabled', True):
                await page.evaluate("window.scrollTo(0, document.body.scrollHeight * 0.3)")
                await asyncio.sleep(random.uniform(2, 5))

            # Tìm ô comment (sử dụng aria-label để ổn định hơn)
            comment_box_selector = 'div[aria-label*="Viết bình luận"], div[aria-label*="Write a comment"]'
            await page.locator(comment_box_selector).first.click()
            await page.keyboard.type(comment_text, delay=random.uniform(50, 150))
            await asyncio.sleep(random.uniform(1, 3))

            # Gửi comment
            await page.keyboard.press("Enter")
            await page.wait_for_timeout(5000) # Chờ comment xuất hiện

            logging.info(f"Bình luận thành công vào bài viết {post_id}.")

            # Ghi log vào DB
            comment_log = {
                "comment_id": f"{post_id}_{random.randint(1000,9999)}", # Tạo ID giả
                "post_id": post_id,
                "account_id": self.account_id,
                "product_id": product_id,
                "shopee_link": product_info['shopee_link'],
                "template_used": comment_text,
                "status": "success"
            }
            db.add_comment_log(comment_log) # Hàm này cũng sẽ cập nhật status của post

        except TimeoutError:
            logging.error(f"Timeout khi tải bài viết {post_id}. Bỏ qua.")
            db.update_post_status(post_id, 'error')
        except Exception as e:
            logging.error(f"Lỗi khi bình luận vào bài viết {post_id}: {e}")
            db.update_post_status(post_id, 'error')
        finally:
            # Chờ ngẫu nhiên trước khi xử lý bài tiếp theo
            delay = random.randint(
                self.commenter_config.get('min_delay_seconds', 20),
                self.commenter_config.get('max_delay_seconds', 120)
            )
            logging.info(f"Chờ {delay} giây trước khi tiếp tục...")
            await asyncio.sleep(delay)

def main():
    parser = argparse.ArgumentParser(description="Tự động bình luận vào các bài viết đã được đối sánh.")
    parser.add_argument("--account", required=True, help="ID của tài khoản để sử dụng session.")
    parser.add_argument("--products", default="data/products.csv", help="Đường dẫn tới file products.csv.")
    parser.add_argument("--templates", default="data/templates.txt", help="Đường dẫn tới file templates.txt.")

    args = parser.parse_args()

    config = load_config()
    if not config:
        logging.error("Không thể tải cấu hình. Thoát.")
        return

    products = load_products(args.products)
    if not products:
        logging.error("Không có sản phẩm nào. Thoát.")
        return

    templates = load_text_file(args.templates)
    if not templates:
        logging.error("Không có mẫu bình luận nào. Thoát.")
        return

    commenter = FacebookCommenter(
        account_id=args.account,
        config=config,
        products=products,
        templates=templates
    )
    try:
        asyncio.run(commenter.run())
    except FileNotFoundError as e:
        logging.error(e)
    except Exception as e:
        logging.error(f"Lỗi không xác định trong quá trình chạy commenter: {e}")

if __name__ == "__main__":
    # Cách chạy:
    # python src/commenter.py --account acc1
    main()