"""
Flask webapp for private cloud drive using Azure Blob Storage
"""

import os, io, zipfile, json
from flask import Flask, render_template, request, jsonify, send_file
from azure.storage.blob import BlobServiceClient
from werkzeug.utils import secure_filename
from urllib.parse import urlparse

from dotenv import load_dotenv
load_dotenv()

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 100 * 1024 * 1024  # 100MB max upload

# Azure Blob Storage configuration
BLOB_SAS_URL = os.getenv("BLOB_SAS_URL")
parsed_url = urlparse(BLOB_SAS_URL)
ACCOUNT_URL = f"{parsed_url.scheme}://{parsed_url.netloc}/"
CONTAINER_NAME = parsed_url.path.lstrip("/")
CREDENTIAL = parsed_url.query

blob_service_client = BlobServiceClient(account_url=ACCOUNT_URL, credential=CREDENTIAL)
container_client = blob_service_client.get_container_client(CONTAINER_NAME)

# Allowed file extensions
# ALLOWED_EXTENSIONS = {
#     "txt",
#     "pdf",
#     "doc",
#     "docx",
#     "xls",
#     "xlsx",
#     "zip",
#     "jpg",
#     "jpeg",
#     "png",
#     "gif",
#     "py",
#     "js",
#     "json",
#     "csv",
#     "md",
#     "ppt",
#     "pptx",
#     "mp4",
# }


# def allowed_file(filename):
#     return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def build_folder_tree(blobs):
    """Build a hierarchical folder structure from blob paths"""
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

    return tree


@app.route("/")
def index():
    """Main page - file listing"""
    return render_template("index.html")


@app.route("/api/files", methods=["GET"])
def list_files():
    """List all files organized in folder structure"""
    try:
        blobs = container_client.list_blobs()
        tree = build_folder_tree(blobs)
        return jsonify({"status": "success", "tree": tree})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/api/upload", methods=["POST"])
def upload_file():
    """Upload file to blob storage with folder structure"""
    try:
        # todo : if uploaded two different files with same name in same folder, handle that using guid and save filename in metadata
        if "file" not in request.files:
            return jsonify({"status": "error", "message": "No file provided"}), 400

        file = request.files["file"]
        folder = request.form.get("folder", "")

        if not file.filename:
            return jsonify({"status": "error", "message": "No file selected"}), 400

        # if not allowed_file(file.filename):
        #     return jsonify({"status": "error", "message": "File type not allowed"}), 400

        filename = secure_filename(file.filename or "")
        # Build path with folder
        blob_path = f"{folder}/{filename}" if folder else filename
        blob_client = container_client.get_blob_client(blob_path)

        # Upload file
        file_content = file.read()
        blob_client.upload_blob(file_content, overwrite=True)

        return jsonify(
            {
                "status": "success",
                "message": f"File {filename} uploaded successfully",
                "filename": filename,
                "path": blob_path,
            }
        )
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/api/upload-folder", methods=["POST"])
def upload_folder():
    """Upload entire folder structure"""
    try:
        files = request.files.getlist("files[]")
        paths = json.loads(request.form.get("paths[]"))
        folder_prefix = request.form.get("folder", "")

        if not files:
            return jsonify({"status": "error", "message": "No files provided"}), 400

        uploaded = []
        for file, path in zip(files, paths):
            if not file.filename:
                continue

            # if not allowed_file(file.filename):
            #     continue

            # Construct full path
            full_path = f"{folder_prefix}/{path}" if folder_prefix else path
            blob_client = container_client.get_blob_client(full_path)
            file_content = file.read()
            blob_client.upload_blob(file_content, overwrite=True)
            uploaded.append(full_path)

        return jsonify(
            {
                "status": "success",
                "message": f"Uploaded {len(uploaded)} files",
                "uploaded": uploaded,
            }
        )
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/api/download/<path:blob_path>", methods=["GET"])
def download_file(blob_path):
    """Download file from blob storage"""
    try:
        blob_client = container_client.get_blob_client(blob_path)
        download_stream = blob_client.download_blob()
        filename = blob_path.split("/")[-1]

        return send_file(
            io.BytesIO(download_stream.readall()),
            # as_attachment=True,
            download_name=filename,
        )
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/api/download-folder", methods=["POST"])
def download_folder():
    """Download entire folder as ZIP"""
    try:
        data = request.get_json() or {}
        folder_path = data.get("folder_path", "")

        if not folder_path:
            return jsonify({"status": "error", "message": "No folder specified"}), 400

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

        return send_file(
            zip_buffer,
            mimetype="application/zip",
            # as_attachment=True,
            download_name=f"{folder_name}.zip",
        )
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/api/file-info/<path:blob_path>", methods=["GET"])
def get_file_info(blob_path):
    """Get detailed info about a file"""
    try:
        blob_client = container_client.get_blob_client(blob_path)
        properties = blob_client.get_blob_properties()

        return jsonify(
            {
                "status": "success",
                "info": {
                    "name": blob_path.split("/")[-1],
                    "path": blob_path,
                    "size": properties.size,
                    "content_type": properties.content_settings.content_type,
                    "created": (
                        properties.creation_time.isoformat()
                        if properties.creation_time
                        else None
                    ),
                    "modified": (
                        properties.last_modified.isoformat()
                        if properties.last_modified
                        else None
                    ),
                },
            }
        )
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/api/search", methods=["GET"])
def search_files():
    """Search files by name"""
    try:
        query = request.args.get("q", "").lower()
        if not query:
            return jsonify({"status": "error", "message": "Search query required"}), 400

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

        return jsonify({"status": "success", "files": files})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


if __name__ == "__main__":
    app.run()
