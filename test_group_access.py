#!/usr/bin/env python3
"""
Script kiểm tra quyền truy cập group Facebook
"""
import asyncio
import logging
from pathlib import Path
from playwright.async_api import async_playwright, TimeoutError

# Thiết lập logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

async def test_group_access(account_id: str, group_id: str):
    """Kiểm tra quyền truy cập một group cụ thể"""
    sessions_dir = Path("sessions") / account_id
    storage_state_path = sessions_dir / "storage_state.json"
    
    if not storage_state_path.exists():
        logging.error(f"Không tìm thấy session cho tài khoản '{account_id}'")
        return False
    
    group_url = f"https://www.facebook.com/groups/{group_id}/"
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(
            storage_state=storage_state_path,
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={'width': 1920, 'height': 1080}
        )
        page = await context.new_page()
        
        try:
            logging.info(f"Đang kiểm tra group: {group_url}")
            await page.goto(group_url, wait_until="networkidle", timeout=60000)
            await asyncio.sleep(5)  # Chờ trang load hoàn toàn
            
            # Kiểm tra các trường hợp khác nhau
            page_title = await page.title()
            current_url = page.url
            
            logging.info(f"Tiêu đề trang: {page_title}")
            logging.info(f"URL hiện tại: {current_url}")
            
            # Kiểm tra xem có bị redirect không
            if "login" in current_url:
                logging.error("❌ Bị redirect về trang đăng nhập - Session đã hết hạn")
                return False
            
            # Kiểm tra các thông báo lỗi
            error_messages = [
                'div[data-testid="error"]',
                'div[role="alert"]',
                'div[class*="error"]',
                'div[class*="blocked"]',
                'div[class*="restricted"]',
                'div[class*="unavailable"]'
            ]
            
            for error_selector in error_messages:
                if await page.locator(error_selector).count() > 0:
                    error_text = await page.locator(error_selector).first.inner_text()
                    logging.error(f"❌ Group bị chặn: {error_text}")
                    return False
            
            # Kiểm tra yêu cầu tham gia group
            join_buttons = await page.locator('button:has-text("Tham gia"), button:has-text("Join"), button:has-text("Request to join")').count()
            if join_buttons > 0:
                logging.warning("⚠️ Group yêu cầu tham gia trước khi xem feed")
                return False
            
            # Kiểm tra feed có tồn tại không
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
                    await page.wait_for_selector(selector, timeout=10000)
                    logging.info(f"✅ Tìm thấy feed với selector: {selector}")
                    feed_found = True
                    break
                except TimeoutError:
                    continue
            
            if feed_found:
                # Kiểm tra xem có bài viết không
                post_selectors = [
                    'div[role="article"]',
                    'div[data-pagelet*="FeedUnit"]',
                    'div[data-testid="fbfeed_story"]',
                    'div[aria-label*="story"]'
                ]
                
                posts_count = 0
                for selector in post_selectors:
                    posts_count = await page.locator(selector).count()
                    if posts_count > 0:
                        logging.info(f"✅ Tìm thấy {posts_count} bài viết với selector: {selector}")
                        break
                
                if posts_count == 0:
                    logging.warning("⚠️ Feed tồn tại nhưng không có bài viết nào")
                    return False
                else:
                    logging.info(f"✅ Group {group_id} có thể truy cập và có {posts_count} bài viết")
                    return True
            else:
                logging.error(f"❌ Không thể tìm thấy feed của group {group_id}")
                return False
                
        except TimeoutError:
            logging.error(f"❌ Timeout khi truy cập group {group_id}")
            return False
        except Exception as e:
            logging.error(f"❌ Lỗi khi kiểm tra group {group_id}: {e}")
            return False
        finally:
            await browser.close()

async def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Kiểm tra quyền truy cập group Facebook")
    parser.add_argument("--account", required=True, help="ID tài khoản")
    parser.add_argument("--group", required=True, help="ID group cần kiểm tra")
    args = parser.parse_args()
    
    success = await test_group_access(args.account, args.group)
    
    if success:
        print(f"\n✅ Group {args.group} có thể truy cập bình thường")
        return 0
    else:
        print(f"\n❌ Không thể truy cập group {args.group}")
        print("💡 Gợi ý:")
        print("1. Kiểm tra session: py check_session.py --account " + args.account)
        print("2. Đăng nhập lại: py -m src.login_helper --account " + args.account)
        print("3. Kiểm tra group ID có đúng không")
        print("4. Kiểm tra tài khoản có quyền truy cập group không")
        return 1

if __name__ == "__main__":
    exit(asyncio.run(main()))
