"""Task Scheduler / cron ile periyodik (örn. her 15 dk) çalıştır: python buffer_scheduler.py"""

from dotenv import load_dotenv

load_dotenv()

from scheduler_core import fill_queue

if __name__ == "__main__":
    for line in fill_queue():
        print(line)
