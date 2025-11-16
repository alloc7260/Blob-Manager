"""
FastAPI webapp for private cloud drive using Azure Blob Storage
"""

import os, io, zipfile, json
from fastapi import FastAPI, File, UploadFile, Form, HTTPException, Request, Cookie, Response, Depends
from fastapi.responses import StreamingResponse, FileResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from azure.storage.blob import BlobServiceClient
from werkzeug.utils import secure_filename
from urllib.parse import urlparse
from typing import List, Optional

from dotenv import load_dotenv
load_dotenv()

from utils.database import UserDB
from utils.auth import TOTPAuth, JWTAuth

app = FastAPI()

# Setup templates
templates = Jinja2Templates(directory="templates")


# Dependency to get current user from JWT token
async def get_current_user(access_token: Optional[str] = Cookie(None)):
    """Get current authenticated user from JWT token"""
    if not access_token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    payload = JWTAuth.verify_token(access_token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    username = payload.get("username")
    user = UserDB.get_user_by_username(username)
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    
    return user


# Helper to get blob container client for user
def get_user_container_client(blob_sas_url: str):
    """Get blob container client from user's SAS URL"""
    parsed_url = urlparse(blob_sas_url)
    blob_service_client = BlobServiceClient(
        account_url=f"{parsed_url.scheme}://{parsed_url.netloc}/",
        credential=parsed_url.query
    )
    container_client = blob_service_client.get_container_client(parsed_url.path.lstrip("/"))
    return container_client


@app.get("/cloud-storage.png")
async def favicon():
    favicon_path = os.path.join("static", "cloud-storage.png")
    return FileResponse(favicon_path)


@app.get("/login")
async def login_page(request: Request):
    """Login page"""
    return templates.TemplateResponse("login.html", {"request": request})


@app.get("/signup")
async def signup_page(request: Request):
    """Signup page"""
    return templates.TemplateResponse("signup.html", {"request": request})


@app.get("/")
async def index(request: Request, access_token: Optional[str] = Cookie(None)):
    """Main page - file listing (requires authentication)"""
    if not access_token:
        return RedirectResponse(url="/login", status_code=302)
    
    payload = JWTAuth.verify_token(access_token)
    if not payload:
        return RedirectResponse(url="/login", status_code=302)
    
    return templates.TemplateResponse("index.html", {"request": request})


@app.post("/api/signup")
async def signup(username: str = Form(...), blob_sas_url: str = Form(...)):
    """Create new user account and return TOTP QR code"""
    
    # Check if username exists
    if UserDB.username_exists(username):
        raise HTTPException(status_code=400, detail="Username already exists")
    
    try:
        # Generate TOTP secret
        totp_secret = TOTPAuth.generate_secret()
        
        # Generate QR code
        qr_code = TOTPAuth.generate_qr_code(username, totp_secret)
        
        # Store user (without verification yet)
        UserDB.create_user(username, totp_secret, blob_sas_url)
        
        return {
            "status": "success",
            "message": "Scan QR code with authenticator app",
            "qr_code": qr_code,
            "username": username
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/verify-totp")
async def verify_totp(response: Response, username: str = Form(...), totp_code: str = Form(...)):
    """Verify TOTP code and login"""
    try:
        # Get user
        user = UserDB.get_user_by_username(username)
        if not user:
            raise HTTPException(status_code=401, detail="Invalid username")
        
        # Verify TOTP
        if not TOTPAuth.verify_totp(user["totp_secret"], totp_code):
            raise HTTPException(status_code=401, detail="Invalid TOTP code")
        
        # Create JWT token
        access_token = JWTAuth.create_access_token(data={"sub": username})
        
        # Set cookie
        response.set_cookie(
            key="access_token",
            value=access_token,
            httponly=True,
            secure=True,
            samesite="lax",
            max_age=3600  # 1 hour
        )
        
        return {
            "status": "success",
            "message": "Login successful",
            "username": username
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/login")
async def login(response: Response, username: str = Form(...), totp_code: str = Form(...)):
    """Login with username and TOTP code"""
    return await verify_totp(response, username, totp_code)


@app.post("/api/logout")
async def logout(response: Response):
    """Logout user"""
    response.delete_cookie(key="access_token")
    return {"status": "success", "message": "Logged out successfully"}


@app.get("/api/me")
async def get_me(current_user: dict = Depends(get_current_user)):
    """Get current user info"""
    return {"username": current_user["username"]}


@app.get("/api/files")
async def list_files(current_user: dict = Depends(get_current_user)):
    """List all files organized in folder structure"""
    try:
        container_client = get_user_container_client(current_user["blob_sas_url"])
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
    current_user: dict = Depends(get_current_user)
):
    """Upload file to blob storage with folder structure"""
    try:
        container_client = get_user_container_client(current_user["blob_sas_url"])
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
    folder: Optional[str] = Form(""),
    current_user: dict = Depends(get_current_user)
):
    """Upload entire folder structure"""
    try:
        container_client = get_user_container_client(current_user["blob_sas_url"])
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
async def download_file(blob_path: str, current_user: dict = Depends(get_current_user)):
    """Download file from blob storage"""
    try:
        container_client = get_user_container_client(current_user["blob_sas_url"])
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
async def download_folder(folder_path: str = Form(...), current_user: dict = Depends(get_current_user)):
    """Download entire folder as ZIP"""
    try:
        container_client = get_user_container_client(current_user["blob_sas_url"])
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
async def search_files(q: str, current_user: dict = Depends(get_current_user)):
    """Search files by name"""
    try:
        container_client = get_user_container_client(current_user["blob_sas_url"])
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
