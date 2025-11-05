import os
import base64
from datetime import datetime, timezone
from typing import Optional

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, HttpUrl

from schemas import ModelFile, ModelConfig
from database import db, create_document

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def read_root():
    return {"message": "Hello from FastAPI Backend!"}


@app.get("/api/hello")
def hello():
    return {"message": "Hello from the backend API!"}


@app.get("/test")
def test_database():
    """Test endpoint to check if database is available and accessible"""
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": None,
        "database_name": None,
        "connection_status": "Not Connected",
        "collections": []
    }

    try:
        if db is not None:
            response["database"] = "✅ Available"
            response["database_url"] = "✅ Configured"
            response["database_name"] = db.name if hasattr(db, 'name') else "✅ Connected"
            response["connection_status"] = "Connected"

            try:
                collections = db.list_collection_names()
                response["collections"] = collections[:10]
                response["database"] = "✅ Connected & Working"
            except Exception as e:
                response["database"] = f"⚠️  Connected but Error: {str(e)[:50]}"
        else:
            response["database"] = "⚠️  Available but not initialized"

    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:50]}"

    # Check environment variables
    response["database_url"] = "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set"
    response["database_name"] = "✅ Set" if os.getenv("DATABASE_NAME") else "❌ Not Set"

    return response


# ----------------------------
# Model Management Endpoints
# ----------------------------

@app.post("/api/models", response_class=JSONResponse)
async def upload_model(file: UploadFile = File(...)):
    """Upload a model .zip and store it in MongoDB as base64 string.
    Returns the stored document metadata.
    """
    if not file.filename.lower().endswith('.zip'):
        raise HTTPException(status_code=400, detail="File must be a .zip archive")

    content = await file.read()
    if len(content) == 0:
        raise HTTPException(status_code=400, detail="Empty file")

    try:
        b64 = base64.b64encode(content).decode('utf-8')
        doc = ModelFile(
            name=file.filename,
            size=len(content),
            content_type=file.content_type or 'application/zip',
            data_b64=b64,
            active=True,
        )

        # Deactivate previous active models and URL configs
        if db is None:
            raise HTTPException(status_code=500, detail="Database not available")
        db['modelfile'].update_many({"active": True}, {"$set": {"active": False, "updated_at": datetime.now(timezone.utc)}})
        db['modelconfig'].update_many({"active": True}, {"$set": {"active": False, "updated_at": datetime.now(timezone.utc)}})

        inserted_id = create_document('modelfile', doc)
        return {"id": inserted_id, "type": "db", "name": doc.name, "size": doc.size, "content_type": doc.content_type, "active": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to store model: {str(e)}")


class UrlPayload(BaseModel):
    url: HttpUrl


@app.post("/api/models/url", response_class=JSONResponse)
def set_model_url(payload: UrlPayload):
    """Set Teachable Machine model URL as the active source."""
    if db is None:
        raise HTTPException(status_code=500, detail="Database not available")

    # Deactivate previous sources (files and configs)
    db['modelfile'].update_many({"active": True}, {"$set": {"active": False, "updated_at": datetime.now(timezone.utc)}})
    db['modelconfig'].update_many({"active": True}, {"$set": {"active": False, "updated_at": datetime.now(timezone.utc)}})

    cfg = ModelConfig(source_type='url', url=str(payload.url), active=True)
    cfg_id = create_document('modelconfig', cfg)
    return {"id": cfg_id, "type": "url", "url": cfg.url, "active": True}


@app.get("/api/models/active")
def get_active_model():
    """Get metadata of the active model source (db or url)."""
    if db is None:
        raise HTTPException(status_code=500, detail="Database not available")

    # Prefer active URL config if present
    cfg = db['modelconfig'].find_one({"active": True}, sort=[("updated_at", -1)])
    if cfg:
        return {
            "type": "url",
            "url": cfg.get("url"),
            "active": True,
            "updated_at": cfg.get("updated_at")
        }

    # Fallback to active stored file
    doc = db['modelfile'].find_one({"active": True}, sort=[("updated_at", -1)])
    if doc:
        return {
            "type": "db",
            "id": str(doc.get("_id")),
            "name": doc.get("name"),
            "size": doc.get("size"),
            "content_type": doc.get("content_type"),
            "active": True,
            "updated_at": doc.get("updated_at")
        }

    return {"active": False}


@app.get("/api/models", response_class=JSONResponse)
def list_models(limit: Optional[int] = 10):
    """List recent model uploads (metadata only)."""
    if db is None:
        raise HTTPException(status_code=500, detail="Database not available")
    cursor = db['modelfile'].find({}, {"data_b64": 0}).sort("updated_at", -1).limit(limit or 10)
    result = []
    for d in cursor:
        d["id"] = str(d.pop("_id"))
        result.append(d)
    return result


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
