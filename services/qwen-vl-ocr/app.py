import argparse, io, logging, os
from fastapi import FastAPI, UploadFile, File, Form, Header, HTTPException
from fastapi.responses import JSONResponse
from PIL import Image
from typing import Optional
import torch
from transformers import AutoProcessor, AutoModelForVision2Seq

app = FastAPI()
Image.MAX_IMAGE_PIXELS = int(os.getenv('MAX_IMAGE_PIXELS','178956970'))
API_KEY=os.getenv('API_KEY')
QWEN_MODEL=os.getenv('QWEN_MODEL','Qwen/Qwen2.5-VL-7B-Instruct')

class QwenVLGateway:
    def __init__(self, model_id: str):
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.processor = AutoProcessor.from_pretrained(model_id, trust_remote_code=True)
        self.model = AutoModelForVision2Seq.from_pretrained(
            model_id, torch_dtype=torch.float16 if self.device=='cuda' else torch.float32,
            trust_remote_code=True
        ).to(self.device)
    def ocr(self, image: Image.Image, mode: str = "text"):
        prompt = (
            "<|im_start|>system\nExtrahiere ausschließlich den im Bild vorhandenen Text in natürlicher "
            "Lesereihenfolge. Keine Erklärungen, keine Halluzinationen.<|im_end|>\n"
            "<|im_start|>user\nOCR bitte.<|im_end|>\n<|im_start|>assistant\n"
        )
        inputs = self.processor(images=image, text=prompt, return_tensors="pt").to(self.device)
        generated_ids = self.model.generate(**inputs, max_new_tokens=2048)
        out = self.processor.batch_decode(generated_ids, skip_special_tokens=True)[0]
        return {"text": out.strip()}

qwen: Optional[QwenVLGateway] = None

@app.on_event("startup")
async def init_model():
    global qwen
    logging.basicConfig(level=os.getenv('LOG_LEVEL','INFO'), format='%(asctime)s %(levelname)s %(name)s %(message)s')
    logging.getLogger('qwen-vl-ocr').info("loading model id=%s", QWEN_MODEL)
    qwen = QwenVLGateway(QWEN_MODEL)

@app.post("/ocr")
async def ocr_endpoint(file: UploadFile = File(...), mode: str = Form("text"), x_api_key: str = Header(None)):
    if API_KEY and x_api_key != API_KEY:
        raise HTTPException(401, "unauthorized")
    max_mb = int(os.getenv('MAX_UPLOAD_MB', '10'))
    MAX_SIZE = max_mb * 1024 * 1024
    img_bytes = await file.read(MAX_SIZE + 1)
    if len(img_bytes) > MAX_SIZE:
        return JSONResponse({"error":"file too large"}, status_code=413)
    img = Image.open(io.BytesIO(img_bytes)).convert("RGB")
    result = qwen.ocr(img, mode=mode)
    logging.getLogger('qwen-vl-ocr').info("ocr len=%d", len(result.get('text','')))
    return JSONResponse(result)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", default=8001, type=int)
    parser.add_argument("--model", default="Qwen/Qwen2.5-VL-7B-Instruct")
    args = parser.parse_args()
    import uvicorn
    uvicorn.run("app:app", host=args.host, port=args.port, reload=False)
