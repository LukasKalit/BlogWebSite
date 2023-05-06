from sqlalchemy.orm import Session
from sqlalchemy import select, update, delete, values

from . import models, schemas

import datetime


def register_user(db: Session, user: schemas.User):
    new_user = models.Users(**user.dict())
    db.add(new_user)
    db.commit()
    return True

def get_user_by_email(db: Session, email : str):
    if email != None:
        user = db.execute(select(models.Users).where(models.Users.email == email)).first()
        if not user:
            return None
        return user[0]
    return None

    
def get_user_by_id(db: Session, id : int):
    if id != None:
        user = db.execute(select(models.Users).where(models.Users.id == id)).first()
        if not user:
            return None
        return user[0]
    return None

    
def get_user_by_name(db: Session, username: str):
    if username != None:
        user = db.execute(select(models.Users).where(models.Users.name == username)).first()
        if not user:
            return None
        return user[0]
    return None







# ================================================
def get_all_posts(db: Session):
    return db.scalars(select(models.BlogPost)).all()

def get_post(db: Session, id_post: int):
    return db.scalars(select(models.BlogPost).filter(models.BlogPost.id == id_post)).first()

def get_post_by_title(db: Session, title: str):
    return db.scalars(select(models.BlogPost).filter(models.BlogPost.title == title)).first()

def create_post(db: Session, post_data: schemas.EntirePost):
    x = datetime.datetime.now()
    time = f"{x.strftime('%B')} {x.day}, {x.year}"
    db_post = models.BlogPost(**post_data.dict(), date = time)
    db.add(db_post)
    db.commit()
    db.refresh(db_post)
    return

def update_post(db: Session, post_data: schemas.EntirePost, post_id: int):
    print(post_data.author)
    db.execute(update(models.BlogPost).where(models.BlogPost.id == post_id).values(
        title = post_data.title,
        subtitle = post_data.subtitle,
        body = post_data.body,
        author = post_data.author,
        img_url = post_data.img_url,
    ))
    db.commit()
    return

def delete_post(db: Session, post_id:str):
    try:
        db.execute(delete(models.BlogPost).where(models.BlogPost.id == post_id))
        db.commit()
        return True
    except:
        return False