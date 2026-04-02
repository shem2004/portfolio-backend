import jwt
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import smtplib
import os 
from dotenv import load_dotenv 
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session
import time

# --- IMPORTS PARA SA DATABASE ---
import models
from database import engine, SessionLocal

# I-load ang .env file 
load_dotenv() 

ADMIN_USER = os.getenv("ADMIN_USER")
ADMIN_PASS = os.getenv("ADMIN_PASS")
SECRET_KEY = os.getenv("SECRET_KEY")

security = HTTPBearer()

# ITO ANG GUWARDIYA NATIN
def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=["HS256"])
        return payload
    except:
        # GENERIC ERROR: Para walang clue ang hackers
        raise HTTPException(status_code=401, detail="Unauthorized access.")

# I-CREATE ANG DATABASE TABLES AUTOMATICALLY KUNG WALA PA
models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="SΛIΛH Portfolio API")

# Kukunin na natin sa .env ang credentials
MY_EMAIL = os.getenv("EMAIL_USER")
MY_APP_PASSWORD = os.getenv("EMAIL_PASS")

# --- 1. SECURE CORS CONFIGURATION ---
# Kunin ang string mula sa Render (Environment Variable)
origins_raw = os.getenv("ALLOWED_ORIGINS", "")

# Siguraduhin na listahan ang ibabato natin sa middleware
if origins_raw:
    # Paghiwalayin gamit ang comma at tanggalin ang spaces
    ALLOWED_ORIGINS = [origin.strip() for origin in origins_raw.split(",")]
else:
    # Kung walang nakuha sa environment, i-allow ang lahat (para hindi mag-fail ang connect)
    ALLOWED_ORIGINS = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS, 
    allow_credentials=True,
    allow_methods=["*"], # Mas safe na "*" muna para i-allow ang OPTIONS request ng Vercel
    allow_headers=["*"],
)

# --- DEPENDENCY PARA SA DATABASE CONNECTION ---
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- 2. RATE LIMITER (ANTI-SPAM SA CONTACT FORM) ---
ip_tracker = {}
RATE_LIMIT = 5 # 5 messages max
TIME_WINDOW = 86400 # 24 hours (sa seconds)

def check_rate_limit(request: Request):
    client_ip = request.client.host
    current_time = time.time()
    
    if client_ip not in ip_tracker:
        ip_tracker[client_ip] = []
        
    # Linisin ang mga lumang request (lagpas 24 hours na)
    ip_tracker[client_ip] = [t for t in ip_tracker[client_ip] if current_time - t < TIME_WINDOW]
    
    if len(ip_tracker[client_ip]) >= RATE_LIMIT:
        raise HTTPException(status_code=429, detail="Too many requests. Please try again tomorrow.")
        
    ip_tracker[client_ip].append(current_time)


# --- PYDANTIC MODEL ---
class ContactForm(BaseModel):
    name: str
    email: EmailStr  
    message: str

class ProjectCreate(BaseModel):
    title: str
    description: str
    image_url: str
    category: str

# --- EMAIL LOGIC ---
def send_email_notification(sender_name, sender_email, message_content):
    try:
        msg = MIMEMultipart()
        msg['From'] = MY_EMAIL
        msg['To'] = MY_EMAIL  
        msg['Subject'] = f"New Portfolio Message from {sender_name}"

        body = f"""
        You have received a new message from your Portfolio Website!

        --------------------------------------
        Name:    {sender_name}
        Email:   {sender_email}
        --------------------------------------
        
        Message:
        {message_content}
        """
        msg.attach(MIMEText(body, 'plain'))

        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()  
        server.login(MY_EMAIL, MY_APP_PASSWORD)
        server.send_message(msg)
        server.quit()
        return True
    except Exception:
        # 3. TINANGGAL ANG DETAILED PRINT ERRORS PARA SA SECURITY
        return False

# --- API ENDPOINTS ---
@app.post("/api/contact")
async def submit_contact(request: Request, form_data: ContactForm, db: Session = Depends(get_db)):
    # I-CHECK ANG RATE LIMIT BAGO MAG-PROCESS
    check_rate_limit(request)

    # TINANGGAL ANG MGA CONSOLE/PRINT STATEMENTS
    new_message = models.ContactMessage(
        name=form_data.name,
        email=form_data.email,
        message=form_data.message
    )
    db.add(new_message)
    db.commit()
    db.refresh(new_message)

    success = send_email_notification(form_data.name, form_data.email, form_data.message)

    if success:
        return {"status": "success", "message": "Message sent successfully!"}
    else:
        # GENERIC ERROR MESSAGE PARA HINDI MALAMAN NG HACKER ANG SYSTEM MO
        raise HTTPException(status_code=500, detail="An error occurred while sending the message. Please try again later.")

class LoginData(BaseModel):
    username: str
    password: str

@app.post("/api/login")
async def login_admin(data: LoginData):
    if data.username == ADMIN_USER and data.password == ADMIN_PASS:
        token = jwt.encode({"user": data.username}, SECRET_KEY, algorithm="HS256")
        return {"status": "success", "token": token}
    else:
        raise HTTPException(status_code=401, detail="Invalid credentials.") # GENERIC ERROR
    
@app.post("/api/projects")
async def create_project(project_data: ProjectCreate, db: Session = Depends(get_db), token = Depends(verify_token)):
    new_project = models.Project(
        title=project_data.title,
        description=project_data.description,
        image_url=project_data.image_url,
        category=project_data.category
    )
    db.add(new_project)
    db.commit()
    db.refresh(new_project)
    return {"status": "success", "message": "Project added successfully!"}

@app.get("/api/projects")
async def get_projects(db: Session = Depends(get_db)):
    projects = db.query(models.Project).order_by(models.Project.id.desc()).all()
    return projects

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000)