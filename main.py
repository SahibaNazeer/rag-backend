import os
import psycopg2
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from pypdf import PdfReader
from sentence_transformers import SentenceTransformer
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Load lightweight local embedding model (Runs on your CPU, no API calls needed!)
embedder = SentenceTransformer('all-MiniLM-L6-v2')

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

DB_NAME = os.getenv("DB_NAME", "postgres")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "postgres")
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")

def get_db_connection():
    try:
        return psycopg2.connect(
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            host=DB_HOST,
            port=DB_PORT,
            connect_timeout=5
        )
    except Exception as e:
        print("Database connection error:", e)
        return None

class QueryRequest(BaseModel):
    question: str

@app.post("/upload")
async def upload_pdf(file: UploadFile = File(...)):
    if not file.filename.endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed")

    conn = get_db_connection()
    if not conn:
        raise HTTPException(status_code=500, detail="Database connection failed. Check PostgreSQL service.")

    try:
        reader = PdfReader(file.file)
        text = ""
        for page in reader.pages:
            extracted = page.extract_text()
            if extracted:
                text += extracted + "\n"

        if not text.strip():
            raise HTTPException(status_code=400, detail="Could not extract text from PDF")

        # Local CPU Vector Generation (No API 404 possible)
        embedding = embedder.encode(text[:8000]).tolist()

        cur = conn.cursor()
        cur.execute(
            "INSERT INTO documents (content, embedding) VALUES (%s, %s::vector)",
            (text, str(embedding))
        )
        conn.commit()
        cur.close()
        conn.close()

        return {"message": "PDF uploaded and embeddings saved successfully!"}

    except Exception as e:
        if conn:
            conn.close()
        print("Upload Error:", e)
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/query")
async def query_rag(request: QueryRequest):
    conn = get_db_connection()
    if not conn:
        raise HTTPException(status_code=500, detail="Database connection failed. Check PostgreSQL service.")

    try:
        # Local CPU Query Vector Generation
        q_embedding = embedder.encode(request.question).tolist()

        cur = conn.cursor()
        cur.execute(
            "SELECT content FROM documents ORDER BY embedding <=> %s::vector LIMIT 3",
            (str(q_embedding),)
        )
        rows = cur.fetchall()
        cur.close()
        conn.close()

        context = "\n---\n".join([r[0] for r in rows]) if rows else ""
        prompt = f"Context:\n{context}\n\nQuestion: {request.question}\n\nAnswer concisely based on context:"
        
        # Gemini generates the final natural text answer
        model = genai.GenerativeModel('gemini-3.5-flash')
        gen_response = model.generate_content(prompt)

        return {"answer": gen_response.text}

    except Exception as e:
        if conn:
            conn.close()
        print("Query Error:", e)
        raise HTTPException(status_code=500, detail=str(e))