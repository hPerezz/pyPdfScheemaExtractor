"""CLI interface for PDF extraction"""
import click
import json
import os
from pathlib import Path
from typing import Dict, List
from .extractor import PDFExtractor
import time
import traceback


def load_schema_file(schema_path: str) -> Dict[str, Dict[str, str]]:
    """Load extraction schemas from JSON file"""
    with open(schema_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def process_pdf_file(extractor: PDFExtractor,
                    pdf_path: Path,
                    label: str,
                    extraction_schema: Dict[str, str],
                    output_dir: Path = None) -> Dict[str, str]:
    """Process a single PDF file"""
    try:
        with open(pdf_path, 'rb') as f:
            pdf_bytes = f.read()
        
        click.echo(f"Processing: {pdf_path.name} (label: {label})")
        
        start_ts = time.perf_counter()
        results = extractor.extract(label, extraction_schema, pdf_bytes)
        elapsed_s = time.perf_counter() - start_ts
        
        # Save results if output directory specified
        if output_dir:
            output_path = output_dir / f"{pdf_path.stem}_results.json"
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(results, f, indent=2, ensure_ascii=False)
            click.echo(f"  Results saved to: {output_path}")

        # Report timing and LLM usage
        used_llm = getattr(extractor.decision_engine, 'used_llm_last_call', False)
        click.echo(f"  Time: {elapsed_s:.2f}s | LLM used: {'yes' if used_llm else 'no'}")
        
        return results
    
    except Exception as e:
        click.echo(f"  Error processing {pdf_path.name}: {e}", err=True)
        if click.get_current_context().params.get('verbose'):
            traceback.print_exc()
        return {}


@click.command()
@click.argument('pdf_folder', type=click.Path(exists=True, file_okay=False, path_type=Path))
@click.option('--schema-file', '-s', 
              type=click.Path(exists=True, dir_okay=False, path_type=Path),
              help='JSON file mapping PDF filenames to (label, extraction_schema)')
@click.option('--output-dir', '-o',
              type=click.Path(file_okay=False, path_type=Path),
              help='Directory to save extraction results')
@click.option('--label', '-l', 
              help='Default label for all PDFs (if schema-file not provided)')
@click.option('--schema-json', '-j',
              help='JSON string with extraction schema (if schema-file not provided)')
@click.option('--verbose', '-v', is_flag=True,
              help='Verbose output')
def main(pdf_folder: Path, schema_file: Path, output_dir: Path, 
         label: str, schema_json: str, verbose: bool):
    """
    Extract structured information from PDFs in a folder.
    
    PDF_FOLDER: Folder containing PDF files to process
    
    Examples:
    
    \b
    # Using schema file (JSON format: { "filename.pdf": {"label": "...", "schema": {...}} })
    pdf-extract /path/to/pdfs --schema-file schemas.json --output-dir results
    
    \b
    # Using command line options for all PDFs
    pdf-extract /path/to/pdfs --label "fatura" --schema-json '{"valor": "valor total da fatura", "data": "data de vencimento"}'
    """
    # Initialize extractor
    try:
        extractor = PDFExtractor()
    except Exception as e:
        click.echo(f"Error initializing extractor: {e}", err=True)
        if verbose:
            traceback.print_exc()
        return
    
    # Create output directory if specified
    if output_dir:
        output_dir.mkdir(parents=True, exist_ok=True)
    
    # Get PDF files
    pdf_files = list(pdf_folder.glob('*.pdf'))
    if not pdf_files:
        click.echo(f"No PDF files found in {pdf_folder}", err=True)
        return
    
    click.echo(f"Found {len(pdf_files)} PDF file(s)")
    
    # Load schemas
    schemas = {}
    if schema_file:
        try:
            schemas = load_schema_file(schema_file)
            click.echo(f"Loaded schemas from {schema_file}")
        except Exception as e:
            click.echo(f"Error loading schema file: {e}", err=True)
            return
    elif label and schema_json:
        # Use default schema for all PDFs
        try:
            default_schema = json.loads(schema_json)
            for pdf_file in pdf_files:
                schemas[pdf_file.name] = {
                    'label': label,
                    'schema': default_schema
                }
        except json.JSONDecodeError as e:
            click.echo(f"Invalid JSON schema: {e}", err=True)
            return
    else:
        click.echo("Error: Must provide either --schema-file or both --label and --schema-json", err=True)
        return
    
    # Process each PDF
    all_results = {}
    for pdf_file in pdf_files:
        pdf_name = pdf_file.name
        
        # Get schema for this PDF
        if pdf_name not in schemas:
            click.echo(f"Warning: No schema found for {pdf_name}, skipping", err=True)
            continue
        
        pdf_config = schemas[pdf_name]
        pdf_label = pdf_config['label']
        pdf_schema = pdf_config['schema']
        
        # Process
        results = process_pdf_file(
            extractor, pdf_file, pdf_label, pdf_schema, output_dir
        )
        all_results[pdf_name] = results
        
        if verbose:
            click.echo(f"  Extracted values:")
            for field, value in results.items():
                click.echo(f"    {field}: {value}")
    
    # Summary
    click.echo(f"\nProcessed {len(all_results)} PDF(s) successfully")
    
    # Save combined results if output directory specified
    if output_dir and all_results:
        combined_path = output_dir / "all_results.json"
        with open(combined_path, 'w', encoding='utf-8') as f:
            json.dump(all_results, f, indent=2, ensure_ascii=False)
        click.echo(f"Combined results saved to: {combined_path}")


if __name__ == '__main__':
    main()

