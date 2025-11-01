import argparse, tempfile, subprocess, os
from fastapi import FastAPI, File, UploadFile
from fastapi.responses import JSONResponse
import whisper

app = FastAPI()
model = None

@app.on_event("startup")
def load_model():
    global model
    model = whisper.load_model("small")

def _to_wav(bytes_buf: bytes) -> str:
    fd, raw = tempfile.mkstemp(suffix=".bin"); os.write(fd, bytes_buf); os.close(fd)
    wav = raw + ".wav"
    subprocess.run(["ffmpeg","-loglevel","error","-y","-i",raw,"-ac","1","-ar","16000", wav], check=True)
    os.remove(raw)
    return wav

@app.post("/transcribe")
async def transcribe(file: UploadFile = File(...)):
    data = await file.read()
    wav = _to_wav(data)
    try:
        result = model.transcribe(wav, language="de")
        return JSONResponse({"text": result.get("text"," ").strip()})
    finally:
        if os.path.exists(wav): os.remove(wav)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", default=8004, type=int)
    args = parser.parse_args()
    import uvicorn
    uvicorn.run("app:app", host=args.host, port=args.port, reload=False)
