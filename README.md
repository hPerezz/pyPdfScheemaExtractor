# PDF Extractor

A high-performance, cost-effective system for extracting structured information from PDF documents. The system uses a multi-stage approach with semantic search and only resorts to LLM (OpenAI) when necessary, making it both accurate and economical.

##  Features

- ✅ **Multi-stage extraction pipeline**: Regex patterns → Semantic search → LLM fallback
- ✅ **Smart candidate generation**: Uses embeddings for semantic similarity matching
- ✅ **Intelligent decision engine**: Only uses LLM when confidence is low
- ✅ **Multiple interfaces**: CLI, REST API, and Web UI
- ✅ **Batch processing**: Process multiple PDFs at once
- ✅ **Configurable thresholds**: Adjust confidence levels for your use case
- ✅ **Cost-effective**: Minimizes LLM API calls by using local models first

##  Technologies

### Backend Framework
- **FastAPI** (>=0.104.0) - Modern, fast web framework for building APIs
- **Uvicorn** (>=0.24.0) - ASGI server for running FastAPI applications
- **Python 3.8+** - Programming language

### PDF Processing
- **PyMuPDF** (>=1.23.0) - Fast PDF text extraction and rendering
- **pdfplumber** (>=0.10.0) - Alternative PDF extraction library for structured data

### Machine Learning & AI
- **sentence-transformers** (>=2.2.2) - Semantic embeddings using transformer models
  - Model: `all-MiniLM-L6-v2` (local, lightweight)
- **OpenAI API** (>=1.3.0) - LLM fallback for low-confidence extractions
  - Model: `gpt-5-mini` (configurable)
- **scikit-learn** (>=1.3.0) - Machine learning utilities
- **numpy** (>=1.24.0) - Numerical computing

### Data Processing
- **pandas** (>=2.0.0) - Data manipulation and analysis

### CLI & Utilities
- **Click** (>=8.1.0) - Command-line interface creation
- **python-dotenv** (>=1.0.0) - Environment variable management
- **python-multipart** (>=0.0.6) - File upload support for FastAPI

### Frontend
- **HTML5/CSS3/JavaScript** - Modern web UI with drag-and-drop support

##  Installation

### Prerequisites

- Python 3.8 or higher
- pip (Python package manager)

### Step 1: Clone the Repository

```bash
git clone <repository-url>
cd enter_ai
```

### Step 2: Create a Virtual Environment (Recommended)

```bash
# Create virtual environment
python3 -m venv venv

# Activate virtual environment
# On macOS/Linux:
source venv/bin/activate
# On Windows:
venv\Scripts\activate
```

### Step 3: Install Dependencies

```bash
# Install all required packages
pip install -r requirements.txt

# Or install the package in development mode
pip install -e .
```

### Step 4: Set Up Environment Variables

Create a `.env` file in the project root:

```bash
OPENAI_API_KEY=your_openai_api_key_here
```

