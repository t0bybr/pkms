from datetime import datetime
def make_ics(summary: str, dt: datetime, description: str = "", location: str = ""):
    dtstamp = datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')
    dtstart = dt.strftime('%Y%m%dT%H%M%S')
    uid = f"{dtstart}-{abs(hash(summary+description))}@pkms"
    ics = ("BEGIN:VCALENDAR\nVERSION:2.0\nPRODID:-//PKMS//DE\n"
           "BEGIN:VEVENT\n"
           f"DTSTAMP:{dtstamp}\nDTSTART:{dtstart}\nSUMMARY:{summary}\n"
           f"DESCRIPTION:{description}\nLOCATION:{location}\nUID:{uid}\n"
           "END:VEVENT\nEND:VCALENDAR\n")
    return ics

