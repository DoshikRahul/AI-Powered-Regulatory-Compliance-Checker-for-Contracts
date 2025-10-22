import streamlit as st
import schedule
import threading
import time
import json
#import os
from pathlib import Path
from datetime import datetime

import scrapping
import agreement_comparision   
import data_extraction
import notifications

# --------------------------------------------------------------------
# Constants and Configuration
# --------------------------------------------------------------------
JSON_DIR = Path("json_files")
TEMP_DIR = Path("temp")
LOG_DIR = Path("logs")

AGREEMENT_JSON_MAP = {
    "Data Processing Agreement": JSON_DIR / "dpa.json",
    "Joint Controller Agreement": JSON_DIR / "jca.json",
    "Controller-to-Controller Agreement": JSON_DIR / "c2c.json",
    "Processor-to-Subprocessor Agreement": JSON_DIR / "subprocessor.json",
    "Standard Contractual Clauses": JSON_DIR / "scc.json"
}

# --------------------------------------------------------------------
# Setup Functions
# --------------------------------------------------------------------
def setup_directories():
    """Create necessary directories if they don't exist."""
    for directory in [JSON_DIR, TEMP_DIR, LOG_DIR]:
        directory.mkdir(exist_ok=True)

def log_error(error_message):
    """Log errors to file with timestamp."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_file = LOG_DIR / "error_log.txt"
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(f"[{timestamp}] {error_message}\n")

# --------------------------------------------------------------------
# Background Scheduler
# --------------------------------------------------------------------
def run_scheduler():
    """Runs the scraper periodically."""
    try:
        schedule.every(1).hour.do(scrapping.call_scrape_function)
        while True:
            schedule.run_pending()
            time.sleep(60)
    except Exception as e:
        log_error(f"Scheduler error: {str(e)}")

# Start scheduler only once
if "scheduler_started" not in st.session_state:
    threading.Thread(target=run_scheduler, daemon=True).start()
    st.session_state["scheduler_started"] = True

# --------------------------------------------------------------------
# Main Application
# --------------------------------------------------------------------
def process_document(file_path, agreement_type):
    """Process document and return comparison results."""
    try:
        # Extract clauses
        with st.spinner("📄 Extracting clauses..."):
            unseen_data = data_extraction.Clause_extraction(str(file_path))
            st.write("✅ Clause extraction completed")

        # Load template
        template_path = AGREEMENT_JSON_MAP[agreement_type]
        if not template_path.exists():
            st.error(f"Template not found: {template_path}")
            return None

        # Load template data
        with st.spinner("📖 Loading template..."):
            with open(template_path, "r", encoding="utf-8") as f:
                template_data = f.read()

        # Compare agreements
        with st.spinner("🔄 Comparing with template..."):
            return agreement_comparision.compare_agreements(unseen_data, template_data)

    except Exception as e:
        log_error(f"Document processing error: {str(e)}")
        st.error(f"Error processing document: {str(e)}")
        return None

def main():
    st.set_page_config(
        page_title="Contract Compliance Checker",
        page_icon="📜",
        layout="wide"
    )

    st.title("📜 Contract Compliance Checker")
    st.caption("Automated GDPR document compliance using AI-powered clause extraction")

    # Ensure directories exist
    setup_directories()

    # File upload
    uploaded_file = st.file_uploader("📂 Upload an agreement (PDF or DOCX)", type=["pdf", "docx", "doc"])

    if uploaded_file is not None:
        try:
            # Save uploaded file
            temp_path = TEMP_DIR / f"temp_{uploaded_file.name}"
            temp_path.write_bytes(uploaded_file.getvalue())
            
            # Extract text from PDF to JSON first
            temp_json_path = TEMP_DIR / f"temp_{uploaded_file.name}.json"
            
            with st.spinner("📝 Extracting text from document..."):
                data_extraction.extract_text_to_json(str(temp_path), str(temp_json_path))
                st.write("✅ Text extraction completed")

            with st.spinner("🔍 Analyzing document type..."):
                # Identify agreement type using the JSON file
                agreement_type = agreement_comparision.document_type(str(temp_json_path))
                st.success(f"**Detected Document Type:** {agreement_type}")

                if agreement_type in AGREEMENT_JSON_MAP:
                    # Process document
                    result = process_document(temp_path, agreement_type)
                    
                    if result:
                        # Display results
                        st.subheader("📊 Comparison Result")
                        
                        # Try to parse JSON if string
                        if isinstance(result, str):
                            try:
                                result = json.loads(result)
                            except json.JSONDecodeError:
                                pass
                        
                        # Display results
                        if isinstance(result, dict):
                            st.json(result)
                        else:
                            st.write(result)
                        
                        # Send email notification
                        with st.spinner("📧 Sending email notification..."):
                            email_sent = notifications.send_compliance_result(
                                result, 
                                uploaded_file.name, 
                                agreement_type
                            )
                            if email_sent:
                                st.success("✅ Email notification sent successfully!")
                            else:
                                st.warning("⚠️ Failed to send email notification")
                else:
                    st.error("🚫 This document type is not under GDPR compliance.")
                    st.info(f"Supported types: {', '.join(AGREEMENT_JSON_MAP.keys())}")

        except Exception as e:
            log_error(f"Main application error: {str(e)}")
            st.error(f"An error occurred: {str(e)}")
            
            # Send error notification email
            error_message = f"""
Document Processing Failed

Document: {uploaded_file.name if uploaded_file else 'Unknown'}
Error: {str(e)}

The system encountered an error while processing your document.
Please check if:
- The document format is correct (PDF or DOCX)
- The document contains readable text
- API rate limits haven't been exceeded

Check system logs for more details.
"""
            notifications.send_notification("❌ Document Processing Failed", error_message)

        finally:
            # Cleanup
            if 'temp_path' in locals() and temp_path.exists():
                temp_path.unlink(missing_ok=True)
            if 'temp_json_path' in locals() and temp_json_path.exists():
                temp_json_path.unlink(missing_ok=True)

if __name__ == "__main__":
    main()