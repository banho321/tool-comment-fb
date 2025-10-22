#!/usr/bin/env python3
"""
Bot Monitor - Monitor and restart bot if needed
"""
import subprocess
import time
import logging
import psutil
import os
from datetime import datetime

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('monitor.log'),
        logging.StreamHandler()
    ]
)

class BotMonitor:
    def __init__(self, account_id: str, check_interval: int = 60):
        self.account_id = account_id
        self.check_interval = check_interval
        self.process = None
        self.restart_count = 0
        self.max_restarts = 10
        
    def is_bot_running(self):
        """Check if bot process is running"""
        try:
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                if proc.info['cmdline']:
                    cmdline = ' '.join(proc.info['cmdline'])
                    if 'continuous_runner.py' in cmdline and self.account_id in cmdline:
                        return True, proc.info['pid']
            return False, None
        except Exception as e:
            logging.error(f"Error checking bot process: {e}")
            return False, None
    
    def start_bot(self):
        """Start the bot process"""
        try:
            logging.info(f"Starting bot for account: {self.account_id}")
            self.process = subprocess.Popen([
                'python', 'continuous_runner.py', 
                '--account', self.account_id, 
                '--interval', '30'
            ])
            self.restart_count += 1
            logging.info(f"Bot started with PID: {self.process.pid}")
            return True
        except Exception as e:
            logging.error(f"Error starting bot: {e}")
            return False
    
    def stop_bot(self):
        """Stop the bot process"""
        try:
            if self.process:
                self.process.terminate()
                self.process.wait(timeout=10)
                logging.info("Bot stopped gracefully")
            return True
        except Exception as e:
            logging.error(f"Error stopping bot: {e}")
            return False
    
    def restart_bot(self):
        """Restart the bot process"""
        logging.info("Restarting bot...")
        self.stop_bot()
        time.sleep(5)
        return self.start_bot()
    
    def monitor(self):
        """Main monitoring loop"""
        logging.info(f"Starting bot monitor for account: {self.account_id}")
        logging.info(f"Check interval: {self.check_interval} seconds")
        
        while True:
            try:
                is_running, pid = self.is_bot_running()
                
                if not is_running:
                    logging.warning("Bot is not running, attempting to start...")
                    
                    if self.restart_count >= self.max_restarts:
                        logging.error(f"Max restarts ({self.max_restarts}) reached. Stopping monitor.")
                        break
                    
                    if self.start_bot():
                        logging.info("Bot started successfully")
                    else:
                        logging.error("Failed to start bot")
                else:
                    logging.info(f"Bot is running (PID: {pid})")
                
                # Reset restart count if bot has been running for a while
                if is_running and self.restart_count > 0:
                    self.restart_count = max(0, self.restart_count - 1)
                
                time.sleep(self.check_interval)
                
            except KeyboardInterrupt:
                logging.info("Monitor stopped by user")
                break
            except Exception as e:
                logging.error(f"Monitor error: {e}")
                time.sleep(30)  # Wait before retry
        
        # Cleanup
        self.stop_bot()
        logging.info("Monitor stopped")

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Bot Monitor")
    parser.add_argument("--account", required=True, help="Account ID")
    parser.add_argument("--interval", type=int, default=60, help="Check interval in seconds")
    
    args = parser.parse_args()
    
    monitor = BotMonitor(args.account, args.interval)
    monitor.monitor()

if __name__ == "__main__":
    main()
