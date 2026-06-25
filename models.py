from sqlalchemy import Column, Integer, String, Text, ForeignKey
from database import Base

class Rooms(Base):
    __tablename__ = "rooms"

    id = Column(Integer, primary_key=True, index=True)
    room_id = Column(String(6), unique=True, index=True, nullable=False) 
    creator_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    saved_code = Column(Text, default="") 