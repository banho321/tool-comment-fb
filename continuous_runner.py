#!/usr/bin/env python3
"""
Continuous Runner - Chạy bot liên tục với monitoring
"""
import asyncio
import logging
import time
import signal
import sys
import subprocess
from datetime import datetime

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
        """Run one complete cycle by calling main.py as a subprocess with a timeout."""
        # Set a timeout slightly shorter than the run interval to prevent overlaps
        timeout_seconds = self.interval_minutes * 60 - 30
        if timeout_seconds <= 0:
            timeout_seconds = 300 # Default to 5 minutes if interval is too short

        try:
            self.run_count += 1
            self.last_run = datetime.now()

            logging.info(f"=== STARTING CYCLE #{self.run_count} ===")
            logging.info(f"Account: {self.account_id}, Timeout: {timeout_seconds}s")
            
            command = [sys.executable, 'main.py', '--account', self.account_id]

            # Run the subprocess with a timeout
            process = await asyncio.create_subprocess_exec(
                *command, stdout=subprocess.PIPE, stderr=subprocess.PIPE
            )

            stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=timeout_seconds)

            if process.returncode == 0:
                logging.info(f"main.py executed successfully.")
                if stdout:
                    logging.info(f"stdout:\n{stdout.decode(errors='ignore')}")
            else:
                logging.error(f"main.py exited with error code {process.returncode}")
                if stderr:
                    logging.error(f"stderr:\n{stderr.decode(errors='ignore')}")

        except asyncio.TimeoutError:
            logging.error(f"Cycle #{self.run_count} timed out after {timeout_seconds} seconds. Terminating process.")
            process.terminate()
            await process.wait()
            logging.info("Process terminated. The runner will continue to the next cycle.")
        except Exception as e:
            logging.error(f"An unexpected error occurred in cycle #{self.run_count}: {e}")
        finally:
             logging.info(f"=== COMPLETED CYCLE #{self.run_count} ===")

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
                    # Sleep in a way that respects the stop signal
                    for _ in range(self.interval_minutes * 60):
                        if not self.running:
                            break
                        await asyncio.sleep(1)

            except KeyboardInterrupt:
                logging.info("Received keyboard interrupt, stopping...")
                self.running = False
            except Exception as e:
                logging.error(f"Unexpected error in continuous loop: {e}")
                logging.info("Waiting 5 minutes before retry...")
                await asyncio.sleep(300)

        logging.info("Continuous runner stopped")

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
