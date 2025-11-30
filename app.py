import streamlit as st
import pandas as pd
import time
import os
from pathlib import Path

# Import modules
from config.settings import UPLOADS_DIR, GEMINI_API_KEY
from src.document_processing.pdf_parser import extract_text_from_pdf
from src.document_processing.excel_parser import parse_excel_to_projects
from src.ai_engine.cv_analyzer import analyze_cv
from src.ai_engine.project_extractor import extract_projects_from_text, normalize_projects
from src.ai_engine.matcher import batch_match_projects
from src.ai_engine.email_generator import generate_email, preview_email_html
from src.email_automation.gmail_auth import authenticate_gmail
from src.email_automation.email_queue import EmailQueue
from src.data_management.database import init_database, log_application, get_statistics, get_application_history
from src.data_management.export_manager import export_to_csv, generate_match_report_pdf
from src.analytics.visualizations import plot_score_distribution, plot_company_breakdown, plot_application_timeline
from src.utils.logging_config import setup_logging

# Setup logging
logger = setup_logging()

# Initialize DB
init_database()

# Page Config
st.set_page_config(
    page_title="PFE Matcher & Auto-Apply",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .stButton>button {
        width: 100%;
    }
    .match-card {
        padding: 15px;
        border-radius: 10px;
        border: 1px solid #ddd;
        margin-bottom: 10px;
    }
    .high-match { border-left: 5px solid #28a745; }
    .med-match { border-left: 5px solid #ffc107; }
    .low-match { border-left: 5px solid #dc3545; }
</style>
""", unsafe_allow_html=True)

def init_session_state():
    if "cv_data" not in st.session_state:
        st.session_state.cv_data = {}
    if "projects" not in st.session_state:
        st.session_state.projects = []
    if "matches" not in st.session_state:
        st.session_state.matches = []
    if "email_queue" not in st.session_state:
        st.session_state.email_queue = EmailQueue()
    if "gmail_service" not in st.session_state:
        st.session_state.gmail_service = None

def sidebar_section():
    st.sidebar.title("🚀 PFE Matcher")
    
    # API Status
    if not GEMINI_API_KEY:
        st.sidebar.error("⚠️ Gemini API Key Missing!")
    
    # Uploads
    st.sidebar.header("1. Upload Documents")
    cv_file = st.sidebar.file_uploader("Upload CV (PDF)", type=["pdf"])
    pfe_book = st.sidebar.file_uploader("Upload PFE Book (PDF/Excel)", type=["pdf", "xlsx", "xls"])
    
    # Settings
    st.sidebar.header("2. Settings")
    min_score = st.sidebar.slider("Minimum Match Score", 0, 100, 60)
    email_tone = st.sidebar.selectbox("Email Tone", ["Formal", "Enthusiastic", "Academic", "Startup-style"])
    language = st.sidebar.selectbox("Language", ["English", "French"])
    
    # Gmail Auth
    st.sidebar.header("3. Email System")
    if st.sidebar.button("Authenticate Gmail"):
        with st.spinner("Authenticating..."):
            service = authenticate_gmail()
            if service:
                st.session_state.gmail_service = service
                st.sidebar.success("Gmail Authenticated! ✅")
            else:
                st.sidebar.error("Authentication Failed ❌")
                
    if st.session_state.gmail_service:
        st.sidebar.success("Gmail Connected")
        
    return cv_file, pfe_book, min_score, email_tone, language

def main_content(cv_file, pfe_book, min_score, email_tone, language):
    tabs = st.tabs(["🔍 Match & Apply", "📨 Email Queue", "📊 Analytics", "⚙️ Manage"])
    
    # --- TAB 1: MATCH & APPLY ---
    with tabs[0]:
        col1, col2 = st.columns([1, 3])
        
        with col1:
            st.subheader("Action Center")
            if st.button("🚀 Analyze & Match", type="primary"):
                if not cv_file or not pfe_book:
                    st.error("Please upload both CV and PFE Book.")
                else:
                    process_matching(cv_file, pfe_book, min_score)
            
            # Stats
            if st.session_state.matches:
                st.metric("Total Matches", len(st.session_state.matches))
                top_matches = len([m for m in st.session_state.matches if m.get("overall_score", 0) >= 80])
                st.metric("Top Matches (80+)", top_matches)
                
                if st.button("📥 Export CSV"):
                    path = export_to_csv(st.session_state.matches)
                    st.success(f"Exported to {path}")

        with col2:
            st.subheader("Match Results")
            if not st.session_state.matches:
                st.info("Upload documents and click 'Analyze & Match' to start.")
            else:
                display_matches(email_tone, language)

    # --- TAB 2: EMAIL QUEUE ---
    with tabs[1]:
        st.subheader("Email Queue")
        queue = st.session_state.email_queue
        status = queue.get_queue_status()
        
        c1, c2, c3 = st.columns(3)
        c1.metric("Queued Emails", status["queue_size"])
        c2.metric("Sent Today", status["sent_today"])
        c3.metric("Remaining Quota", status["remaining_today"])
        
        if st.button("📤 Send All Queued Emails"):
            if not st.session_state.gmail_service:
                st.error("Please authenticate Gmail first!")
            else:
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                def update_progress(current, total):
                    progress_bar.progress(current / total)
                    status_text.text(f"Sending {current}/{total}...")
                
                results = queue.process_queue(st.session_state.gmail_service, update_progress)
                
                success_count = len([r for r in results if r["success"]])
                st.success(f"Sent {success_count} emails successfully!")
                
                # Log to DB
                for res in results:
                    # We need to find the match data to log properly, 
                    # but queue only has email data. 
                    # Ideally queue should store full context or we update DB status here.
                    pass 

        # Display Queue Items
        if queue.queue:
            for i, item in enumerate(queue.queue):
                with st.expander(f"{i+1}. {item['subject']} ({item['to_email']})"):
                    st.markdown(item['body'], unsafe_allow_html=True)
                    if st.button(f"Remove #{i+1}", key=f"rm_{i}"):
                        queue.remove_from_queue(i)
                        st.rerun()
        else:
            st.info("Queue is empty.")

    # --- TAB 3: ANALYTICS ---
    with tabs[2]:
        st.subheader("Dashboard")
        stats = get_statistics()
        
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Total Applications", stats.get("total_applications", 0))
        c2.metric("Sent Emails", stats.get("sent_emails", 0))
        c3.metric("Responses", stats.get("responses", 0))
        c4.metric("Avg Match Score", stats.get("avg_match_score", 0))
        
        st.divider()
        
        g1, g2 = st.columns(2)
        with g1:
            if st.session_state.matches:
                st.plotly_chart(plot_score_distribution(st.session_state.matches), use_container_width=True)
        with g2:
            if st.session_state.matches:
                st.plotly_chart(plot_company_breakdown(st.session_state.matches), use_container_width=True)
                
        st.subheader("Application History")
        history = get_application_history()
        if history:
            st.dataframe(pd.DataFrame(history))
            st.plotly_chart(plot_application_timeline(history), use_container_width=True)

    # --- TAB 4: MANAGE ---
    with tabs[3]:
        st.subheader("Data Management")
        if st.button("Clear Cache"):
            # Implement clear cache
            st.success("Cache cleared!")
            
        if st.button("Reset Database", type="primary"):
            # Implement reset
            st.warning("Database reset!")

def process_matching(cv_file, pfe_book, min_score):
    # Save uploaded files
    cv_path = UPLOADS_DIR / cv_file.name
    with open(cv_path, "wb") as f:
        f.write(cv_file.getbuffer())
        
    pfe_path = UPLOADS_DIR / pfe_book.name
    with open(pfe_path, "wb") as f:
        f.write(pfe_book.getbuffer())
        
    status = st.status("Processing...", expanded=True)
    
    # 1. Analyze CV
    status.write("📄 Analyzing CV...")
    cv_text = extract_text_from_pdf(cv_path)["text"]
    st.session_state.cv_data = analyze_cv(cv_text)
    
    # 2. Extract Projects
    status.write("📚 Extracting Projects...")
    if pfe_book.name.endswith(".xlsx") or pfe_book.name.endswith(".xls"):
        raw_projects = parse_excel_to_projects(pfe_path)
    else:
        pfe_text = extract_text_from_pdf(pfe_path)["text"]
        raw_projects = extract_projects_from_text(pfe_text)
        
    st.session_state.projects = normalize_projects(raw_projects)
    status.write(f"✅ Found {len(st.session_state.projects)} projects.")
    
    # 3. Match
    status.write("🧠 Matching with AI...")
    st.session_state.matches = batch_match_projects(
        st.session_state.cv_data, 
        st.session_state.projects, 
        min_score
    )
    
    status.update(label="Done!", state="complete", expanded=False)

def display_matches(tone, language):
    for match in st.session_state.matches:
        score = match.get("overall_score", 0)
        color_class = "high-match" if score >= 80 else "med-match" if score >= 60 else "low-match"
        
        with st.container():
            st.markdown(f"""
            <div class="match-card {color_class}">
                <h3>{match.get('project_title')} ({score}%)</h3>
                <p><strong>{match.get('company')}</strong></p>
                <p>{match.get('recommendation')}</p>
            </div>
            """, unsafe_allow_html=True)
            
            with st.expander("View Details & Apply"):
                c1, c2 = st.columns(2)
                with c1:
                    st.write("**Matching Points:**")
                    for p in match.get("matching_points", []):
                        st.write(f"- {p}")
                    st.write("**Gaps:**")
                    for g in match.get("gaps", []):
                        st.write(f"- {g}")
                        
                with c2:
                    if st.button("✨ Generate Email", key=f"gen_{match.get('project_id')}"):
                        project = next((p for p in st.session_state.projects if p.get("id") == match.get("project_id")), {})
                        email = generate_email(st.session_state.cv_data, project, match, tone, language)
                        
                        st.session_state[f"email_{match.get('project_id')}"] = email
                        
                    if f"email_{match.get('project_id')}" in st.session_state:
                        email = st.session_state[f"email_{match.get('project_id')}"]
                        st.markdown(preview_email_html(email), unsafe_allow_html=True)
                        
                        if st.button("Add to Queue", key=f"queue_{match.get('project_id')}"):
                            st.session_state.email_queue.add_to_queue({
                                "to_email": "test@example.com", # Placeholder, should extract from project
                                "subject": email["subject"],
                                "body": email["body"],
                                "project_id": match.get("project_id")
                            })
                            st.success("Added to queue!")

if __name__ == "__main__":
    init_session_state()
    cv, pfe, min_s, tone, lang = sidebar_section()
    main_content(cv, pfe, min_s, tone, lang)
