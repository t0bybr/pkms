import os, sqlite3, time, shutil, pathlib
INDEX_DIR=os.environ.get('INDEX_DIR','/app/index')
DATA_DIR=os.environ.get('DATA_DIR','/app/data')
STATE_DB=os.path.join(INDEX_DIR, 'ingest_state.sqlite')
os.makedirs(os.path.dirname(STATE_DB), exist_ok=True)

class IndexTracker:
    def __init__(self, db_path=STATE_DB):
        self.db_path=db_path
        self._init()
    def _conn(self):
        con=sqlite3.connect(self.db_path, timeout=30, check_same_thread=False)
        con.execute("PRAGMA busy_timeout=30000")
        return con
    def _init(self):
        con=self._conn()
        cur=con.cursor()
        cur.execute("CREATE TABLE IF NOT EXISTS files(path TEXT PRIMARY KEY, checksum TEXT, updated_at INTEGER)")
        cur.execute("CREATE TABLE IF NOT EXISTS retries(path TEXT PRIMARY KEY, tries INTEGER DEFAULT 0)")
        try:
            cur.execute("PRAGMA journal_mode=WAL")
        except Exception:
            pass
        con.commit(); con.close()
    def is_processed(self, path:str, checksum:str)->bool:
        con=self._conn(); cur=con.cursor()
        cur.execute("SELECT checksum FROM files WHERE path=?", (path,))
        row=cur.fetchone(); con.close()
        return bool(row and row[0]==checksum)
    def mark_processed(self, path:str, checksum:str):
        now=int(time.time())
        con=self._conn(); cur=con.cursor()
        cur.execute("INSERT OR REPLACE INTO files(path,checksum,updated_at) VALUES (?,?,?)", (path,checksum,now))
        cur.execute("DELETE FROM retries WHERE path=?", (path,))
        con.commit(); con.close()
    def add_retry(self, path:str):
        con=self._conn(); cur=con.cursor()
        try:
            cur.execute("INSERT INTO retries(path,tries) VALUES(?,1)", (path,))
        except sqlite3.IntegrityError:
            cur.execute("UPDATE retries SET tries=tries+1 WHERE path=?", (path,))
        cur.execute("SELECT tries FROM retries WHERE path=?", (path,))
        tries=cur.fetchone()[0]
        con.commit(); con.close()
        return tries

tracker=IndexTracker()
RETRY_DIR=os.path.join(DATA_DIR,'inbox','_retry')
DEAD_DIR=os.path.join(DATA_DIR,'inbox','_deadletter')
for d in (RETRY_DIR, DEAD_DIR): os.makedirs(d, exist_ok=True)

def move_retry(path:str, tries:int):
    dst=os.path.join(RETRY_DIR, pathlib.Path(path).name + f".retry{tries}")
    shutil.move(path, dst)
    return dst

def move_dead(path:str):
    dst=os.path.join(DEAD_DIR, pathlib.Path(path).name)
    shutil.move(path, dst)
    return dst
