import pathlib
from services.ingest_worker.pipelines.text import ingest_markdown
from services.ingest_worker.pipelines.code import ingest_code
from services.ingest_worker.pipelines.vision import ingest_image
from services.ingest_worker.pipelines.audio import ingest_audio
from services.ingest_worker.pipelines.pdf import ingest_pdf

IMAGE_EXT={'.png','.jpg','.jpeg'}
AUDIO_EXT={'.wav','.mp3','.m4a'}

def dispatch(path: str):
    ext=pathlib.Path(path).suffix.lower()
    if ext in {'.md','.markdown'}: return ingest_markdown(path)
    if ext=='.pdf': return ingest_pdf(path)
    if ext in IMAGE_EXT: return ingest_image(path)
    if ext in AUDIO_EXT: return ingest_audio(path)
    return ingest_code(path)
