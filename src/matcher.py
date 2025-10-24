import logging
import re
from datetime import datetime, timedelta
import argparse
from thefuzz import fuzz

# Import các module tự viết
from src.utils import load_config, load_products, normalize_text
import src.db as db

# Thiết lập logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class PostMatcher:
    def __init__(self, config: dict, products: list):
        self.config = config
        self.products = products
        self.matcher_config = config.get('matcher', {})
        self.blacklist = self.matcher_config.get('blacklist', [])

    def run(self):
        """Chạy quá trình lọc và đối sánh."""
        logging.info("Bắt đầu quá trình lọc và đối sánh bài viết...")
        posts_to_check = db.get_posts_to_match()

        if not posts_to_check:
            logging.info("Không có bài viết mới nào để xử lý.")
            return

        logging.info(f"Tìm thấy {len(posts_to_check)} bài viết mới. Đang xử lý...")

        for post in posts_to_check:
            self._process_post(post)

        logging.info("Hoàn tất quá trình lọc và đối sánh.")

    def _process_post(self, post: dict):
        """Xử lý một bài viết duy nhất: lọc, rồi đối sánh."""
        post_id = post['post_id']

        # 1. Lọc bài viết
        is_valid, reason = self._filter_post(post)
        if not is_valid:
            logging.info(f"Bài viết {post_id} bị bỏ qua. Lý do: {reason}")
            db.update_post_status(post_id, status=reason)
            return

        # 2. Đối sánh từ khóa
        matched_product = self._match_keywords(post)
        if matched_product:
            logging.info(f"MATCH! Bài viết {post_id} khớp với sản phẩm '{matched_product['name']}' (ID: {matched_product['product_id']}).")
            db.update_post_status(post_id, status='matched', matched_product_id=int(matched_product['product_id']))
        else:
            # Nếu không match, cập nhật trạng thái để không quét lại
            logging.debug(f"Bài viết {post_id} không khớp với sản phẩm nào.")
            db.update_post_status(post_id, status='skipped_unmatched')

    def _filter_post(self, post: dict) -> (bool, str):
        """
        Áp dụng các bộ lọc cho bài viết.
        Trả về (True, None) nếu hợp lệ, (False, reason) nếu không.
        """
        # Lọc theo blacklist
        normalized_text = post.get('normalized_text', '')
        for keyword in self.blacklist:
            if keyword in normalized_text:
                return False, 'skipped_blacklist'

        # Lọc theo tuổi bài viết
        max_age_days = self.config['settings'].get('max_post_age_days', 3)
        post_datetime = self._parse_relative_time(post.get('created_at', ''))

        if post_datetime and (datetime.now() - post_datetime).days > max_age_days:
            return False, 'skipped_age'

        return True, None

    def _parse_relative_time(self, time_str: str) -> datetime | None:
        """
        Chuyển đổi chuỗi thời gian tương đối của Facebook (vd: "5m", "2h", "Yesterday") sang datetime.
        Lưu ý: Đây là phiên bản đơn giản, có thể cần `dateparser` cho các trường hợp phức tạp hơn.
        """
        if not time_str: return None

        time_str = time_str.lower().strip()
        now = datetime.now()

        # Tiếng Anh
        if 'just now' in time_str: return now
        if 'm' in time_str:
            minutes = int(re.search(r'(\d+)\s*m', time_str).group(1))
            return now - timedelta(minutes=minutes)
        if 'h' in time_str:
            hours = int(re.search(r'(\d+)\s*h', time_str).group(1))
            return now - timedelta(hours=hours)
        if 'd' in time_str:
            days = int(re.search(r'(\d+)\s*d', time_str).group(1))
            return now - timedelta(days=days)
        if 'yesterday' in time_str:
            return now - timedelta(days=1)

        # Tiếng Việt
        if 'vừa xong' in time_str or 'vừa mới' in time_str: return now
        if 'phút' in time_str:
            minutes = int(re.search(r'(\d+)\s*phút', time_str).group(1))
            return now - timedelta(minutes=minutes)
        if 'giờ' in time_str:
            hours = int(re.search(r'(\d+)\s*giờ', time_str).group(1))
            return now - timedelta(hours=hours)
        if 'ngày' in time_str:
            days = int(re.search(r'(\d+)\s*ngày', time_str).group(1))
            return now - timedelta(days=days)
        if 'hôm qua' in time_str:
            return now - timedelta(days=1)

        return None # Không thể phân tích

    def _match_keywords(self, post: dict) -> dict | None:
        """
        So khớp từ khóa sản phẩm với nội dung bài viết.
        Sử dụng regex word boundary để đảm bảo khớp chính xác từ.
        """
        text_to_search = post.get('normalized_text', '')
        logging.info(f"--- Matching Post ID: {post['post_id']} ---")
        logging.info(f"Normalized Post Text: {text_to_search[:200]}...")

        for product in self.products:
            # Lấy tên và các alias của sản phẩm
            keywords_to_check = [product['name']] + product.get('aliases', [])

            for keyword in keywords_to_check:
                # Chuẩn hóa cả từ khóa để so sánh
                norm_keyword = normalize_text(keyword)
                if not norm_keyword: continue

                logging.info(f"Checking for keyword: '{norm_keyword}' (Product: {product['name']})")
                if norm_keyword in text_to_search:
                    logging.info(f"SUCCESS (Direct Match): Found keyword '{norm_keyword}' in post.")
                    return product

        # Fuzzy Matching Fallback
        fuzzy_config = self.matcher_config.get('fuzzy_matching', {})
        if fuzzy_config.get('enabled', False):
            min_ratio = fuzzy_config.get('min_ratio', 0.92)

            for product in self.products:
                keywords_to_check = [product['name']] + product.get('aliases', [])
                for keyword in keywords_to_check:
                    norm_keyword = normalize_text(keyword)
                    if not norm_keyword: continue

                    # Check for partial ratio, which is good for finding substrings
                    ratio = fuzz.partial_ratio(norm_keyword, text_to_search)
                    if ratio / 100.0 >= min_ratio:
                        logging.debug(f"SUCCESS (Fuzzy Match): Keyword '{norm_keyword}' has ratio {ratio}% in post.")
                        return product

        return None

def main():
    parser = argparse.ArgumentParser(description="Lọc và đối sánh các bài viết đã quét.")
    parser.add_argument("--products", default="data/products.csv", help="Đường dẫn tới file products.csv.")

    args = parser.parse_args()

    config = load_config()
    if not config:
        logging.error("Không thể tải cấu hình. Thoát.")
        return

    products = load_products(args.products)
    if not products:
        logging.error("Không có sản phẩm nào để đối sánh. Thoát.")
        return

    matcher = PostMatcher(config=config, products=products)
    matcher.run()

if __name__ == "__main__":
    # Cách chạy:
    # python src/matcher.py
    main()