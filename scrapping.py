import os
import requests
import json
import data_extraction  # ensure your module name matches the actual file
import notifications

def scrape_data(url, name):
    """Download PDF file from URL."""
    response = requests.get(url, stream=True)
    if response.status_code == 200:
        with open(name, "wb") as f:
            for chunk in response.iter_content(chunk_size=1024):
                if chunk:
                    f.write(chunk)
        print(f"✅ Download successful: {name}")
    else:
        print(f"❌ Failed to download ({response.status_code}) from {url}")

def call_scrape_function():
    """Scrape agreements, extract clauses, and store in JSON files."""
    DOCUMENT_MAP = {
        
        #"SCC":{
        #    "json_file": "json_files/scc.json",
        #    "link": r"https://www.miller-insurance.com/assets/PDF-Downloads/Standard-Contractual-Clauses-SCCs.pdf"
        #},
        "DPA" :{
            "json_file": "json_files/dpa.json",
            "link": r"https://www.benchmarkone.com/wp-content/uploads/2018/05/GDPR-Sample-Agreement.pdf"
        },
        "JCA" :{
            "json_file": "json_files/jca.json",
            "link": r"https://www.surf.nl/files/2019-11/model-joint-controllership-agreement.pdf"
        },
        "C2C" :{
            "json_file": "json_files/c2c.json",
            "link": r"https://www.fcmtravel.com/sites/default/files/2020-03/2-Controller-to-controller-data-privacy-addendum.pdf"
        },
        "Subprocessor" :{
            "json_file": "json_files/subprocessor.json",
            "link": r"https://greaterthan.eu/wp-content/uploads/Personal-Data-Sub-Processor-Agreement-2024-01-24.pdf"
        }
    }

    # Ensure output folder exists
    os.makedirs("json_files", exist_ok=True)
    temp_agreement = "temp_agreement.pdf"

    try:
        for key, value in DOCUMENT_MAP.items():
            print(f"\n🔹 Processing {key} Agreement...")
            scrape_data(value["link"], temp_agreement)

            # Extract clauses from the downloaded PDF
            clauses = data_extraction.Clause_extraction(temp_agreement)
            
            # Parse if it's a string response
            if isinstance(clauses, str):
                clauses = json.loads(clauses)

            # Save extracted clauses to JSON
            with open(value["json_file"], "w", encoding="utf-8") as f:
                json.dump(clauses, f, indent=2, ensure_ascii=False)
            print(f"💾 Clauses saved to {value['json_file']}")
    
    except Exception as e:
        # Send error notification
        error_message = f"""
Template Scraping Failed

Error: {str(e)}

The system encountered an error while trying to scrape and process GDPR agreement templates.
This may be due to:
- API rate limits
- Network issues
- File processing errors

Please check the system logs for more details.
"""
        notifications.send_notification("⚠️ Template Scraping Failed", error_message)
        print(f"❌ Error during scraping: {str(e)}")
        raise

# Comment out to prevent auto-execution on import (runs on schedule only)
# call_scrape_function()
