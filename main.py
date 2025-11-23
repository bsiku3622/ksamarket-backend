from fastapi import FastAPI
from routes import auth, users, items, uploads, chatrooms
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root():
    return {"message": "Developed by Jaewon Baek."}


app.include_router(auth.router, prefix="/auth", tags=["Auth"])
app.include_router(users.router, prefix="/users", tags=["Users"])
app.include_router(items.router, prefix="/items", tags=["Items"])
app.include_router(uploads.router, prefix="/uploads", tags=["Uploads"])
app.include_router(chatrooms.router, prefix="/chatrooms", tags=["Chatrooms"])
