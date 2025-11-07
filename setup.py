from setuptools import setup, find_packages

setup(
    name="pdf-extractor",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "PyMuPDF>=1.23.0",
        "pdfplumber>=0.10.0",
        "sentence-transformers>=2.2.2",
        "openai>=1.3.0",
        "numpy>=1.24.0",
        "pandas>=2.0.0",
        "click>=8.1.0",
        "python-dotenv>=1.0.0",
        "scikit-learn>=1.3.0",
        "fastapi>=0.104.0",
        "uvicorn>=0.24.0",
        "python-multipart>=0.0.6",
    ],
    entry_points={
        "console_scripts": [
            "pdf-extract=pdf_extractor.cli:main",
        ],
    },
)

