from typing import List

from fastapi import Depends, FastAPI, HTTPException, Request, Form, status
from sqlalchemy.orm import Session

from . import crud, models, schemas, security, database
from .database import SessionLocal, engine

from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.middleware.sessions import SessionMiddleware
from starlette_wtf import CSRFProtectMiddleware, csrf_protect

from fastapi.responses import HTMLResponse, RedirectResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from fastapi.security import OAuth2PasswordRequestForm
from datetime import timedelta, datetime

import urllib, hashlib

models.Base.metadata.create_all(bind=engine)

app = FastAPI(middleware=[
    Middleware(SessionMiddleware, secret_key='***REPLACEME1***'),
    Middleware(CSRFProtectMiddleware, csrf_secret='***REPLACEME2***')
])


app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")


def get_gravatar_url(email, size=100, default='identicon', rating='g'):
    email_hash = hashlib.md5(email.lower().encode('utf-8')).hexdigest()
    gravatar_url = f"https://www.gravatar.com/avatar/{email_hash}?s={size}&d={default}&r={rating}"
    return gravatar_url


# Security path
@app.post("/token", response_model=schemas.Token)
async def login_for_access_token(request: Request, 
                                 form_data: OAuth2PasswordRequestForm = Depends(), 
                                 db:Session = Depends(database.get_db)):
    user = security.authenticate_user(form_data.username, form_data.password, db)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=security.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = security.create_access_token(
        data={"sub": user.name}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}


# Endpoints

@app.get('/')
def get_all_posts(request:Request, 
                  db: Session = Depends(database.get_db),
                  current_user: schemas.User = Depends(security.get_current_user)):
    if current_user == "expired":
        current_user = None

    posts = crud.get_all_posts(db)

    return templates.TemplateResponse("index.html", {"request": request, "all_posts":posts, "logged_in" : current_user})

@app.get("/about")
def about(request:Request):

    return templates.TemplateResponse("about.html", {'request':request})

@app.get("/contact")
def contact(request:Request):
    return templates.TemplateResponse("contact.html", {'request':request})


# USERS SERVICE

@app.get('/login')
def login(request:Request):
    return templates.TemplateResponse("login.html", {"request": request,"user":"", "msg":""})

@app.post('/login')
async def login(request:Request,
          form: schemas.UserBase = Depends(schemas.UserBase.login_as_form),
          db: Session = Depends(database.get_db)):
    
    msg=""

    if not form.email:
        msg = "Please insert loggin"

    elif not form.password:
        msg = "Please insert password"

    elif not crud.get_user_by_name(db, form.email):
        msg = "This user doesn't exist"
    

    elif not security.authenticate_user(form.email, form.password, db):
        msg = "Invalid login or password"

    else:
        user_oath = schemas.baseaccount_to_oath(form)
        token = await login_for_access_token(request=request, form_data=user_oath, db=db)

        if token:
            redirect_url = request.url_for('get_all_posts')
            response = RedirectResponse(redirect_url)
            response.set_cookie(key="access_token",value= f"Bearer {token['access_token']}", secure=True, httponly=True)
            response.status_code = 302  
            return response

    return templates.TemplateResponse("login.html", {"request": request,"user":"", "msg":msg})


@app.get('/register')
def register(request:Request):
    msg=""
    user=""
    return templates.TemplateResponse("register.html", {"request": request,"user":user, "msg":msg})

@app.post('/register')
def register(request:Request, 
             db:Session = Depends(database.get_db), 
             user:schemas.User = Depends(schemas.User.register_as_form)):
    msg=""

    if not user.name:
        msg = "Please insert loggin"

    elif not user.password:
        msg = "Please insert password"

    elif not user.email:
        msg = "Please insert email"
    elif crud.get_user_by_email(db, user.email):
        msg = "Email in data base already exist."

    elif not crud.get_user_by_name(db, user.name):
        user.password = security.get_password_hash(user.password)
        user.avatar_url = get_gravatar_url(user.email)
        
        if crud.register_user(db, user):            
            redirect_url = request.url_for('login')
            response = RedirectResponse(redirect_url)
            response.status_code = 302
            return response
        else:
            return HTTPException(status_code=500, detail="Something go wrong with registering in database. Please try again.")
    else:
        msg = "Name in data base already exist."

    return templates.TemplateResponse("register.html", {"request": request,"user":user, "msg":msg})


@app.get("/logout")
async def logout():
    response = RedirectResponse(url="/")
    response.delete_cookie("Authorization", domain="127.0.0.1")
    response.delete_cookie("access_token")
    response.delete_cookie("session")
    return response

# HANDLING POST

@app.get("/post/{index}")
async def show_post(request: Request, 
                    index:int, 
                    db:Session = Depends(database.get_db), 
                    current_user: schemas.User = Depends(security.get_current_user)):
    
    if current_user == "expired":
        current_user = None

    requested_post = None
    posts = crud.get_all_posts(db)
    for blog_post in posts:
        #This can be replace by crud
        if blog_post.id == index:
            requested_post = blog_post

    comments = crud.get_comments_to_post(db= db, post_id= requested_post.id)
    comments = [item[0] for item in comments]

    for i in range(len(comments)):
        avatar = crud.get_user_by_id(db=db, id=comments[i].owner_id).avatar_url
        comments[i].avatar_url = avatar
        comments[i] = schemas.AvatarComment(**comments[i].__dict__)

    return templates.TemplateResponse("post.html", {"request": request, 'requested_post': requested_post, "logged_in": current_user, "comments": comments})

