from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from . import models, schemas, crud
from .database import engine, Base, get_db
from fastapi.middleware.cors import CORSMiddleware
from .auth import hash_password, verify_password, create_access_token
from .models import User
from .schemas import UserCreate, Token
from fastapi.security import OAuth2PasswordBearer
import os
import jose
from fastapi import Depends

Base.metadata.create_all(bind=engine)

app = FastAPI()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # for now, later restrict
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = "HS256"

def get_current_user(token: str = Depends(oauth2_scheme)):
    try:
        payload = jose.jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
        if username is None:
            raise HTTPException(status_code=401, detail="Invalid token")
        return username
    except jose.JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

@app.post("/items", response_model=schemas.ItemResponse)
def create(item: schemas.ItemCreate, db: Session = Depends(get_db)):
    return crud.create_item(db, item)

@app.get("/items")
# def read_all(db: Session = Depends(get_db)):
def read_all(
    db: Session = Depends(get_db),
    user: str = Depends(get_current_user)
):
    return crud.get_items(db)

@app.get("/items/{item_id}")
def read_one(item_id: int, db: Session = Depends(get_db)):
    item = crud.get_item(db, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Not found")
    return item

@app.put("/items/{item_id}")
def update(item_id: int, item: schemas.ItemCreate, db: Session = Depends(get_db)):
    updated = crud.update_item(db, item_id, item)
    if not updated:
        raise HTTPException(status_code=404, detail="Not found")
    return updated

@app.delete("/items/{item_id}")
def delete(item_id: int, db: Session = Depends(get_db)):
    deleted = crud.delete_item(db, item_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Not found")
    return {"message": "Deleted"}


@app.post("/register")
def register(user: UserCreate, db: Session = Depends(get_db)):
    db_user = User(username=user.username, password=hash_password(user.password))
    db.add(db_user)
    db.commit()
    return {"message": "User created"}

@app.post("/login", response_model=Token)
def login(user: UserCreate, db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.username == user.username).first()

    if not db_user or not verify_password(user.password, db_user.password):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = create_access_token({"sub": db_user.username})
    return {"access_token": token, "token_type": "bearer"}