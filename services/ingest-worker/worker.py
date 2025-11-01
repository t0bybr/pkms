import os, time
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from services.ingest_worker.router import dispatch
from services.ingest_worker.common.state import tracker, move_retry, move_dead
from services.ingest_worker.common.utils import sha256_file

DATA_DIR=os.environ.get('DATA_DIR','/app/data')
INBOX=os.path.join(DATA_DIR,'inbox')
MAX_RETRIES=3

class Handler(FileSystemEventHandler):
    def on_created(self, event):
        if event.is_directory: return
        path=event.src_path
        time.sleep(0.2)
        checksum = sha256_file(path)
        if tracker.is_processed(path, checksum):
            return
        try:
            dispatch(path)
            tracker.mark_processed(path, checksum)
        except Exception as e:
            tries = tracker.add_retry(path)
            if tries>=MAX_RETRIES:
                move_dead(path)
            else:
                move_retry(path, tries)
            err=os.path.join(os.environ.get('INDEX_DIR','/app/index'),'logs','ingest_errors.log')
            os.makedirs(os.path.dirname(err), exist_ok=True)
            with open(err,'a') as f: f.write(f"{path}: {e}\n")

if __name__=="__main__":
    os.makedirs(INBOX, exist_ok=True)
    observer=Observer(); observer.schedule(Handler(), INBOX, recursive=True)
    observer.start()
    try:
        while True: time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()
