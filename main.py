import argparse
import logging
import asyncio

# Import các module và tiện ích
import src.db as db
from src.utils import load_config, load_products, load_text_file
from src.crawler import FacebookCrawler
from src.matcher import PostMatcher
from src.commenter import FacebookCommenter

# Thiết lập logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("bot.log"),
        logging.StreamHandler()
    ]
)

def main():
    """Hàm chính điều phối toàn bộ hoạt động của bot."""
    parser = argparse.ArgumentParser(
        description="Facebook Group Comment Bot",
        formatter_class=argparse.RawTextHelpFormatter
    )

    # Các đối số bắt buộc
    parser.add_argument("--account", required=True, help="ID của tài khoản để sử dụng session.")

    # Các đối số tùy chọn cho file input
    parser.add_argument("--groups-file", default="data/groups.txt", help="Đường dẫn tới file chứa danh sách group.")
    parser.add_argument("--products-file", default="data/products.csv", help="Đường dẫn tới file chứa danh sách sản phẩm.")
    parser.add_argument("--templates-file", default="data/templates.txt", help="Đường dẫn tới file chứa các mẫu bình luận.")

    # Cờ để điều khiển các bước chạy
    parser.add_argument("--skip-crawler", action='store_true', help="Bỏ qua bước quét bài viết.")
    parser.add_argument("--skip-matcher", action='store_true', help="Bỏ qua bước lọc và đối sánh.")
    parser.add_argument("--skip-commenter", action='store_true', help="Bỏ qua bước bình luận.")
    parser.add_argument("--dry-run", action='store_true', help="Chạy ở chế độ thử, không đăng bình luận thật.")

    args = parser.parse_args()

    logging.info("="*20 + " BOT BẮT ĐẦU " + "="*20)

    # 1. Khởi tạo và tải cấu hình
    logging.info("Đang tải cấu hình và dữ liệu...")
    db.initialize_db()
    config = load_config()
    if not config:
        logging.critical("Không thể tải file config.yaml. Thoát.")
        return

    # Cập nhật config với cờ dry-run nếu được truyền vào
    if args.dry_run:
        config['settings']['dry_run'] = True
        logging.warning("DRY-RUN mode is enabled globally.")

    products = load_products(args.products_file)
    groups = load_text_file(args.groups_file)
    templates = load_text_file(args.templates_file)

    # 2. Chạy Crawler
    if not args.skip_crawler:
        logging.info("-" * 20 + " BƯỚC 1: CRAWLER " + "-" * 20)
        if not groups:
            logging.error("Không có group nào trong file. Bỏ qua bước crawler.")
        else:
            try:
                crawler = FacebookCrawler(account_id=args.account, groups=groups, config=config)
                asyncio.run(crawler.run())
            except FileNotFoundError as e:
                logging.critical(f"Lỗi nghiêm trọng với Crawler: {e}. Vui lòng chạy login_helper.py cho tài khoản '{args.account}'.")
                return # Dừng hẳn nếu không có session
            except Exception as e:
                logging.error(f"Lỗi không xác định trong Crawler: {e}")
    else:
        logging.info("Bỏ qua bước Crawler theo yêu cầu.")

    # 3. Chạy Matcher
    if not args.skip_matcher:
        logging.info("-" * 20 + " BƯỚC 2: MATCHER " + "-" * 20)
        if not products:
            logging.error("Không có sản phẩm nào trong file. Bỏ qua bước matcher.")
        else:
            try:
                matcher = PostMatcher(config=config, products=products)
                matcher.run()
            except Exception as e:
                logging.error(f"Lỗi không xác định trong Matcher: {e}")
    else:
        logging.info("Bỏ qua bước Matcher theo yêu cầu.")

    # 4. Chạy Commenter
    if not args.skip_commenter:
        logging.info("-" * 20 + " BƯỚC 3: COMMENTER " + "-" * 20)
        if not products or not templates:
            logging.error("Thiếu file sản phẩm hoặc mẫu bình luận. Bỏ qua bước commenter.")
        else:
            try:
                commenter = FacebookCommenter(
                    account_id=args.account,
                    config=config,
                    products=products,
                    templates=templates
                )
                asyncio.run(commenter.run())
            except FileNotFoundError as e:
                 logging.critical(f"Lỗi nghiêm trọng với Commenter: {e}. Vui lòng chạy login_helper.py cho tài khoản '{args.account}'.")
                 return # Dừng hẳn nếu không có session
            except Exception as e:
                logging.error(f"Lỗi không xác định trong Commenter: {e}")
    else:
        logging.info("Bỏ qua bước Commenter theo yêu cầu.")

    logging.info("="*20 + " BOT KẾT THÚC " + "="*20)

if __name__ == "__main__":
    main()