"""FastAPI interface for PDF extraction"""
from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from typing import List, Dict, Optional
from pydantic import BaseModel
from pathlib import Path
import json
import os
from .extractor import PDFExtractor


app = FastAPI(title="PDF Extractor API", version="1.0.0")


class ExtractionRequestItem(BaseModel):
    """Single extraction request item"""
    label: str
    extraction_schema: Dict[str, str]
    pdf_path: str






# Initialize extractor
extractor = None


@app.on_event("startup")
async def startup_event():
    """Initialize extractor on startup"""
    global extractor
    try:
        extractor = PDFExtractor()
    except Exception as e:
        print(f"Warning: Failed to initialize extractor: {e}")


@app.post("/extract")
async def extract_from_requests(request: List[ExtractionRequestItem]):
    """
    Extract data from PDFs based on extraction requests.
    
    Accepts an array of extraction requests, each containing:
    - label: Document type identifier
    - extraction_schema: Dictionary mapping field names to descriptions
    - pdf_path: Path to the PDF file (relative to pdfs folder or absolute)
    
    Returns an array of extraction results.
    """
    if extractor is None:
        raise HTTPException(status_code=500, detail="Extractor not initialized")
    
    results = []
    
    for item in request:
        try:
            # Resolve PDF path
            pdf_path = Path(item.pdf_path)
            
            # If relative path, try to find in pdfs folder
            if not pdf_path.is_absolute():
                # Try in current directory first
                if not pdf_path.exists():
                    # Try in pdfs folder (pdf_extractor/pdfs/)
                    pdfs_folder = Path(__file__).parent / "pdfs"
                    potential_path = pdfs_folder / pdf_path.name
                    if potential_path.exists():
                        pdf_path = potential_path
                    else:
                        # Try as relative to current working directory
                        cwd_path = Path.cwd() / pdf_path
                        if cwd_path.exists():
                            pdf_path = cwd_path
                        else:
                            raise FileNotFoundError(f"PDF file not found: {item.pdf_path}")
            
            if not pdf_path.exists():
                raise FileNotFoundError(f"PDF file not found: {pdf_path}")
            
            # Read PDF file
            with open(pdf_path, 'rb') as f:
                pdf_bytes = f.read()
            
            # Extract data
            extracted_data = extractor.extract(
                label=item.label,
                extraction_schema=item.extraction_schema,
                pdf_bytes=pdf_bytes
            )
            
            results.append({
                "label": item.label,
                "pdf_path": str(pdf_path),
                "extracted_data": extracted_data,
                "success": True
            })
            
        except FileNotFoundError as e:
            results.append({
                "label": item.label,
                "pdf_path": item.pdf_path,
                "extracted_data": {},
                "success": False,
                "error": str(e)
            })
        except Exception as e:
            results.append({
                "label": item.label,
                "pdf_path": item.pdf_path,
                "extracted_data": {},
                "success": False,
                "error": f"Error processing PDF: {str(e)}"
            })
    
    return results


@app.post("/extract-upload")
async def extract_from_upload(
    pdf_file: UploadFile = File(...),
    label: str = Form(...),
    schema_json: str = Form(...)
):
    """
    Extract data from an uploaded PDF file.
    
    Accepts:
    - pdf_file: Uploaded PDF file
    - label: Document type identifier
    - schema_json: JSON string with extraction schema (field_name -> description mapping)
    
    Returns extraction result.
    """
    if extractor is None:
        raise HTTPException(status_code=500, detail="Extractor not initialized")
    
    try:
        # Parse schema JSON
        try:
            extraction_schema = json.loads(schema_json)
        except json.JSONDecodeError as e:
            raise HTTPException(status_code=400, detail=f"Invalid schema JSON: {str(e)}")
        
        # Read PDF file
        pdf_bytes = await pdf_file.read()
        
        # Extract data
        extracted_data = extractor.extract(
            label=label,
            extraction_schema=extraction_schema,
            pdf_bytes=pdf_bytes
        )
        
        return {
            "label": label,
            "filename": pdf_file.filename,
            "extracted_data": extracted_data,
            "success": True
        }
        
    except HTTPException:
        raise
    except Exception as e:
        return {
            "label": label,
            "filename": pdf_file.filename if pdf_file else "unknown",
            "extracted_data": {},
            "success": False,
            "error": f"Error processing PDF: {str(e)}"
        }


@app.post("/extract-batch")
async def extract_from_batch_upload(
    pdf_files: List[UploadFile] = File(...),
    labels: str = Form(...),
    schemas_json: str = Form(...)
):
    """
    Extract data from multiple uploaded PDF files.
    
    Accepts:
    - pdf_files: List of uploaded PDF files (sent as multiple files with field name "pdf_files")
    - labels: JSON string with array of labels (one per PDF)
    - schemas_json: JSON string with array of schemas (one per PDF)
    
    Returns array of extraction results.
    """
    if extractor is None:
        raise HTTPException(status_code=500, detail="Extractor not initialized")
    
    try:
        # Parse labels and schemas
        try:
            labels_list = json.loads(labels)
            schemas_list = json.loads(schemas_json)
        except json.JSONDecodeError as e:
            raise HTTPException(status_code=400, detail=f"Invalid JSON: {str(e)}")
        
        # Validate input lengths
        if len(pdf_files) != len(labels_list) or len(pdf_files) != len(schemas_list):
            raise HTTPException(
                status_code=400,
                detail=f"Mismatch: {len(pdf_files)} files, {len(labels_list)} labels, {len(schemas_list)} schemas"
            )
        
        if len(pdf_files) == 0:
            raise HTTPException(status_code=400, detail="At least one PDF file is required")
        
        results = []
        
        for i, pdf_file in enumerate(pdf_files):
            try:
                label = labels_list[i]
                schema = schemas_list[i]
                
                # Validate schema is a dict
                if not isinstance(schema, dict):
                    raise ValueError(f"Schema {i} must be a dictionary")
                
                # Read PDF file
                pdf_bytes = await pdf_file.read()
                
                # Extract data
                extracted_data = extractor.extract(
                    label=label,
                    extraction_schema=schema,
                    pdf_bytes=pdf_bytes
                )
                
                results.append({
                    "label": label,
                    "filename": pdf_file.filename,
                    "extracted_data": extracted_data,
                    "success": True,
                    "index": i
                })
                
            except Exception as e:
                results.append({
                    "label": labels_list[i] if i < len(labels_list) else "unknown",
                    "filename": pdf_file.filename if pdf_file else "unknown",
                    "extracted_data": {},
                    "success": False,
                    "error": f"Error processing PDF: {str(e)}",
                    "index": i
                })
        
        return results
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Batch processing error: {str(e)}")


# Serve static files for the UI
static_dir = Path(__file__).parent.parent / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")


@app.get("/", response_class=HTMLResponse)
async def serve_ui():
    """Serve the main UI page"""
    ui_file = Path(__file__).parent.parent / "static" / "index.html"
    if ui_file.exists():
        with open(ui_file, "r", encoding="utf-8") as f:
            return f.read()
    return HTMLResponse(
        content="<h1>UI not found</h1><p>Please ensure static/index.html exists.</p>",
        status_code=404
    )


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "extractor_initialized": extractor is not None
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

