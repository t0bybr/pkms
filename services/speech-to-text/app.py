import argparse, tempfile, subprocess, os, logging
from fastapi import FastAPI, File, UploadFile, Header, HTTPException
from fastapi.responses import JSONResponse
import whisper

app = FastAPI()
model = None

@app.on_event("startup")
def load_model():
    global model
    model = whisper.load_model("small")
    logging.basicConfig(level=os.getenv('LOG_LEVEL','INFO'), format='%(asctime)s %(levelname)s %(name)s %(message)s')
    logging.getLogger('speech-to-text').info("model_loaded name=small")

def _to_wav(bytes_buf: bytes) -> str:
    fd, raw = tempfile.mkstemp(suffix=".bin"); os.write(fd, bytes_buf); os.close(fd)
    wav = raw + ".wav"
    subprocess.run(["ffmpeg","-loglevel","error","-y","-i",raw,"-ac","1","-ar","16000", wav], check=True, timeout=30)
    os.remove(raw)
    return wav

@app.post("/transcribe")
API_KEY=os.getenv('API_KEY')

async def transcribe(file: UploadFile = File(...), x_api_key: str = Header(None)):
    if API_KEY and x_api_key != API_KEY:
        return JSONResponse({"error":"unauthorized"}, status_code=401)
    max_mb = int(os.getenv('MAX_UPLOAD_MB', '10'))
    MAX_SIZE = max_mb * 1024 * 1024
    data = await file.read(MAX_SIZE + 1)
    if len(data) > MAX_SIZE:
        return JSONResponse({"error":"file too large"}, status_code=413)
    wav = _to_wav(data)
    try:
        result = model.transcribe(wav, language="de")
        text = result.get("text"," ").strip()
        logging.getLogger('speech-to-text').info("transcribe len=%d", len(text))
        return JSONResponse({"text": text})
    finally:
        if os.path.exists(wav): os.remove(wav)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", default=8004, type=int)
    args = parser.parse_args()
    import uvicorn
    uvicorn.run("app:app", host=args.host, port=args.port, reload=False)
