from flask import Flask, render_template, g
import sqlite3
from pathlib import Path
import csv
from datetime import datetime

# --- Cấu hình ---
DATABASE = Path(__file__).parent / "data" / "facebook_bot.db"
PRODUCTS_CSV = Path(__file__).parent / "data" / "products.csv"
PER_PAGE = 25 # Số mục hiển thị trên mỗi trang

app = Flask(__name__)

# --- Tải dữ liệu sản phẩm ---
def load_product_names():
    """Tải tên sản phẩm từ CSV vào một dictionary để tra cứu."""
    product_names = {}
    try:
        with open(PRODUCTS_CSV, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                product_names[int(row['product_id'])] = row['name']
    except (FileNotFoundError, KeyError, ValueError) as e:
        app.logger.error(f"Lỗi khi tải file sản phẩm: {e}")
    return product_names

# --- Quản lý kết nối DB ---
def get_db():
    """Mở một kết nối DB mới nếu chưa có cho context hiện tại."""
    if 'db' not in g:
        try:
            g.db = sqlite3.connect(
                DATABASE,
                detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES,
                check_same_thread=False
            )
            g.db.row_factory = sqlite3.Row
        except sqlite3.Error as e:
            app.logger.error(f"Không thể kết nối tới database: {e}")
            return None
    return g.db

@app.teardown_appcontext
def close_db(e=None):
    """Đóng kết nối DB khi context của app bị hủy."""
    db = g.pop('db', None)
    if db is not None:
        db.close()

# --- Các route ---
@app.route('/')
def index():
    """Trang chính của dashboard."""
    db_conn = get_db()
    if not db_conn:
        return "Lỗi: Không thể kết nối tới database.", 500

    product_names = load_product_names()
    stats = {}

    try:
        # Thống kê tổng quan
        stats['total_scanned'] = db_conn.execute('SELECT COUNT(*) FROM posts').fetchone()[0]
        stats['total_matched'] = db_conn.execute("SELECT COUNT(*) FROM posts WHERE status = 'matched'").fetchone()[0]
        stats['total_commented'] = db_conn.execute("SELECT COUNT(*) FROM posts WHERE status = 'commented'").fetchone()[0]

        # Thống kê hôm nay
        today_str = datetime.now().strftime('%Y-%m-%d')
        stats['comments_today'] = db_conn.execute(
            "SELECT COUNT(*) FROM comments WHERE date(commented_at) = ?", (today_str,)
        ).fetchone()[0]

        # Lấy dữ liệu gần đây
        recent_posts = db_conn.execute('SELECT * FROM posts ORDER BY crawled_at DESC LIMIT ?', (PER_PAGE,)).fetchall()
        recent_comments = db_conn.execute('SELECT * FROM comments ORDER BY commented_at DESC LIMIT ?', (PER_PAGE,)).fetchall()

    except sqlite3.OperationalError as e:
        # Xử lý trường hợp bảng chưa tồn tại
        if "no such table" in str(e):
             return render_template('error.html', message="Database chưa được khởi tạo. Vui lòng chạy `python main.py` trước tiên.")
        else:
             return render_template('error.html', message=f"Lỗi truy vấn database: {e}")
    except Exception as e:
        return render_template('error.html', message=f"Đã có lỗi xảy ra: {e}")


    return render_template(
        'index.html',
        stats=stats,
        recent_posts=recent_posts,
        recent_comments=recent_comments,
        product_names=product_names
    )

@app.route('/posts')
def all_posts():
    # Tương tự, bạn có thể tạo trang để xem tất cả bài viết với phân trang
    return "Chức năng xem tất cả bài viết sẽ được phát triển sau."

@app.route('/comments')
def all_comments():
    # Tương tự, bạn có thể tạo trang để xem tất cả bình luận
    return "Chức năng xem tất cả bình luận sẽ được phát triển sau."

if __name__ == '__main__':
    # Để chạy dashboard: python app.py
    # Sau đó truy cập http://127.0.0.1:5000
    app.run(debug=True, port=5000)