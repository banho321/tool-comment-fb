import sqlite3
from pathlib import Path
import logging
from datetime import datetime, timedelta

# Thiết lập đường dẫn tới file database trong thư mục data
DB_FILE = Path(__file__).parent.parent / "data" / "facebook_bot.db"
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def get_db_connection():
    """Tạo và trả về một kết nối tới database."""
    try:
        conn = sqlite3.connect(DB_FILE, detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES)
        conn.row_factory = sqlite3.Row
        return conn
    except sqlite3.Error as e:
        logging.error(f"Lỗi kết nối database: {e}")
        return None

def initialize_db():
    """Khởi tạo các bảng trong database nếu chúng chưa tồn tại."""
    logging.info(f"Đang khởi tạo database tại: {DB_FILE}")
    conn = get_db_connection()
    if conn is None:
        return

    try:
        with conn:
            # Bảng lưu thông tin các bài viết được quét
            conn.execute("""
                CREATE TABLE IF NOT EXISTS posts (
                    post_id TEXT PRIMARY KEY,
                    group_id TEXT NOT NULL,
                    author_id TEXT,
                    created_at TEXT NOT NULL,
                    crawled_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    full_text TEXT,
                    normalized_text TEXT,
                    status TEXT DEFAULT 'new', -- 'new', 'matched', 'commented', 'skipped_blacklist', 'skipped_age', 'error'
                    matched_product_id INTEGER,
                    comment_id TEXT
                )
            """)

            # Bảng lưu lịch sử các comment đã thực hiện
            conn.execute("""
                CREATE TABLE IF NOT EXISTS comments (
                    comment_id TEXT PRIMARY KEY,
                    post_id TEXT NOT NULL,
                    account_id TEXT NOT NULL,
                    product_id INTEGER,
                    shopee_link TEXT,
                    template_used TEXT,
                    commented_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    status TEXT DEFAULT 'success', -- 'success', 'failed', 'deleted'
                    FOREIGN KEY (post_id) REFERENCES posts (post_id)
                )
            """)
            logging.info("Khởi tạo database thành công.")
    except sqlite3.Error as e:
        logging.error(f"Lỗi khi khởi tạo bảng: {e}")
    finally:
        conn.close()

def add_post(post_data: dict):
    """Thêm một bài viết mới vào DB, bỏ qua nếu đã tồn tại."""
    sql = """
        INSERT OR IGNORE INTO posts (post_id, group_id, created_at, full_text, normalized_text)
        VALUES (:post_id, :group_id, :created_at, :full_text, :normalized_text)
    """
    conn = get_db_connection()
    try:
        with conn:
            conn.execute(sql, post_data)
    except sqlite3.IntegrityError:
        logging.warning(f"Bài viết {post_data.get('post_id')} đã tồn tại.")
    except sqlite3.Error as e:
        logging.error(f"Lỗi khi thêm bài viết {post_data.get('post_id')}: {e}")
    finally:
        if conn:
            conn.close()

def get_posts_to_match():
    """Lấy danh sách các bài viết có trạng thái 'new' để xử lý."""
    conn = get_db_connection()
    try:
        cursor = conn.execute("SELECT * FROM posts WHERE status = 'new'")
        posts = cursor.fetchall()
        return [dict(row) for row in posts]
    except sqlite3.Error as e:
        logging.error(f"Lỗi khi lấy bài viết để match: {e}")
        return []
    finally:
        if conn:
            conn.close()

def update_post_status(post_id: str, status: str, matched_product_id: int = None):
    """Cập nhật trạng thái của một bài viết."""
    sql = "UPDATE posts SET status = ?, matched_product_id = ? WHERE post_id = ?"
    conn = get_db_connection()
    try:
        with conn:
            conn.execute(sql, (status, matched_product_id, post_id))
    except sqlite3.Error as e:
        logging.error(f"Lỗi khi cập nhật trạng thái bài viết {post_id}: {e}")
    finally:
        if conn:
            conn.close()

def add_comment_log(comment_data: dict):
    """Ghi log một comment vào DB."""
    sql = """
        INSERT INTO comments (comment_id, post_id, account_id, product_id, shopee_link, template_used, status)
        VALUES (:comment_id, :post_id, :account_id, :product_id, :shopee_link, :template_used, :status)
    """
    conn = get_db_connection()
    try:
        with conn:
            conn.execute(sql, comment_data)
        # Cập nhật trạng thái bài viết tương ứng
        update_post_status(comment_data['post_id'], 'commented')
    except sqlite3.Error as e:
        logging.error(f"Lỗi khi ghi log comment cho bài viết {comment_data['post_id']}: {e}")
    finally:
        if conn:
            conn.close()

def get_comment_count_for_account(account_id: str, hours: int = 1, days: int = 0) -> int:
    """Đếm số lượng comment của một account trong một khoảng thời gian."""
    if hours:
        since = datetime.now() - timedelta(hours=hours)
        time_col = 'commented_at'
        sql = f"SELECT COUNT(*) FROM comments WHERE account_id = ? AND {time_col} >= ?"
        params = (account_id, since)
    elif days:
        since = datetime.now() - timedelta(days=days)
        time_col = 'commented_at'
        sql = f"SELECT COUNT(*) FROM comments WHERE account_id = ? AND date({time_col}) = date(?)"
        params = (account_id, since)
    else: # per day
        since = datetime.now().date()
        sql = "SELECT COUNT(*) FROM comments WHERE account_id = ? AND date(commented_at) = ?"
        params = (account_id, since)


    conn = get_db_connection()
    try:
        cursor = conn.execute(sql, params)
        count = cursor.fetchone()[0]
        return count
    except sqlite3.Error as e:
        logging.error(f"Lỗi khi đếm comment cho {account_id}: {e}")
        return 0 # Trả về 0 để tránh bị block do lỗi
    finally:
        if conn:
            conn.close()

if __name__ == '__main__':
    # Chạy file này trực tiếp để khởi tạo DB
    initialize_db()
    # Ví dụ thêm dữ liệu
    # print("Kiểm tra các hàm DB...")
    # post = {
    #     "post_id": "groupid_postid123", "group_id": "12345", "created_at": "2023-10-27T10:00:00",
    #     "full_text": "Cần mua máy xay abc", "normalized_text": "can mua may xay abc"
    # }
    # add_post(post)
    # posts_to_match = get_posts_to_match()
    # print(f"Tìm thấy {len(posts_to_match)} bài viết mới.")
    # if posts_to_match:
    #     print(f"Bài viết đầu tiên: {posts_to_match[0]['post_id']}")
    #     update_post_status(posts_to_match[0]['post_id'], 'matched', 1001)

    # count = get_comment_count_for_account('acc1', days=1)
    # print(f"Số comment của acc1 trong ngày: {count}")