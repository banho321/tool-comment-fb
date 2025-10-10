import yaml
from pathlib import Path
import logging
import csv
import json
import re

def load_config():
    """Tải file cấu hình config.yaml."""
    config_path = Path(__file__).parent.parent / "config.yaml"
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    except FileNotFoundError:
        logging.error("Không tìm thấy file config.yaml.")
        return None
    except Exception as e:
        logging.error(f"Lỗi khi đọc file config.yaml: {e}")
        return None

def load_products(filepath: str):
    """Tải danh sách sản phẩm từ file CSV."""
    products = []
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                try:
                    # Chuyển đổi chuỗi JSON của aliases thành list
                    row['aliases'] = json.loads(row['aliases'])
                    products.append(row)
                except json.JSONDecodeError:
                    logging.warning(f"Bỏ qua sản phẩm ID {row.get('product_id')} do lỗi JSON trong 'aliases'.")
                except KeyError:
                    logging.warning(f"Bỏ qua dòng không hợp lệ trong products.csv: {row}")
    except FileNotFoundError:
        logging.error(f"Không tìm thấy file sản phẩm: {filepath}")
    return products

def load_text_file(filepath: str) -> list[str]:
    """Tải danh sách các dòng từ một file text (groups.txt, templates.txt)."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            # Bỏ qua các dòng trống và dòng comment
            lines = [line.strip() for line in f if line.strip() and not line.strip().startswith('#')]
            return lines
    except FileNotFoundError:
        logging.error(f"Không tìm thấy file: {filepath}")
        return []

def normalize_text(text: str) -> str:
    """
    Chuẩn hóa văn bản:
    1. Chuyển thành chữ thường.
    2. Xóa dấu tiếng Việt.
    3. Xóa các ký tự đặc biệt không cần thiết.
    """
    if not text:
        return ""
    text = text.lower()
    # Bảng thay thế các ký tự có dấu
    replacements = {
        'á': 'a', 'à': 'a', 'ả': 'a', 'ã': 'a', 'ạ': 'a',
        'ă': 'a', 'ắ': 'a', 'ằ': 'a', 'ẳ': 'a', 'ẵ': 'a', 'ặ': 'a',
        'â': 'a', 'ấ': 'a', 'ầ': 'a', 'ẩ': 'a', 'ẫ': 'a', 'ậ': 'a',
        'đ': 'd',
        'é': 'e', 'è': 'e', 'ẻ': 'e', 'ẽ': 'e', 'ẹ': 'e',
        'ê': 'e', 'ế': 'e', 'ề': 'e', 'ể': 'e', 'ễ': 'e', 'ệ': 'e',
        'í': 'i', 'ì': 'i', 'ỉ': 'i', 'ĩ': 'i', 'ị': 'i',
        'ó': 'o', 'ò': 'o', 'ỏ': 'o', 'õ': 'o', 'ọ': 'o',
        'ô': 'o', 'ố': 'o', 'ồ': 'o', 'ổ': 'o', 'ỗ': 'o', 'ộ': 'o',
        'ơ': 'o', 'ớ': 'o', 'ờ': 'o', 'ở': 'o', 'ỡ': 'o', 'ợ': 'o',
        'ú': 'u', 'ù': 'u', 'ủ': 'u', 'ũ': 'u', 'ụ': 'u',
        'ư': 'u', 'ứ': 'u', 'ừ': 'u', 'ử': 'u', 'ữ': 'u', 'ự': 'u',
        'ý': 'y', 'ỳ': 'y', 'ỷ': 'y', 'ỹ': 'y', 'ỵ': 'y'
    }
    for char, replacement in replacements.items():
        text = text.replace(char, replacement)

    # Giữ lại chữ, số và khoảng trắng
    text = re.sub(r'[^a-z0-9\s]', ' ', text)
    # Thay thế nhiều khoảng trắng bằng một
    text = re.sub(r'\s+', ' ', text).strip()

    return text

if __name__ == '__main__':
    # Test các hàm
    print("--- Testing load_config ---")
    config = load_config()
    if config:
        print(f"Max posts to scan: {config['settings']['max_posts_to_scan_per_group']}")

    print("\n--- Testing load_products ---")
    products = load_products(Path(__file__).parent.parent / "data" / "products.csv")
    if products:
        print(f"Loaded {len(products)} products. First product: {products[0]['name']}")
        print(f"Aliases for first product: {products[0]['aliases']}")

    print("\n--- Testing normalize_text ---")
    vietnamese_text = "Cần mua MÁY XAY SINH TỐ đa năng, giá tốt!!!"
    normalized = normalize_text(vietnamese_text)
    print(f"Original: '{vietnamese_text}'")
    print(f"Normalized: '{normalized}'")