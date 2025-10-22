# AI-Powered Regulatory Compliance Checker for Contracts

Short description
This project provides tools and code to analyze contracts for regulatory compliance (GDPR-focused). It uses NLP and rule-based checks to identify potential compliance issues and produce actionable findings.

Key features
- Extracts and analyzes contract text
- Detects GDPR-relevant clauses and risk patterns
- Generates a structured compliance report
- Supports development/testing with sample artifacts included in the repository

Repository contents (high level)
- Source code and modules for parsing/analyzing contracts
- PROBLEM_STATEMENT.md — project goal and scope
- gdpr_compliance_flowchart.mmd — architecture / flowchart (Mermaid)
- temp_agreement.pdf — sample contract (ignored from repo)
- unseen_text.json — sample input data (ignored from repo)
- .venv, .env, logs, and temporary files are excluded via .gitignore

Requirements
- Windows 10/11 (development instructions use PowerShell)
- Python 3.10+ recommended
- Git
- A virtual environment (venv)

Quick setup (Windows PowerShell)
1. Open PowerShell and change to project folder:
   cd 'D:\Infosys_Springboard\project_groq_v'

2. Create and activate virtual environment (if not already):
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1

3. Install dependencies:
   pip install -r requirements.txt
   (If requirements.txt is missing, install project-specific packages as needed)

Environment
- Copy .env.example to .env and set environment variables the app requires.
- Sensitive files are excluded by .gitignore (.env, .venv, logs, temp files).

Common commands
- Run main script (example):
  python -m src.main
  (Replace with the actual entrypoint in the project.)

- Run tests (if tests exist):
  pytest tests/

Repository maintenance
- To start fresh with Git locally (destructive — removes local history):
  Remove-Item -Recurse -Force .git
  git init
  git add .
  git commit -m "Initial commit"
  git branch -M main
  git remote add origin <repo-url>
  git push -u --force origin main

Contributing
- Create an issue describing the change or bug
- Fork, create a branch, implement the fix, add tests, and open a pull request

Notes
- This README is a starting point. Update the "Run" instructions, entrypoints, and dependency list to match the actual project files.
- Add a LICENSE file to declare project license.

Contact
- Repository: https://github.com/DoshikRahul/AI-Powered-Regulatory-Compliance-Checker-for-Contracts
