#!/usr/bin/env python3
"""
Script kiểm tra session Facebook và đăng nhập lại nếu cần
"""
import asyncio
import logging
from pathlib import Path
from playwright.async_api import async_playwright

# Thiết lập logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

async def check_session(account_id: str):
    """Kiểm tra session Facebook có còn hoạt động không"""
    sessions_dir = Path("sessions") / account_id
    storage_state_path = sessions_dir / "storage_state.json"
    
    if not storage_state_path.exists():
        logging.error(f"Không tìm thấy session cho tài khoản '{account_id}'")
        return False
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(
            storage_state=storage_state_path,
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = await context.new_page()
        
        try:
            # Truy cập Facebook
            await page.goto("https://www.facebook.com", timeout=30000)
            await asyncio.sleep(3)
            
            # Kiểm tra xem có đăng nhập không
            login_indicators = [
                'input[name="email"]',
                'input[name="pass"]',
                'button[data-testid="royal_login_button"]',
                'div[data-testid="login_form"]'
            ]
            
            is_logged_in = True
            for indicator in login_indicators:
                if await page.locator(indicator).count() > 0:
                    is_logged_in = False
                    break
            
            if is_logged_in:
                logging.info(f"✅ Session của tài khoản '{account_id}' vẫn hoạt động")
                
                # Kiểm tra thêm bằng cách truy cập profile
                try:
                    await page.goto("https://www.facebook.com/me", timeout=15000)
                    await asyncio.sleep(2)
                    
                    # Kiểm tra xem có bị redirect về trang login không
                    if "login" in page.url or "facebook.com/me" not in page.url:
                        logging.warning(f"⚠️ Session có thể đã hết hạn cho tài khoản '{account_id}'")
                        return False
                    else:
                        logging.info(f"✅ Xác nhận session hoạt động bình thường")
                        return True
                        
                except Exception as e:
                    logging.warning(f"⚠️ Không thể xác nhận session: {e}")
                    return False
            else:
                logging.warning(f"⚠️ Tài khoản '{account_id}' chưa đăng nhập")
                return False
                
        except Exception as e:
            logging.error(f"❌ Lỗi khi kiểm tra session: {e}")
            return False
        finally:
            await browser.close()

async def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Kiểm tra session Facebook")
    parser.add_argument("--account", required=True, help="ID tài khoản cần kiểm tra")
    args = parser.parse_args()
    
    is_valid = await check_session(args.account)
    
    if not is_valid:
        print(f"\n🔧 Để đăng nhập lại, chạy lệnh:")
        print(f"py -m src.login_helper --account {args.account}")
        return 1
    else:
        print(f"\n✅ Tài khoản '{args.account}' sẵn sàng sử dụng")
        return 0

if __name__ == "__main__":
    exit(asyncio.run(main()))