@app.post("/post/{index}")
@security.expired_redirection
async def send_comment(request: Request, 
                       index:int, 
                       db: Session = Depends(database.get_db), 
                       comment:schemas.CommentText = Depends(schemas.CommentText.as_form), 
                       current_user: schemas.User = Depends(security.get_current_user_required)):

    requested_post = None
    posts = crud.get_all_posts(db)
    for blog_post in posts:
        #This can be replace by crud
        if blog_post.id == index:
            requested_post = blog_post

    dt =datetime.now()
    comment_model = schemas.EntireComment(
        **comment.dict(),
        # text = comment.text,
        date = dt.strftime("%Y-%m-%d %H:%M:%S"),
        owner_id = current_user.id,
        post_id = requested_post.id
        )
    crud.add_comment(db=db, comment_data=comment_model) 

    comments = crud.get_comments_to_post(db= db, post_id= requested_post.id)
    comments = [item[0] for item in comments]

    for i in range(len(comments)):
        avatar = crud.get_user_by_id(db=db, id=comments[i].owner_id).avatar_url
        comments[i].avatar_url = avatar
        comments[i] = schemas.AvatarComment(**comments[i].__dict__)

    return templates.TemplateResponse("post.html", {"request": request, 'requested_post': requested_post, "logged_in": current_user, "comments": comments})



@app.get("/delete/{id}")
# @security.admin_privilages
@security.expired_redirection
@security.owner_privilages
async def delete_post(id = int, 
                      db:Session = Depends(database.get_db), 
                      current_user:schemas.User = Depends(security.get_current_user_required)):
    
    if crud.delete_post(db,id) == False:
        raise HTTPException(status_code=404, detail="Post not found")
    else:
        pass
    response = RedirectResponse(url='/')
    response.status_code = 302
    return response


# NEW POST

@app.get("/new_post/")
@security.expired_redirection
async def new_post(request:Request, 
                   current_user:schemas.User = Depends(security.get_current_user_required)):
    form = await schemas.CreatePostForm.from_formdata(request)
    body_text = schemas.PostBase()
    return templates.TemplateResponse('make-post.html', {'request':request, "form":form, "body_text":body_text, "logged_in" : current_user})

@app.post("/new_post/")
@security.expired_redirection
async def new_post(request:Request,
                   db: Session = Depends(database.get_db), 
                   body_text: schemas.PostBase = Depends(schemas.PostBase.as_form),
                   current_user: schemas.User = Depends(security.get_current_user_required)):
    form = await schemas.CreatePostForm.from_formdata(request)

    if await form.validate_on_submit():

        # make validation for fastapi form
        post_data = schemas.EntirePost(
            title = form.title.data,
            subtitle = form.subtitle.data,
            author = form.author.data,
            img_url = form.img_url.data,
            body = body_text.body,
            owner_id = current_user.id
        )

        crud.create_post(db=db, post_data=post_data)
        post = crud.get_post_by_title(db, post_data.title)
        response = RedirectResponse(url=f'/post/{post.id}')
        response.status_code = 302
        return response

    return templates.TemplateResponse('make-post.html', {'request':request, "form":form, "body_text":body_text})

# EDIT POST

@app.get('/edit/{id}')
# @security.admin_privilages
@security.expired_redirection
@security.owner_privilages
async def edit_post(request:Request, 
                    id : int, 
                    db : Session = Depends(database.get_db), 
                    current_user:schemas.User = Depends(security.get_current_user_required)):
    crud_data = crud.get_post(db, id)
    form = await schemas.CreatePostForm.from_formdata(request)
    form.title.data = crud_data.title
    form.subtitle.data = crud_data.subtitle
    form.author.data = crud_data.author
    form.img_url.data = crud_data.img_url
    body_text = schemas.PostBase
    body_text.body = crud_data.body
    editing = True
    return templates.TemplateResponse('make-post.html', {'request':request, "form":form, "body_text":body_text, "editing":editing})


@app.post('/edit/{id}')
# @security.admin_privilages
@security.expired_redirection
@security.owner_privilages
async def edit_post(request:Request, 
                    id: int, 
                    db: Session = Depends(database.get_db), 
                    body_text: schemas.PostBase = Depends(schemas.PostBase.as_form),
                    current_user:schemas.User = Depends(security.get_current_user_required)):
    form = await schemas.CreatePostForm.from_formdata(request)
    editing = True
    
    if await form.validate_on_submit():
        # make validation for fastapi form
        post_data = schemas.EntirePost(
            title = form.title.data,
            subtitle = form.subtitle.data,
            author = form.author.data,
            img_url = form.img_url.data,
            body = body_text.body,
            owner_id = current_user.id
        )

        crud.update_post(db, post_data, id)
        post = crud.get_post_by_title(db, post_data.title)
        response = RedirectResponse(url=f'/post/{post.id}')
        response.status_code = 302
        return response

    return templates.TemplateResponse('make-post.html', {'request':request, "form":form, "body_text":body_text, "editing":editing})