**Note**: You can get an OpenAI API key from [OpenAI Platform](https://platform.openai.com/api-keys).

## ⚙️ Configuration

Configuration settings can be found in `pdf_extractor/config.py`:

- **T_HIGH** (default: 0.85): High confidence threshold - accepts values directly
- **T_LOW** (default: 0.60): Low confidence threshold - uses normalization
- **LLM_MODEL** (default: "gpt-5-mini"): OpenAI model to use for fallback
- **EMBEDDING_MODEL** (default: "sentence-transformers/all-MiniLM-L6-v2"): Local embedding model
- **TOP_K_CANDIDATES** (default: 5): Number of top candidates to consider per field

##  Usage

### 1. Command Line Interface (CLI)

The CLI tool allows you to process multiple PDFs from a folder.

#### Using a Schema File

Create a JSON file (e.g., `schemas.json`) mapping PDF filenames to their extraction schemas:

```json
{
  "documento1.pdf": {
    "label": "RG",
    "schema": {
      "nome": "nome completo da pessoa",
      "cpf": "número de identificação de pessoa física em formato XXX.XXX.XXX-XX",
      "data_nascimento": "data de nascimento no formato DD/MM/AAAA"
    }
  },
  "documento2.pdf": {
    "label": "fatura",
    "schema": {
      "valor": "valor total da fatura em reais",
      "data_vencimento": "data de vencimento no formato DD/MM/AAAA",
      "fornecedor": "nome do fornecedor ou empresa"
    }
  }
}
```

Then run:

```bash
pdf-extract /path/to/pdfs --schema-file schemas.json --output-dir results
```

#### Using Command Line Options

For processing all PDFs with the same schema:

```bash
pdf-extract /path/to/pdfs \
  --label "fatura" \
  --schema-json '{"valor": "valor total da fatura", "data": "data de vencimento"}' \
  --output-dir results
```

#### CLI Options

- `--schema-file, -s`: Path to JSON file with extraction schemas
- `--output-dir, -o`: Directory to save extraction results
- `--label, -l`: Default label for all PDFs (if schema-file not provided)
- `--schema-json, -j`: JSON string with extraction schema (if schema-file not provided)
- `--verbose, -v`: Enable verbose output

### 2. REST API

#### Start the API Server

```bash
python run_api.py
```

Or using uvicorn directly:

```bash
uvicorn pdf_extractor.api:app --host 0.0.0.0 --port 8000 --reload
```

The API will be available at `http://localhost:8000`

#### API Endpoints

##### Health Check
```bash
GET /health
```

##### Extract from File Paths
```bash
POST /extract
Content-Type: application/json

[
  {
    "label": "RG",
    "extraction_schema": {
      "nome": "nome completo da pessoa",
      "cpf": "número de identificação de pessoa física"
    },
    "pdf_path": "path/to/document.pdf"
  }
]
```

##### Extract from Upload (Single File)
```bash
POST /extract-upload
Content-Type: multipart/form-data

pdf_file: <file>
label: "RG"
schema_json: '{"nome": "nome completo", "cpf": "número de CPF"}'
```

##### Extract from Upload (Batch)
```bash
POST /extract-batch
Content-Type: multipart/form-data

pdf_files: <file1>, <file2>, ...
labels: '["RG", "fatura"]'
schemas_json: '[{"nome": "nome"}, {"valor": "valor total"}]'
```

##### Interactive API Documentation

Once the server is running, visit:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

### 3. Web UI

The system includes a beautiful, modern web interface for easy PDF extraction.

#### Access the Web UI

1. Start the API server:
   ```bash
   python run_api.py
   ```

2. Open your browser and navigate to:
   ```
   http://localhost:8000
   ```

#### Using the Web UI

1. Click **"+ Add PDF"** to add a PDF file
2. Upload a PDF file (drag and drop supported)
3. Enter a document label (e.g., "RG", "fatura", "invoice")
4. Define the extraction schema:
   - Use **JSON Editor** mode to write JSON directly
   - Use **Form Builder** mode to add fields visually
5. Add more PDFs if needed
6. Click **"Extract All PDFs"** to process
7. View results in the results section

##  Architecture

The system follows a multi-stage extraction pipeline:

```
PDF Input
    ↓
1. Text Extractor (PyMuPDF/pdfplumber)
    ↓ Extracts text blocks with metadata (bbox, font, size)
2. Preprocessor
    ↓ Normalizes, tokenizes, groups blocks, creates hashes
3. Candidate Generator
    ↓ Generates candidates using:
    - Regex patterns
    - Semantic search (embeddings)
    - Label proximity
4. Scorer & Validator
    ↓ Combines signals:
    - Regex match
    - Semantic similarity
    - Positional match
    - Value validation
5. Decision Engine
    ↓ Makes decisions:
    - Score ≥ T_HIGH (0.85) → Accept directly
    - Score ≥ T_LOW (0.60) → Normalize deterministically
    - Score < T_LOW → Call LLM (OpenAI API)
    ↓
Final Extracted Values
```

### Key Components

- **TextExtractor**: Extracts text blocks with metadata from PDFs
- **Preprocessor**: Normalizes and processes text blocks
- **CandidateGenerator**: Generates extraction candidates using multiple strategies
- **ScorerValidator**: Scores and validates candidates
- **DecisionEngine**: Makes final decisions on extraction values
- **LLMClient**: Handles OpenAI API calls when needed

## 📝 Example Schema Format

The extraction schema is a JSON object mapping field names to their descriptions:

```json
{
  "field_name_1": "description of what to extract for field 1",
  "field_name_2": "description of what to extract for field 2",
  "field_name_3": "description of what to extract for field 3"
}
```

Example:

```json
{
  "nome": "nome completo da pessoa",
  "cpf": "número de identificação de pessoa física em formato XXX.XXX.XXX-XX",
  "data_nascimento": "data de nascimento no formato DD/MM/AAAA",
  "endereco": "endereço completo de residência"
}
```

##  Output Format

Results are returned in JSON format:

```json
{
  "nome": "João Silva",
  "cpf": "123.456.789-00",
  "data_nascimento": "01/01/1990"
}
```

When using CLI with `--output-dir`, results are saved as:
- Individual files: `{pdf_name}_results.json`
- Combined file: `all_results.json`

##  Development

### Project Structure

```
enter_ai/
├── pdf_extractor/          # Main package
│   ├── __init__.py
│   ├── api.py              # FastAPI application
│   ├── cli.py              # CLI interface
│   ├── config.py           # Configuration settings
│   ├── extractor.py        # Main orchestrator
│   ├── text_extractor.py   # PDF text extraction
│   ├── preprocessor.py     # Text preprocessing
│   ├── candidate_generator.py  # Candidate generation
│   ├── scorer_validator.py     # Scoring and validation
│   ├── decision_engine.py      # Decision engine
│   ├── llm_client.py           # OpenAI client
│   └── pdfs/                   # Default PDF directory
├── static/                 # Web UI files
│   └── index.html
├── results/                # Output directory
├── requirements.txt        # Python dependencies
├── setup.py               # Package setup
├── run_api.py             # API server script
└── README.md              # This file
```

### Running Tests

```bash
# Add test commands here when tests are available
```

##  Troubleshooting

### Common Issues

1. **OpenAI API Key Error**
   - Ensure `.env` file exists with `OPENAI_API_KEY` set
   - Verify the API key is valid

2. **PDF Not Found**
   - Check the PDF path is correct
   - For relative paths, PDFs should be in `pdf_extractor/pdfs/` or current directory

3. **Import Errors**
   - Ensure all dependencies are installed: `pip install -r requirements.txt`
   - Activate your virtual environment

4. **Port Already in Use**
   - Change the port in `run_api.py` or use: `uvicorn pdf_extractor.api:app --port 8001`

