import secrets
from datetime import datetime
from fastapi import FastAPI, Request, Form, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from config.db import redis_client, audit_collection

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")
templates.env.cache = None  # Disables the cache to prevent the unhashable type error

@app.get("/", response_class=HTMLResponse)
def read_index(request: Request):
    return templates.TemplateResponse(
    request=request, 
    name="index.html", 
    context={"request": request}
)

@app.post("/create", response_class=HTMLResponse)
def create_secret(request: Request, secret_text: str = Form(...), ttl_seconds: int = Form(300)):
    # 1. Generate a secure random token for the URL
    token = secrets.token_urlsafe(16)
    
    # 2. Save secret text in Redis with a TTL (Time-To-Live) expiration
    redis_client.setex(name=token, time=ttl_seconds, value=secret_text)
    
    # 3. Save harmless metadata in MongoDB for audit logs
    audit_collection.insert_one({
        "token": token,
        "created_at": datetime.utcnow(),
        "status": "active",
        "expires_in": ttl_seconds
    })
    
    # 4. Generate shareable link
    share_url = str(request.url_for("view_secret", token=token))
    return templates.TemplateResponse(
    request=request, 
    name="success.html", 
    context={"request": request, "share_url": share_url}
)

@app.get("/secret/{token}", response_class=HTMLResponse)
def view_secret(request: Request, token: str):
    # 1. Fetch secret text from Redis
    secret_message = redis_client.get(token)
    
    if not secret_message:
        # UPDATE MONGODB: Mark it as expired if it was still marked active
        audit_collection.update_one(
            {"token": token, "status": "active"}, 
            {"$set": {"status": "expired"}}
        )
        
        return templates.TemplateResponse(
            request=request, 
            name="view.html", 
            context={
                "request": request, 
                "error": "This secret has expired, already been viewed, or never existed."
            }
        )
    
    # 2. SELF-DESTRUCTION: Immediately delete from Redis forever
    redis_client.delete(token)
    
    # 3. Update MongoDB audit log status to destroyed
    audit_collection.update_one({"token": token}, {"$set": {"status": "destroyed"}})
    
    return templates.TemplateResponse(
        request=request, 
        name="view.html", 
        context={
            "request": request, 
            "secret_message": secret_message
        }
    )