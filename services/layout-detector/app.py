import argparse, io, logging, os
from fastapi import FastAPI, UploadFile, File, Header, HTTPException
from fastapi.responses import JSONResponse
from ultralytics import YOLO
from PIL import Image

app = FastAPI()
model = None
CLASSES = ["text","title","list","table","figure"]
Image.MAX_IMAGE_PIXELS = int(os.getenv('MAX_IMAGE_PIXELS','178956970'))
API_KEY=os.getenv('API_KEY')

@app.on_event("startup")
async def load_model():
    global model, args
    logging.basicConfig(level=os.getenv('LOG_LEVEL','INFO'), format='%(asctime)s %(levelname)s %(name)s %(message)s')
    log=logging.getLogger('layout-detector')
    model = YOLO(args.weights)
    log.info("model_loaded weights=%s", args.weights)

@app.post("/detect")
async def detect(file: UploadFile = File(...), x_api_key: str = Header(None)):
    if API_KEY and x_api_key != API_KEY:
        raise HTTPException(401, "unauthorized")
    max_mb = int(os.getenv('MAX_UPLOAD_MB', '10'))
    MAX_SIZE = max_mb * 1024 * 1024
    img_bytes = await file.read(MAX_SIZE + 1)
    if len(img_bytes) > MAX_SIZE:
        return JSONResponse({"error":"file too large"}, status_code=413)
    img = Image.open(io.BytesIO(img_bytes)).convert("RGB")
    res = model.predict(img, imgsz=1280, conf=0.25, verbose=False)[0]
    bboxes=[]
    for b in res.boxes:
        x1,y1,x2,y2 = b.xyxy[0].tolist()
        cls = int(b.cls[0].item())
        conf = float(b.conf[0].item())
        bboxes.append({"bbox":[x1,y1,x2-x1,y2-y1], "cls": CLASSES[cls] if cls < len(CLASSES) else str(cls), "conf": conf})
    logging.getLogger('layout-detector').info("detect boxes=%d", len(bboxes))
    return JSONResponse({"bboxes": bboxes})

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", default=8002, type=int)
    parser.add_argument("--weights", default="/models/doclaynet.pt")
    args = parser.parse_args()
    import uvicorn
    uvicorn.run("app:app", host=args.host, port=args.port, reload=False)
