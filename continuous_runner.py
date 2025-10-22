#!/usr/bin/env python3
"""
Continuous Runner - Chạy bot liên tục với monitoring
"""
import asyncio
import logging
import time
import signal
import sys
from datetime import datetime
from pathlib import Path

# Import main modules
from main import main as run_main
from src.utils import load_config

# Setup logging
logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('continuous_runner.log'),
        logging.StreamHandler()
    ]
)

class ContinuousRunner:
    def __init__(self, account_id: str, interval_minutes: int = 30):
        self.account_id = account_id
        self.interval_minutes = interval_minutes
        self.running = True
        self.run_count = 0
        self.last_run = None
        
        # Setup signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully"""
        logging.info(f"Received signal {signum}, shutting down gracefully...")
        self.running = False
        
    async def run_cycle(self):
        """Run one complete cycle"""
        try:
            self.run_count += 1
            self.last_run = datetime.now()
            
            logging.info(f"=== STARTING CYCLE #{self.run_count} ===")
            logging.info(f"Account: {self.account_id}")
            logging.info(f"Time: {self.last_run}")
            
            # Run main application
            await run_main_async(self.account_id)
            
            logging.info(f"=== COMPLETED CYCLE #{self.run_count} ===")
            
        except Exception as e:
            logging.error(f"Error in cycle #{self.run_count}: {e}")
            logging.error("Continuing to next cycle...")
    
    async def run_continuous(self):
        """Run continuously with specified interval"""
        logging.info(f"Starting continuous runner for account: {self.account_id}")
        logging.info(f"Interval: {self.interval_minutes} minutes")
        logging.info("Press Ctrl+C to stop")
        
        while self.running:
            try:
                await self.run_cycle()
                
                if self.running:
                    logging.info(f"Waiting {self.interval_minutes} minutes until next run...")
                    await asyncio.sleep(self.interval_minutes * 60)
                    
            except KeyboardInterrupt:
                logging.info("Received keyboard interrupt, stopping...")
                break
            except Exception as e:
                logging.error(f"Unexpected error: {e}")
                logging.info("Waiting 5 minutes before retry...")
                await asyncio.sleep(300)  # Wait 5 minutes on error
        
        logging.info("Continuous runner stopped")

async def run_main_async(account_id: str):
    """Run main application asynchronously"""
    import argparse
    
    # Create mock args for main
    class Args:
        def __init__(self, account):
            self.account = account
            self.groups_file = "data/groups.txt"
            self.products_file = "data/products.csv"
            self.templates_file = "data/templates.txt"
            self.skip_crawler = False
            self.skip_matcher = False
            self.skip_commenter = False
            self.dry_run = False
    
    args = Args(account_id)
    
    # Run main logic
    from src.utils import load_config, load_text_file, load_products
    import src.db as db
    from src.crawler import FacebookCrawler
    from src.matcher import PostMatcher
    from src.commenter import FacebookCommenter
    
    logging.info("==================== BOT BẮT ĐẦU ====================")
    logging.info("Đang tải cấu hình và dữ liệu...")
    
    # Load config
    config = load_config()
    if not config:
        raise Exception("Không thể tải cấu hình")
    
    # Initialize database
    db.initialize_db()
    
    # Load data
    groups = load_text_file(args.groups_file)
    products = load_products(args.products_file)
    templates = load_text_file(args.templates_file)
    
    if not groups:
        raise Exception("Không có group nào để quét")
    if not products:
        raise Exception("Không có sản phẩm nào")
    if not templates:
        raise Exception("Không có mẫu bình luận nào")
    
    # Step 1: Crawler
    if not args.skip_crawler:
        logging.info("-------------------- BƯỚC 1: CRAWLER --------------------")
        crawler = FacebookCrawler(account_id=args.account, groups=groups, config=config)
        await crawler.run()
    else:
        logging.info("Bỏ qua bước Crawler")
    
    # Step 2: Matcher
    if not args.skip_matcher:
        logging.info("-------------------- BƯỚC 2: MATCHER --------------------")
        matcher = PostMatcher(config=config, products=products)
        matcher.run()
    else:
        logging.info("Bỏ qua bước Matcher")
    
    # Step 3: Commenter
    if not args.skip_commenter and not args.dry_run:
        logging.info("-------------------- BƯỚC 3: COMMENTER --------------------")
        commenter = FacebookCommenter(
            account_id=args.account,
            config=config,
            products=products,
            templates=templates
        )
        await commenter.run()
    else:
        logging.info("Bỏ qua bước Commenter")
    
    logging.info("==================== BOT KẾT THÚC ====================")

async def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Continuous Facebook Bot Runner")
    parser.add_argument("--account", required=True, help="Account ID")
    parser.add_argument("--interval", type=int, default=30, help="Interval in minutes (default: 30)")
    parser.add_argument("--once", action="store_true", help="Run once and exit")
    
    args = parser.parse_args()
    
    runner = ContinuousRunner(args.account, args.interval)
    
    if args.once:
        logging.info("Running once and exiting...")
        await runner.run_cycle()
    else:
        await runner.run_continuous()

if __name__ == "__main__":
    asyncio.run(main())
