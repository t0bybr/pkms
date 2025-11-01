import argparse, io, torch, logging, os
from fastapi import FastAPI, UploadFile, File, Form, Header, HTTPException
from fastapi.responses import JSONResponse
from PIL import Image
import open_clip

app = FastAPI()
model=None; preprocess=None; tokenizer=None; device="cuda" if torch.cuda.is_available() else "cpu"
Image.MAX_IMAGE_PIXELS = int(os.getenv('MAX_IMAGE_PIXELS','178956970'))
API_KEY=os.getenv('API_KEY')

@app.on_event("startup")
async def init():
    global model, preprocess, tokenizer, args
    logging.basicConfig(level=os.getenv('LOG_LEVEL','INFO'), format='%(asctime)s %(levelname)s %(name)s %(message)s')
    model, _, preprocess = open_clip.create_model_and_transforms(args.model, pretrained=args.pretrained, device=device)
    tokenizer = open_clip.get_tokenizer(args.model)
    logging.getLogger('clip-embed').info("model_ready name=%s pretrained=%s device=%s", args.model, args.pretrained, device)

@app.post("/embed_image")
async def embed_image(file: UploadFile = File(...), x_api_key: str = Header(None)):
    if API_KEY and x_api_key != API_KEY:
        raise HTTPException(401, "unauthorized")
    max_mb = int(os.getenv('MAX_UPLOAD_MB', '10'))
    MAX_SIZE = max_mb * 1024 * 1024
    img_bytes = await file.read(MAX_SIZE + 1)
    if len(img_bytes) > MAX_SIZE:
        return JSONResponse({"error":"file too large"}, status_code=413)
    img = Image.open(io.BytesIO(img_bytes)).convert("RGB")
    with torch.no_grad():
        im = preprocess(img).unsqueeze(0).to(device)
        feats = model.encode_image(im)
        feats = feats / feats.norm(dim=-1, keepdim=True)
    vec = feats.cpu().tolist()[0]
    logging.getLogger('clip-embed').info("embed_image dim=%d", len(vec))
    return JSONResponse({"vector": vec})

@app.post("/embed_text")
async def embed_text(text: str = Form(...), x_api_key: str = Header(None)):
    if API_KEY and x_api_key != API_KEY:
        raise HTTPException(401, "unauthorized")
    with torch.no_grad():
        tok = tokenizer([text]).to(device)
        feats = model.encode_text(tok)
        feats = feats / feats.norm(dim=-1, keepdim=True)
    vec = feats.cpu().tolist()[0]
    logging.getLogger('clip-embed').info("embed_text dim=%d", len(vec))
    return JSONResponse({"vector": vec})

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", default=8003, type=int)
    parser.add_argument("--model", default="ViT-L-14")
    parser.add_argument("--pretrained", default="openai")
    args = parser.parse_args()
    import uvicorn
    uvicorn.run("app:app", host=args.host, port=args.port, reload=False)
