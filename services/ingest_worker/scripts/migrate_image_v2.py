import os
import lancedb

INDEX_DIR=os.environ.get('INDEX_DIR','/app/index')

def main():
    db=lancedb.connect(INDEX_DIR)
    names=set(db.table_names())
    if 'image_v1' not in names:
        print('no source table image_v1 found; nothing to do')
        return
    src=db.open_table('image_v1')
    if 'image_v2' in names:
        dst=db.open_table('image_v2')
    else:
        dst=db.create_table('image_v2', data=[])

    rows=src.to_list()
    out=[]; moved=0
    for r in rows:
        rec=dict(r)
        if 'embedding' not in rec and 'clip_embedding' in rec:
            rec['embedding']=rec['clip_embedding']
            rec.pop('clip_embedding', None)
            moved+=1
        out.append(rec)
        if len(out)>=1024:
            dst.add(out); out=[]
    if out:
        dst.add(out)
    print(f'migrated {len(rows)} records; updated {moved} with embedding from clip_embedding')

if __name__=='__main__':
    main()

