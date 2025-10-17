from fastapi import FastAPI, Request, HTTPException
import httpx

app = FastAPI()

GOOGLE_DRIVE_API = "https://www.googleapis.com/drive/v3"
GOOGLE_USERINFO = "https://www.googleapis.com/oauth2/v3/userinfo"

async def _get_auth_header(request: Request) -> str:
    auth = request.headers.get("Authorization")
    if not auth or not auth.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Missing Google OAuth Bearer token")
    return auth

@app.get("/health")
async def health():
    return {"ok": True}

@app.get("/me")
async def me(request: Request):
    auth = await _get_auth_header(request)
    async with httpx.AsyncClient(timeout=20) as client:
        r = await client.get(GOOGLE_USERINFO, headers={"Authorization": auth})
        if r.status_code != 200:
            raise HTTPException(status_code=r.status_code, detail=r.text)
        return r.json()

@app.get("/drive/files")
async def list_files(request: Request, q: str | None = None, pageToken: str | None = None, pageSize: int = 25):
    auth = await _get_auth_header(request)
    params = {
        "pageSize": pageSize,
        "fields": "files(id,name,mimeType,modifiedTime,owners(displayName,emailAddress)),nextPageToken",
    }
    if q: params["q"] = q
    if pageToken: params["pageToken"] = pageToken
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.get(f"{GOOGLE_DRIVE_API}/files", headers={"Authorization": auth}, params=params)
        if r.status_code != 200:
            raise HTTPException(status_code=r.status_code, detail=r.text)
        return r.json()

@app.get("/drive/files/{file_id}")
async def get_file_meta(request: Request, file_id: str):
    auth = await _get_auth_header(request)
    params = {"fields": "id,name,mimeType,size,modifiedTime,owners,webViewLink"}
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.get(f"{GOOGLE_DRIVE_API}/files/{file_id}", headers={"Authorization": auth}, params=params)
        if r.status_code != 200:
            raise HTTPException(status_code=r.status_code, detail=r.text)
        return r.json()

@app.get("/drive/files/{file_id}/download")
async def download_file(request: Request, file_id: str):
    auth = await _get_auth_header(request)
    async with httpx.AsyncClient(timeout=60) as client:
        # For Google Docs/Sheets/Slides, you might need /export with mimeType.
        r = await client.get(f"{GOOGLE_DRIVE_API}/files/{file_id}?alt=media", headers={"Authorization": auth})
        if r.status_code != 200:
            raise HTTPException(status_code=r.status_code, detail=r.text)
        # Stream raw bytes back
        return r.content
