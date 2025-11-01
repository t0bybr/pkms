import re, os, json
from datetime import datetime, timedelta
from services.ingest_worker.common.ics import make_ics

DATE_RX=r"(?:(?:31|30|[0-2]\d)\.(?:0\d|1[0-2])\.\d{4})"
AMOUNT_RX=r"([+-]?\d{1,3}(?:\.\d{3})*,\d{2})\s*(?:EUR|€)"
STNR_RX=r"\b\d{2}\/?\d{3}\/?\d{5}\b"
IBAN_RX=r"\b[A-Z]{2}\d{2}[A-Z0-9]{10,30}\b"
EURO=lambda s: float(s.replace('.','').replace(',','.'))

def parse_finanzamt(text: str):
    d = {}
    dates = re.findall(DATE_RX, text)
    if dates:
        try:
            d['bescheiddatum']= datetime.strptime(dates[0], '%d.%m.%Y').strftime('%Y-%m-%d')
        except: pass
    m=re.search(AMOUNT_RX, text); d['betrag_eur']= EURO(m.group(1)) if m else None
    m=re.search(STNR_RX, text); d['steuernummer']= m.group(0) if m else None
    m=re.search(IBAN_RX, text); d['iban_masked']= (m.group(0)[:2] + '** **** **** ' + m.group(0)[-4:]) if m else None
    if 'Bescheid' in text: d['doc_type']='bescheid'
    elif 'Mahnung' in text or 'Erinnerung' in text: d['doc_type']='mahnung'
    else: d['doc_type']='mitteilung'
    if d.get('bescheiddatum'):
        base=datetime.strptime(d['bescheiddatum'],'%Y-%m-%d')
        d['einspruchsfrist_bis']=(base+timedelta(days=30)).strftime('%Y-%m-%d')
    return d

def integrate_finanzamt(md_path: str, ocr_text: str):
    meta=parse_finanzamt(ocr_text)
    if not meta: return
    with open(md_path,'r+',encoding='utf-8') as f:
        content=f.read()
        parts=content.split('---\n')
        data=json.loads(parts[1])
        data.update({'doc_domain':'finanzamt', **meta})
        parts[1]=json.dumps(data, ensure_ascii=False, indent=2)+"\n"
        f.seek(0); f.write('---\n'.join(parts)); f.truncate()
    if meta.get('einspruchsfrist_bis'):
        dt=datetime.strptime(meta['einspruchsfrist_bis'],'%Y-%m-%d')
        ics=make_ics('Einspruchsfrist Finanzamt', dt, description=os.path.basename(md_path))
        ics_path=os.path.splitext(md_path)[0]+'.ics'
        with open(ics_path,'w',encoding='utf-8') as f: f.write(ics)
