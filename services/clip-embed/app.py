import argparse, io, torch
from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import JSONResponse
from PIL import Image
import open_clip

app = FastAPI()
model=None; preprocess=None; tokenizer=None; device="cuda" if torch.cuda.is_available() else "cpu"

@app.on_event("startup")
async def init():
    global model, preprocess, tokenizer, args
    model, _, preprocess = open_clip.create_model_and_transforms(args.model, pretrained=args.pretrained, device=device)
    tokenizer = open_clip.get_tokenizer(args.model)

@app.post("/embed_image")
async def embed_image(file: UploadFile = File(...)):
    img_bytes = await file.read()
    img = Image.open(io.BytesIO(img_bytes)).convert("RGB")
    with torch.no_grad():
        im = preprocess(img).unsqueeze(0).to(device)
        feats = model.encode_image(im)
        feats = feats / feats.norm(dim=-1, keepdim=True)
    return JSONResponse({"vector": feats.cpu().tolist()[0]})

@app.post("/embed_text")
async def embed_text(text: str = Form(...)):
    with torch.no_grad():
        tok = tokenizer([text]).to(device)
        feats = model.encode_text(tok)
        feats = feats / feats.norm(dim=-1, keepdim=True)
    return JSONResponse({"vector": feats.cpu().tolist()[0]})

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", default=8003, type=int)
    parser.add_argument("--model", default="ViT-L-14")
    parser.add_argument("--pretrained", default="openai")
    args = parser.parse_args()
    import uvicorn
    uvicorn.run("app:app", host=args.host, port=args.port, reload=False)
