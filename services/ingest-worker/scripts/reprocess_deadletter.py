import os, shutil, pathlib
DATA_DIR=os.environ.get('DATA_DIR','/app/data') or '/app/data'
DEAD=os.path.join(DATA_DIR,'inbox','_deadletter')
INBOX=os.path.join(DATA_DIR,'inbox')
os.makedirs(DEAD, exist_ok=True); os.makedirs(INBOX, exist_ok=True)
cnt=0
for entry in os.scandir(DEAD):
    if not entry.is_file(): continue
    src=entry.path
    dst=os.path.join(INBOX, pathlib.Path(src).name.replace('.retry','').replace('.dead',''))
    print(f"→ {src} -> {dst}")
    shutil.move(src, dst); cnt+=1
print(f"Re-queued {cnt} file(s)")
