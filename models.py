from sqlalchemy import Column, Integer, String, Text, DateTime
from database import Base
from datetime import datetime

# Ito ang magiging 'Table' sa database natin
class ContactMessage(Base):
    __tablename__ = "contact_messages"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50))
    email = Column(String(100))
    message = Column(Text)
    date_sent = Column(DateTime, default=datetime.utcnow) # Automatic na ilalagay ang petsa at oras

# BAGONG TABLE PARA SA MGA PROJECTS/DESIGNS MO
class Project(Base):
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(100))        # Halimbawa: "GLAM-ID UI Design"
    description = Column(Text)         # Halimbawa: "NFC-based loyalty card app design..."
    image_url = Column(String(255))    # Dito natin ise-save yung pangalan ng picture (e.g., "project1.jpg")
    category = Column(String(50))      # Halimbawa: "UI/UX" o "Graphic Design"
    created_at = Column(DateTime, default=datetime.utcnow)