from groq import Groq, RateLimitError
from pydantic import BaseModel
from dotenv import load_dotenv
from enum import Enum
import os
import json
import time
from API_key_manager import api_manager, make_api_call_with_retry

load_dotenv()

def document_type(json_file):
    """
    Reads extracted text from a JSON file and determines the document type using Groq LLM.
    Uses automatic API key rotation on rate limits.
    """
    
    class DocumentType(str, Enum):
        DPA = "Data Processing Agreement"
        JCA = "Joint Controller Agreement"
        C2C = "Controller-to-Controller Agreement"
        subprocessor = "Processor-to-Subprocessor Agreement"
        SCC = "Standard Contractual Clauses"

    class FindDocumentType(BaseModel):
        document_type: DocumentType

    try:
        # Read text from JSON file
        with open(json_file, "r", encoding="utf-8") as f:
            data = json.load(f)
            text = data.get("text", "")
            
        if not text.strip():
            raise ValueError("No text found in JSON file")

        prompt = f"""
        Analyze this document and determine its type.
        You MUST select EXACTLY one of these options (copy exactly as written):
        1. "Data Processing Agreement"
        2. "Joint Controller Agreement"
        3. "Controller-to-Controller Agreement"
        4. "Processor-to-Subprocessor Agreement"
        5. "Standard Contractual Clauses"

        Look for keywords like:
        - Data Processing Agreement: "data processor", "data controller", "processing activities"
        - Joint Controller Agreement: "joint controller", "joint determination", "shared responsibility"
        - Controller-to-Controller Agreement: "controller to controller", "data sharing between controllers"
        - Processor-to-Subprocessor Agreement: "subprocessor", "processor to processor"
        - Standard Contractual Clauses: "standard contractual clauses", "SCC", "adequacy decision"

        Input text:
        {text[:8000]}

        Respond in this EXACT JSON format:
        {{
            "document_type": "EXACT_TYPE_FROM_LIST_ABOVE"
        }}
        """

        # Make API call with automatic retry and key rotation
        def api_call(client):
            response = client.chat.completions.create(
                messages=[{"role": "user", "content": prompt}],
                model="llama-3.3-70b-versatile",
                response_format={"type": "json_object"},
                temperature=0.3
            )
            return response.choices[0].message.content
        
        response_content = make_api_call_with_retry(api_call, max_retries=5)
        result = json.loads(response_content)
        detected_type = result['document_type']
        
        # Validate that the detected type is one of the expected types
        valid_types = [
            "Data Processing Agreement",
            "Joint Controller Agreement", 
            "Controller-to-Controller Agreement",
            "Processor-to-Subprocessor Agreement",
            "Standard Contractual Clauses"
        ]
        
        if detected_type not in valid_types:
            # Try to find a close match
            for valid_type in valid_types:
                if valid_type.lower() in detected_type.lower() or detected_type.lower() in valid_type.lower():
                    return valid_type
            # Default fallback
            return "Data Processing Agreement"
        
        return detected_type

    except Exception as e:
        raise Exception(f"Error in document type analysis: {str(e)}")

def truncate_text(text, max_chars=8000):
    """Truncate text to fit within token limits while preserving meaning"""
    if len(text) <= max_chars:
        return text
    
    # Try to truncate at sentence boundaries
    truncated = text[:max_chars]
    last_period = truncated.rfind('.')
    if last_period > max_chars * 0.8:
        return truncated[:last_period + 1]
    else:
        return truncated[:max_chars] + "..."

def compare_agreements(unseen_data, template_data):
    """
    Compares two agreements using Groq LLM and returns a structured analysis.
    Uses automatic API key rotation on rate limits.
    """
    
    try:
        # Ensure inputs are strings
        unseen_str = json.dumps(unseen_data) if isinstance(unseen_data, dict) else str(unseen_data)
        template_str = json.dumps(template_data) if isinstance(template_data, dict) else str(template_data)

        prompt = f"""
        Compare these two agreements and provide a detailed analysis:

        Template agreement:
        {truncate_text(template_str)}

        New agreement:
        {truncate_text(unseen_str)}

        Provide analysis in this format:
        1. Missing Clauses (list any clauses present in template but missing in new agreement)
        2. Added Clauses (list any new clauses not in template)
        3. Modified Clauses (list clauses with significant changes)
        4. Compliance Score (0-100)
        5. Key Risks (bullet points of main compliance risks)
        6. Recommendations (specific suggestions to improve compliance)
        """

        # Make API call with automatic retry and key rotation
        def api_call(client):
            response = client.chat.completions.create(
                messages=[{"role": "user", "content": prompt}],
                model="llama-3.3-70b-versatile",
                temperature=0.3
            )
            return response.choices[0].message.content
        
        return make_api_call_with_retry(api_call, max_retries=5)

    except Exception as e:
        raise Exception(f"Error in agreement comparison: {str(e)}")

if __name__ == "__main__":
    try:
        # Test document type identification
        json_file = "unseen_text.json"
        doc_type = document_type(json_file)
        print(f"Document Type: {doc_type}")
        
    except Exception as e:
        print(f"Error in main: {str(e)}")