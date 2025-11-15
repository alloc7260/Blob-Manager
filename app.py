"""
FastAPI webapp for private cloud drive using Azure Blob Storage
"""

import os, io, zipfile, json
from fastapi import FastAPI, File, UploadFile, Form, HTTPException, Request
from fastapi.responses import StreamingResponse, FileResponse
from fastapi.templating import Jinja2Templates
from azure.storage.blob import BlobServiceClient
from werkzeug.utils import secure_filename
from urllib.parse import urlparse
from typing import List, Optional

from dotenv import load_dotenv
load_dotenv()

app = FastAPI()

# Setup templates
templates = Jinja2Templates(directory="templates")

# Azure Blob Storage configuration
BLOB_SAS_URL = os.getenv("BLOB_SAS_URL")
parsed_url = urlparse(BLOB_SAS_URL)
blob_service_client = BlobServiceClient(account_url=f"{parsed_url.scheme}://{parsed_url.netloc}/", credential=parsed_url.query)
container_client = blob_service_client.get_container_client(parsed_url.path.lstrip("/"))

@app.get("/cloud-storage.png")
async def favicon():
    favicon_path = os.path.join("static", "cloud-storage.png")
    return FileResponse(favicon_path)


@app.get("/")
async def index(request: Request):
    """Main page - file listing"""
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/api/files")
async def list_files():
    """List all files organized in folder structure"""
    try:
        blobs = container_client.list_blobs()
        tree = {}

        for blob in blobs:
            parts = blob.name.split("/")
            current = tree

            for i, part in enumerate(parts):
                if i == len(parts) - 1:
                    # It's a file
                    if "files" not in current:
                        current["files"] = []
                    current["files"].append(
                        {
                            "name": part,
                            "path": blob.name,
                            "size": blob.size,
                            "modified": (
                                blob.last_modified.isoformat()
                                if blob.last_modified
                                else None
                            ),
                        }
                    )
                else:
                    # It's a folder
                    if "folders" not in current:
                        current["folders"] = {}
                    if part not in current["folders"]:
                        current["folders"][part] = {}
                    current = current["folders"][part]
        return {"status": "success", "tree": tree}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/upload")
async def upload_file(
    file: UploadFile = File(...),
):
    """Upload file to blob storage with folder structure"""
    try:
        # todo : if uploaded two different files with same name in same folder, handle that using guid and save filename in metadata
        if not file.filename:
            raise HTTPException(status_code=400, detail="No file selected")

        filename = secure_filename(file.filename or "")
        # Build path with folder
        blob_path = filename
        blob_client = container_client.get_blob_client(blob_path)

        # Upload file
        file_content = await file.read()
        blob_client.upload_blob(file_content, overwrite=True)

        return {
            "status": "success",
            "message": f"File {filename} uploaded successfully",
            "filename": filename,
            "path": blob_path,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/upload-folder")
async def upload_folder(
    files: List[UploadFile] = File(...),
    paths: str = Form(...),
    folder: Optional[str] = Form("")
):
    """Upload entire folder structure"""
    try:
        if not files:
            raise HTTPException(status_code=400, detail="No files provided")

        paths_list = json.loads(paths)
        uploaded = []
        
        for file, path in zip(files, paths_list):
            if not file.filename:
                continue

            # Construct full path
            full_path = f"{folder}/{path}" if folder else path
            blob_client = container_client.get_blob_client(full_path)
            file_content = await file.read()
            blob_client.upload_blob(file_content, overwrite=True)
            uploaded.append(full_path)

        return {
            "status": "success",
            "message": f"Uploaded {len(uploaded)} files",
            "uploaded": uploaded,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/download/{blob_path:path}")
async def download_file(blob_path: str):
    """Download file from blob storage"""
    try:
        blob_client = container_client.get_blob_client(blob_path)
        download_stream = blob_client.download_blob()
        filename = blob_path.split("/")[-1]

        return StreamingResponse(
            io.BytesIO(download_stream.readall()),
            media_type="application/octet-stream",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/download-folder")
async def download_folder(folder_path: str = Form(...)):
    """Download entire folder as ZIP"""
    try:
        if not folder_path:
            raise HTTPException(status_code=400, detail="No folder specified")

        blobs = container_client.list_blobs(name_starts_with=folder_path)

        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
            for blob in blobs:
                if not blob.name.endswith("/"):
                    download_stream = container_client.get_blob_client(
                        blob.name
                    ).download_blob()
                    relative_path = blob.name[len(folder_path) :].lstrip("/")
                    zip_file.writestr(relative_path, download_stream.readall())

        zip_buffer.seek(0)
        folder_name = folder_path.split("/")[-1]

        return StreamingResponse(
            zip_buffer,
            media_type="application/zip",
            headers={"Content-Disposition": f"attachment; filename={folder_name}.zip"}
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/search")
async def search_files(q: str):
    """Search files by name"""
    try:
        query = q.lower()
        if not query:
            raise HTTPException(status_code=400, detail="Search query required")

        blobs = container_client.list_blobs()
        files = []
        for blob in blobs:
            if query in blob.name.lower():
                files.append(
                    {
                        "name": blob.name.split("/")[-1],
                        "path": blob.name,
                        "size": blob.size,
                        "created": (
                            blob.creation_time.isoformat()
                            if blob.creation_time
                            else None
                        ),
                    }
                )

        return {"status": "success", "files": files}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app)
