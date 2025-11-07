"""LLM client for fallback extraction"""
import json
from typing import Dict, List
from openai import OpenAI
from .config import OPENAI_API_KEY, LLM_MODEL


class LLMClient:
    """Client for OpenAI API (LLM fallback)"""
    
    def __init__(self):
        if not OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY not set in environment variables")
        self.client = OpenAI(api_key=OPENAI_API_KEY)
        self.model = LLM_MODEL
    
    def extract_fields(self,
                      label: str,
                      fields: Dict[str, str],
                      document_text: str,
                      extracted_context: Dict[str, str] = None) -> Dict[str, str]:
        """
        Extract field values using LLM
        
        Args:
            label: Document label
            fields: Dictionary mapping field names to descriptions
            document_text: Document text to extract from
            extracted_context: Already extracted fields (for context)
            
        Returns:
            Dictionary mapping field names to extracted values
        """
        # Build prompt
        fields_description = "\n".join([
            f"- {field_name}: {description}"
            for field_name, description in fields.items()
        ])
        
        context_info = ""
        if extracted_context:
            context_info = f"\n\nAlready extracted fields:\n{json.dumps(extracted_context, indent=2, ensure_ascii=False)}"
        
        prompt = f"""You are a document extraction system. Extract the following fields from the document text.

Document Type: {label}
Document Text:
{document_text}

Fields to extract:
{fields_description}
{context_info}

Instructions:
- Extract the exact value for each field from the document text
- If a field is not found, return empty string ""
- Return only the extracted value, no explanations
- Format values according to their descriptions when possible

Return your response as a JSON object with field names as keys and extracted values as strings.

Example format:
{{
  "field1": "extracted value 1",
  "field2": "extracted value 2"
}}
"""
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a precise document extraction assistant. Return only valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"}
            )
            
            result_text = response.choices[0].message.content
            results = json.loads(result_text)
            
            # Ensure all fields are present
            for field_name in fields.keys():
                if field_name not in results:
                    results[field_name] = ""
            
            return results
        
        except Exception as e:
            # Fallback: return empty strings for all fields
            print(f"Warning: LLM extraction failed: {e}")
            return {field_name: "" for field_name in fields.keys()}

