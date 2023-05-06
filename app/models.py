from sqlalchemy import Boolean, Column, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from .database import Base


class BlogPost(Base):
    __tablename__ = "blog_post"    

    id = Column(Integer, primary_key=True)
    title = Column(String(250), unique=True, nullable=False)
    subtitle = Column(String(250), nullable=False)
    date = Column(String(250), nullable=False)
    body = Column(Text, nullable=False)
    author = Column(String(250), nullable=False)
    img_url = Column(String(250), nullable=False)


class Users(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    email = Column(String(250), unique=True)
    name = Column(String(250), unique=True)
    password = Column(String(200))