from setuptools import setup, find_packages

setup(
    name="pfe-matcher",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "streamlit",
        "pandas",
        "google-generativeai",
        "pdfplumber",
        "PyPDF2",
        "pytesseract",
        "pdf2image",
        "openpyxl",
        "sentence-transformers",
        "google-auth",
        "google-auth-oauthlib",
        "google-api-python-client",
        "python-dotenv",
        "plotly",
        "dnspython",
        "comet-ml",
        "reportlab"
    ],
)
