#!/usr/bin/env python3
"""Simple script to run the PDF Extractor API"""
import uvicorn

if __name__ == "__main__":
    uvicorn.run("pdf_extractor.api:app", host="0.0.0.0", port=8000, reload=True)

