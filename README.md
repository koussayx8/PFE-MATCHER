# PFE Project Matcher & Auto-Apply System

## 🎯 Project Mission

An intelligent automation system that transforms the exhausting PFE job search process into a 5-minute automated workflow. The system reads PFE opportunity books (PDF/Excel), uses AI to match projects against a student's CV, generates personalized application emails with intelligent context injection, and sends them automatically via Gmail.

## 🚀 Features

- **Intelligent Document Processing**: Extracts projects from PDF and Excel PFE books with high accuracy.
- **AI-Powered Matching**: Uses Gemini Pro to analyze CVs and match them against projects based on skills, domain, and experience.
- **Automated Email Generation**: Generates personalized emails for each match, injecting relevant CV snippets and company research.
- **Gmail Integration**: Sends emails automatically with rate limiting and queue management.
- **Analytics Dashboard**: Tracks application status, response rates, and match quality metrics.
- **Export Capabilities**: Exports match reports to CSV and PDF.

## 🛠️ Tech Stack

- **Frontend**: Streamlit
- **AI Engine**: Google Gemini Pro, Perplexity AI (optional), Sentence Transformers
- **Backend**: Python
- **Database**: SQLite
- **Monitoring**: Comet ML

## 📦 Installation

### Prerequisites

- Python 3.10+
- Google Cloud Project with Gmail API enabled
- Gemini API Key

### Setup Steps

1. Clone the repository:

   ```bash
   git clone <repository-url>
   cd pfe-matcher
   ```

2. Create a virtual environment:

   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

4. Configure environment variables:

   - Copy `.env.example` to `.env`
   - Fill in your API keys and configuration

5. Setup Gmail OAuth:
   - Place your `credentials.json` in `config/`

### Usage

Run the application:

```bash
streamlit run app.py
```

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         USER INTERFACE                          │
│                    (Streamlit Web Application)                  │
└────────────────────────────┬────────────────────────────────────┘
                             │
┌────────────────────────────▼────────────────────────────────────┐
│                    ORCHESTRATION LAYER                          │
│              (Main Application Logic - app.py)                  │
└────────────────────────────┬────────────────────────────────────┘
                             │
            ┌────────────────┼────────────────┐
            ▼                ▼                ▼
┌──────────────────┐  ┌──────────────┐  ┌──────────────────┐
│  DOCUMENT        │  │   AI/ML      │  │  EMAIL          │
│  PROCESSING      │  │   MATCHING   │  │  AUTOMATION     │
└──────────────────┘  └──────────────┘  └──────────────────┘
```

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## 📄 License

MIT License
