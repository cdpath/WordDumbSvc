import os
import shutil
import sys
import tempfile
from pathlib import Path
from typing import List, Optional

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

# Add the parent directory to the Python path to import the plugin files
sys.path.append(str(Path(__file__).parent.parent))
from metadata import cli_check_metadata
from parse_job import ParseJobData, do_job
from utils import Log
from database import get_ll_path, get_x_ray_path

app = FastAPI(
    title="WordDumb API",
    description="API for generating Kindle Word Wise and X-Ray files for ebooks",
    version="1.0.0",
)

# Create temp directory for uploads and processed files
TEMP_DIR = Path(tempfile.gettempdir()) / "worddumb_api"
TEMP_DIR.mkdir(exist_ok=True)

# Serve static files (frontend) if available
static_dir = Path("static")
if static_dir.exists():
    app.mount("/static", StaticFiles(directory="static"), name="static")


class ProcessResult(BaseModel):
    title: str
    format: str
    created_files: List[str]
    download_urls: List[str]
    messages: List[str]


@app.post("/api/process", response_model=ProcessResult)
async def process_ebook(
    file: UploadFile = File(...),
    create_wordwise: bool = Form(True),
    create_xray: bool = Form(True),
):
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file uploaded")
    
    # Create unique directory for this upload
    unique_id = tempfile.mkdtemp(dir=TEMP_DIR)
    unique_dir = Path(unique_id)
    
    # Save uploaded file
    file_path = unique_dir / file.filename
    try:
        with open(file_path, "wb") as f:
            shutil.copyfileobj(file.file, f)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error saving file: {str(e)}")
    
    # Process the ebook
    log = Log()
    messages = []
    
    # Check metadata
    md_result = cli_check_metadata(str(file_path), log)
    if md_result is None:
        raise HTTPException(status_code=400, detail="Unsupported book format or language")
    
    # Check support for Word Wise and X-Ray
    create_w = create_wordwise
    create_x = create_xray
    
    if create_w and not md_result.support_ww_list[0]:
        create_w = False
        messages.append("Book language is not supported for Word Wise")
    
    if create_x and not md_result.support_x_ray:
        create_x = False
        messages.append("X-Ray doesn't support the book language")
    
    if not create_w and not create_x:
        raise HTTPException(status_code=400, detail="Cannot create Word Wise or X-Ray for this book")
    
    # Create notification string
    notif = []
    if create_w:
        notif.append("Word Wise")
    if create_x:
        notif.append("X-Ray")
    notif_str = " and ".join(notif)
    messages.append(f"Creating {notif_str} file for book {md_result.mi.get('title')}")
    
    # Create job data and process
    job_data = ParseJobData(
        book_fmt=md_result.book_fmts[0],
        book_path=str(file_path),
        mi=md_result.mi,
        book_lang=md_result.book_lang,
        create_ww=create_w,
        create_x=create_x,
    )
    
    try:
        result = do_job(job_data)
        
        # Find generated files
        book_dir = file_path.parent
        created_files = []
        download_urls = []
        
        # For EPUB, it's a modified version of the original file
        if md_result.book_fmts[0] == "EPUB":
            new_file_stem = file_path.stem
            if create_x:
                new_file_stem += "_x_ray"
            if create_w:
                new_file_stem += "_word_wise"
            new_file = book_dir / f"{new_file_stem}.epub"
            if new_file.exists():
                created_files.append(new_file.name)
                download_urls.append(f"/api/download/{unique_dir.name}/{new_file.name}")
        else:
            # For Kindle formats, look for sidecar files
            if create_w:
                ll_path = get_ll_path(job_data.asin, str(file_path))
                if Path(ll_path).exists():
                    created_files.append(Path(ll_path).name)
                    download_urls.append(f"/api/download/{unique_dir.name}/{Path(ll_path).name}")
            
            if create_x:
                x_ray_path = get_x_ray_path(job_data.asin, str(file_path))
                if Path(x_ray_path).exists():
                    created_files.append(Path(x_ray_path).name)
                    download_urls.append(f"/api/download/{unique_dir.name}/{Path(x_ray_path).name}")
        
        return ProcessResult(
            title=md_result.mi.get("title"),
            format=md_result.book_fmts[0],
            created_files=created_files,
            download_urls=download_urls,
            messages=messages
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing book: {str(e)}")


@app.get("/api/download/{unique_id}/{filename}")
async def download_file(unique_id: str, filename: str):
    file_path = TEMP_DIR / unique_id / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    
    return FileResponse(
        path=file_path,
        filename=filename,
        media_type="application/octet-stream"
    )


@app.get("/")
async def read_root():
    return {"message": "WordDumb API is running. Visit /docs for API documentation."}


# Cleanup old files periodically (could be implemented as a background task)
@app.on_event("startup")
async def startup_event():
    # This could clean up old temporary files
    pass 