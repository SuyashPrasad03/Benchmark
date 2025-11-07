import os
import json
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from typing import List
from dotenv import load_dotenv
import google.generativeai as genai
import chromadb

# --- Load Environment and Configure API ---
load_dotenv()
GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')
if not GOOGLE_API_KEY:
    raise ValueError("GOOGLE_API_KEY not found in .env file")
genai.configure(api_key=GOOGLE_API_KEY)

# --- Configuration ---
DB_PATH = "db"
COLLECTION_NAME = "steel_reports_v2"
EMBEDDING_MODEL = "models/text-embedding-004"
GENERATION_MODEL = "models/learnlm-2.0-flash-experimental"

# --- FastAPI App Initialization ---
app = FastAPI()

# --- ChromaDB Client Initialization ---
try:
    client = chromadb.PersistentClient(path=DB_PATH)
    collection = client.get_collection(name=COLLECTION_NAME)
    print("Successfully connected to ChromaDB collection.")
except Exception as e:
    print(f"Error connecting to ChromaDB: {e}. Run 'process_pdfs.py' first.")
    collection = None

# --- Pydantic Models for Request Body ---
class CompareRequest(BaseModel):
    query: str
    competitors: List[str] = Field(..., min_length=1)
    base_company: str = "Tata Steel"

# --- API Endpoints ---
@app.get("/api/available-companies")
async def get_available_companies():
    if collection is None:
        raise HTTPException(status_code=500, detail="Database not initialized.")
    try:
        all_metadata = collection.get(include=["metadatas"])['metadatas']
        unique_companies = sorted(list(set(meta['company'] for meta in all_metadata)))
        return {"companies": unique_companies}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Could not fetch companies: {e}")

@app.post("/api/compare")
async def handle_comparison(request: CompareRequest):
    if collection is None:
        raise HTTPException(status_code=500, detail="Database not initialized.")

    try:
        all_companies = [request.base_company] + request.competitors
        
        # 1. Embed the user's query
        query_embedding = genai.embed_content(model=EMBEDDING_MODEL, content=request.query, task_type="RETRIEVAL_QUERY")['embedding']

        # 2. Query ChromaDB for each company to get relevant chunks
        all_docs = []
        for company in all_companies:
            results = collection.query(
                query_embeddings=[query_embedding],
                n_results=5, # Get 5 chunks per company
                where={"company": company}
            )
            all_docs.extend(results['documents'][0])
        
        context = "\n\n".join(all_docs)

        # 3. Construct the detailed prompt for structured JSON output
        prompt = f"""
        You are an expert financial data analyst. Your task is to extract and compare financial metrics from the provided context from annual reports.
        The user wants to compare {', '.join(request.competitors)} against {request.base_company} based on the query: "{request.query}".

        From the context below, extract the relevant data for each company and structure your response as a single JSON object.
        The JSON object must have two keys: "table_data" and "graph_data".

        1. "table_data": An array of objects. Each object represents a financial metric. Each object must have a "Metric" key, and then a key for each company with its value as a string. If a value is not found, use "N/A".
           Example: [{{ "Metric": "Revenue (in Cr)", "Tata Steel": "240,000", "JSW Steel": "225,000" }}]

        2. "graph_data": An object suitable for Chart.js. It must have a "labels" array (company names) and a "datasets" array. Each object in "datasets" represents a metric and must have a "label" (metric name) and a "data" array. The "data" array must contain only numerical values for charting, using 0 for "N/A" values. Remove commas and symbols from numbers.
           Example: {{ "labels": ["Tata Steel", "JSW Steel"], "datasets": [{{ "label": "Revenue (in Cr)", "data": [240000, 225000] }}] }}

        Strictly adhere to this JSON format. Do not add any explanation or text outside the JSON object.

        CONTEXT:
        ---
        {context}
        ---

        JSON_OUTPUT:
        """

        # 4. Generate the structured data
        model = genai.GenerativeModel(GENERATION_MODEL)
        response = model.generate_content(
            prompt,
            generation_config={"response_mime_type": "application/json"}
        )
        
        # The response.text should be a valid JSON string now
        return json.loads(response.text)

    except Exception as e:
        print(f"An error occurred: {e}")
        raise HTTPException(status_code=500, detail=f"An error occurred while processing your request: {e}")

# --- Serve Static Files ---
app.mount("/static", StaticFiles(directory="static"), name="static")
@app.get("/")
async def read_root():
    return FileResponse('static/index.html')