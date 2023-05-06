from pydantic import BaseModel, ValidationError, validator
from starlette_wtf import StarletteForm
from wtforms import StringField, SubmitField
from wtforms.validators	import DataRequired, URL
from fastapi import Form
from typing import Union

##WTForm
class CreatePostForm(StarletteForm):
    title = StringField("Blog Post Title", validators=[DataRequired()])
    subtitle = StringField("Subtitle", validators=[DataRequired()])
    author = StringField("Your Name", validators=[DataRequired()])
    img_url = StringField("Blog Image URL", validators=[DataRequired(), URL()])
    submit = SubmitField("Submit Post")

class PostBase(BaseModel):
    body: str | str = ""
    
    @classmethod
    def as_form(self,
        body: str = Form()):

        return self(body=body)

    # @validator('body')
    # def body_cannot_be_empty(cls, v):
    #     if v == "":
    #         raise ValueError('value cannot be empty')
    #     return v.title()


class EntirePost(PostBase):
    title : str
    subtitle : str
    author : str
    img_url: str

    class Config:
        orm_mode = True


class UserBase(BaseModel):
    email: str
    password: str

    @classmethod
    async def login_as_form(self,
                      email: str = Form(""),
                      password: str = Form("")):
        return self(email=email, password=password)
    
    
    class Config:
        orm_mode = True


def baseaccount_to_oath(form):
    class OauthForm():
        username = form.email
        password = form.password

    return OauthForm()


class User(UserBase):
    name: str

    @classmethod
    async def register_as_form(self,
                         name: str = Form(""),
                         email: str = Form(""),
                         password: str = Form("")):
        return self(name=name, email=email, password=password,)
    

class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    username: Union[str, None] = None