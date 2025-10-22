import asyncio
from playwright.async_api import async_playwright
from pathlib import Path
import argparse
import logging

# Thiết lập logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

async def run_login_helper(account_id: str):
    """
    Mở trình duyệt để người dùng đăng nhập thủ công và lưu lại session.
    """
    sessions_dir = Path(__file__).parent.parent / "sessions"
    account_dir = sessions_dir / account_id
    account_dir.mkdir(exist_ok=True)
    storage_state_path = account_dir / "storage_state.json"

    logging.info(f"Sử dụng thư mục session cho tài khoản '{account_id}': {account_dir}")

    async with async_playwright() as p:
        # Use Firefox instead of Chromium for better Facebook compatibility
        browser = await p.firefox.launch(
            headless=False,
            args=[
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-dev-shm-usage'
            ]
        )
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/121.0",
            viewport={'width': 1920, 'height': 1080}
        )
        page = await context.new_page()

        await page.goto("https://www.facebook.com")

        print("\n" + "="*80)
        print("TRÌNH DUYỆT ĐÃ MỞ")
        print(f"Vui lòng đăng nhập vào tài khoản Facebook dành cho '{account_id}'.")
        print("Sau khi đăng nhập thành công, quay lại cửa sổ dòng lệnh này và nhấn Enter.")
        print("="*80 + "\n")

        # Chờ người dùng nhấn Enter
        await asyncio.get_event_loop().run_in_executor(
            None, input, ">> Nhấn Enter để tiếp tục sau khi đã đăng nhập...")

        # Lưu lại storage state (cookies, local storage, etc.)
        await context.storage_state(path=storage_state_path)

        logging.info(f"Đã lưu session thành công vào file: {storage_state_path}")

        await browser.close()

def main():
    parser = argparse.ArgumentParser(
        description="Công cụ hỗ trợ đăng nhập Facebook và lưu session.",
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument(
        "--account",
        required=True,
        help="ID định danh cho tài khoản (ví dụ: 'acc1', 'my_personal_account')."
    )
    args = parser.parse_args()

    try:
        asyncio.run(run_login_helper(args.account))
    except KeyboardInterrupt:
        logging.info("Đã dừng chương trình.")
    except Exception as e:
        logging.error(f"Đã xảy ra lỗi không mong muốn: {e}")

if __name__ == "__main__":
    main()