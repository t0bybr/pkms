import os, time, logging, errno, hashlib
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from router import dispatch
from common.state import tracker, move_retry, move_dead
from common.utils import sha256_file

DATA_DIR=os.environ.get('DATA_DIR','/app/data')
INBOX=os.path.join(DATA_DIR,'inbox')
MAX_RETRIES=3

log = logging.getLogger("ingest-worker")
log.setLevel(os.getenv('LOG_LEVEL','INFO'))
_fmt=logging.Formatter('%(asctime)s %(levelname)s %(name)s %(message)s')
_sh=logging.StreamHandler(); _sh.setFormatter(_fmt); log.addHandler(_sh)
try:
    _logdir=os.path.join(os.environ.get('INDEX_DIR','/app/index'),'logs')
    os.makedirs(_logdir, exist_ok=True)
    _fh=logging.FileHandler(os.path.join(_logdir,'ingest.log'))
    _fh.setFormatter(_fmt); log.addHandler(_fh)
except Exception:
    pass

class Handler(FileSystemEventHandler):
    def on_created(self, event):
        if event.is_directory: return
        path=event.src_path
        time.sleep(0.2)
        try:
            checksum = sha256_file(path)
        except (FileNotFoundError, PermissionError):
            return
        if tracker.is_processed(path, checksum):
            return
        lockdir=os.path.join(os.environ.get('INDEX_DIR','/app/index'),'locks')
        os.makedirs(lockdir, exist_ok=True)
        lockname=hashlib.sha256(path.encode()).hexdigest()+'.lock'
        lockfile=os.path.join(lockdir, lockname)
        fd=None
        try:
            fd=os.open(lockfile, os.O_CREAT|os.O_EXCL|os.O_RDWR)
        except FileExistsError:
            return
        try:
            dispatch(path)
            tracker.mark_processed(path, checksum)
            log.info("ingested file=%s", path)
        except Exception:
            tries = tracker.add_retry(path)
            if tries>=MAX_RETRIES:
                move_dead(path)
                log.error("deadletter file=%s tries=%s", path, tries, exc_info=True)
            else:
                move_retry(path, tries)
                log.warning("retry file=%s tries=%s", path, tries, exc_info=True)
        finally:
            try:
                if fd is not None:
                    os.close(fd)
                if os.path.exists(lockfile):
                    os.unlink(lockfile)
            except Exception:
                pass

if __name__=="__main__":
    os.makedirs(INBOX, exist_ok=True)
    observer=Observer(); observer.schedule(Handler(), INBOX, recursive=True)
    observer.start()
    try:
        while True: time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()
