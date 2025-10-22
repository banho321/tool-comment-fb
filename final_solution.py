#!/usr/bin/env python3
"""
Final Solution - Complete Strategy Change
"""
import asyncio
import logging
import random
from pathlib import Path
from playwright.async_api import async_playwright

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

async def final_solution(account_id: str):
    """Final solution with complete strategy change"""
    sessions_dir = Path("sessions") / account_id
    storage_state_path = sessions_dir / "storage_state.json"
    
    if not storage_state_path.exists():
        logging.error(f"Session not found for account '{account_id}'")
        return False
    
    async with async_playwright() as p:
        # Use Firefox instead of Chromium
        try:
            browser = await p.firefox.launch(
                headless=False,
                args=[
                    '--no-sandbox',
                    '--disable-setuid-sandbox',
                    '--disable-dev-shm-usage'
                ]
            )
        except:
            # Fallback to Chromium with minimal args
            browser = await p.chromium.launch(
                headless=False,
                args=['--no-sandbox', '--disable-dev-shm-usage']
            )
        
        try:
            context = await browser.new_context(
                storage_state=storage_state_path,
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/121.0",
                viewport={'width': 1920, 'height': 1080}
            )
            
            page = await context.new_page()
            
            logging.info("Testing final solution...")
            
            # Step 1: Test basic access
            try:
                await page.goto("https://www.facebook.com", timeout=30000)
                await asyncio.sleep(5)
                
                current_url = page.url
                logging.info(f"Current URL: {current_url}")
                
                if "login" in current_url:
                    logging.warning("Redirected to login - session expired")
                    return False
                else:
                    logging.info("Facebook access successful")
                
            except Exception as e:
                logging.error(f"Error accessing Facebook: {e}")
                return False
            
            # Step 2: Try different group access methods
            group_methods = [
                "https://www.facebook.com/groups/270937463263502/",
                "https://www.facebook.com/groups/270937463263502",
                "https://m.facebook.com/groups/270937463263502/",
                "https://m.facebook.com/groups/270937463263502"
            ]
            
            for method in group_methods:
                try:
                    logging.info(f"Trying method: {method}")
                    
                    # Use different navigation strategy
                    await page.goto(method, wait_until="domcontentloaded", timeout=30000)
                    
                    # Wait for page to load
                    await asyncio.sleep(10)
                    
                    current_url = page.url
                    logging.info(f"URL after navigation: {current_url}")
                    
                    if "login" in current_url:
                        logging.warning("Redirected to login")
                        continue
                    
                    # Check if page loaded successfully
                    try:
                        page_title = await page.title()
                        logging.info(f"Page title: {page_title}")
                        
                        # Check for content
                        body_text = await page.locator('body').inner_text()
                        if body_text and len(body_text) > 100:
                            logging.info(f"Success with method: {method}")
                            return True
                        else:
                            logging.warning(f"No content with method: {method}")
                            continue
                            
                    except Exception as e:
                        logging.error(f"Error checking content with method {method}: {e}")
                        continue
                        
                except Exception as e:
                    logging.error(f"Error with method {method}: {e}")
                    continue
            
            logging.error("All methods failed")
            return False
                
        except Exception as e:
            logging.error(f"Browser error: {e}")
            return False
        finally:
            await browser.close()

async def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Final Solution Test")
    parser.add_argument("--account", required=True, help="Account ID")
    args = parser.parse_args()
    
    success = await final_solution(args.account)
    
    if success:
        print(f"\nFinal solution successful")
        return 0
    else:
        print(f"\nFinal solution failed")
        print("\nRECOMMENDATIONS:")
        print("1. Group may be private/restricted")
        print("2. Try different group ID")
        print("3. Use different account")
        print("4. Consider manual approach")
        return 1

if __name__ == "__main__":
    exit(asyncio.run(main()))
