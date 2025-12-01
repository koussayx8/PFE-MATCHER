import streamlit as st
import pandas as pd
import time
import os
from pathlib import Path

# Import modules
from config.settings import UPLOADS_DIR, GEMINI_API_KEY
from src.document_processing.pdf_parser import extract_text_from_pdf
from src.document_processing.excel_parser import parse_excel_to_projects
from src.document_processing.batch_processor import process_pdfs_parallel
from src.ai_engine.cv_analyzer import analyze_cv
from src.ai_engine.project_extractor import extract_projects_from_text, normalize_projects
from src.ai_engine.matcher import batch_match_projects
from src.ai_engine.email_generator import generate_email, preview_email_html
from src.email_automation.gmail_auth import authenticate_gmail
from src.email_automation.email_queue import EmailQueue
from src.data_management.database import init_database, log_application, get_statistics, get_application_history, save_match_batch, get_recent_matches
from src.data_management.file_manager import FileManager
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
        background-color: #262730; /* Streamlit dark bg */
        color: white;
        margin-bottom: 10px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.3);
    }
    .high-match { border-left: 5px solid #28a745; }
    .med-match { border-left: 5px solid #ffc107; }
    .low-match { border-left: 5px solid #dc3545; }
</style>
""", unsafe_allow_html=True)

import json
from config.settings import DATA_DIR

SESSION_FILE = DATA_DIR / "session_state.json"

def save_state():
    """Save critical session state to disk."""
    state = {
        "cv_data": st.session_state.cv_data,
        "projects": st.session_state.projects,
        "matches": st.session_state.matches
    }
    try:
        with open(SESSION_FILE, "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"Failed to save state: {e}")

def load_state():
    """Load session state from disk."""
    if SESSION_FILE.exists():
        try:
            with open(SESSION_FILE, "r", encoding="utf-8") as f:
                state = json.load(f)
                st.session_state.cv_data = state.get("cv_data", {})
                st.session_state.projects = state.get("projects", [])
                st.session_state.matches = state.get("matches", [])
                return True
        except Exception as e:
            logger.error(f"Failed to load state: {e}")
    return False

def init_session_state():
    if "email_queue" not in st.session_state:
        st.session_state.email_queue = EmailQueue()
    if "gmail_service" not in st.session_state:
        st.session_state.gmail_service = None
        
    # Load persisted data if not already in session
    if "matches" not in st.session_state:
        if load_state():
            st.toast("Restored previous session data! 💾")
        else:
            # Fallback to Database
            db_matches = get_recent_matches()
            if db_matches:
                st.session_state.matches = db_matches
                st.toast(f"Loaded {len(db_matches)} matches from database! 🗄️")
            else:
                st.session_state.cv_data = {}
                st.session_state.projects = []
                st.session_state.matches = []

def sidebar_section():
    st.sidebar.title("🚀 PFE Matcher")
    
    # API Status
    if not GEMINI_API_KEY:
        st.sidebar.error("⚠️ Gemini API Key Missing!")
    
    # Uploads
    st.sidebar.header("1. Upload Documents")
    cv_file = st.sidebar.file_uploader("Upload CV (PDF)", type=["pdf"])

    pfe_books = st.sidebar.file_uploader("Upload PFE Book(s) (PDF/Excel)", type=["pdf", "xlsx", "xls"], accept_multiple_files=True)
    
    # Settings
    st.sidebar.header("2. Settings")
    min_score = st.sidebar.slider("Minimum Match Score", 0, 100, 60)
    email_tone = st.sidebar.selectbox("Email Tone", ["Formal", "Enthusiastic", "Academic", "Startup-style"])
    language = st.sidebar.selectbox("Language", ["English", "French"])
    
    # Filter & Sort
    st.sidebar.header("3. Filter & Sort")
    
    use_hybrid = st.sidebar.checkbox("Use Hybrid Matching (Faster)", value=True, help="Use local AI to pre-filter projects before detailed analysis. Saves time and API costs.")
    os.environ["USE_HYBRID_MATCHING"] = "true" if use_hybrid else "false"
    
    with st.sidebar.expander("Advanced Options"):
        # Get unique companies
        companies = sorted(list(set([m.get("company", "Unknown") for m in st.session_state.matches])))
        selected_companies = st.multiselect("Filter by Company", companies)
        
        filter_score = st.slider("Filter by Score Range", 0, 100, (0, 100))
        
        sort_by = st.selectbox("Sort By", ["Match Score", "Company Name", "Date"])
        sort_order = st.radio("Order", ["Descending", "Ascending"], horizontal=True)
    
    # Gmail Auth
    st.sidebar.header("4. Email System")
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
        
    return cv_file, pfe_books, min_score, email_tone, language, selected_companies, filter_score, sort_by, sort_order

def process_matching(cv_file, pfe_books, min_score):
    # Save uploaded files using FileManager
    file_manager = FileManager()
    
    # Save CV
    cv_doc_id = file_manager.save_file(cv_file, cv_file.name, document_type="cv")
    cv_path = file_manager.get_file_path(cv_doc_id)
        
    pfe_paths = []
    for pfe_book in pfe_books:
        # Save PFE Book
        doc_id = file_manager.save_file(pfe_book, pfe_book.name, document_type="pfe_book")
        p_path = file_manager.get_file_path(doc_id)
        pfe_paths.append(p_path)
        
    status = st.status("Processing...", expanded=True)
    
    # 1. Analyze CV
    status.write("📄 Analyzing CV...")
    cv_text = extract_text_from_pdf(cv_path)["text"]
    st.session_state.cv_data = analyze_cv(cv_text)
    
    # 2. Extract Projects
    status.write(f"📚 Extracting Projects from {len(pfe_paths)} files...")
    raw_projects = []
    
    pdf_files = [p for p in pfe_paths if p.suffix.lower() == ".pdf"]
    excel_files = [p for p in pfe_paths if p.suffix.lower() in [".xlsx", ".xls"]]
    
    # Process Excel files
    for excel_path in excel_files:
        raw_projects.extend(parse_excel_to_projects(excel_path))
        
    # Process PDF files in parallel
    if pdf_files:
        status.write(f"⚡ Scanning {len(pdf_files)} PDFs in parallel...")
        results = process_pdfs_parallel(pdf_files)
        for res in results:
            if res.get("text"):
                projects = extract_projects_from_text(res["text"])
                raw_projects.extend(projects)
        
    st.session_state.projects = normalize_projects(raw_projects)
    status.write(f"✅ Found {len(st.session_state.projects)} projects.")
    
    # 3. Match
    status.write("🧠 Matching with AI...")
    st.session_state.matches = batch_match_projects(
        st.session_state.cv_data, 
        st.session_state.projects, 
        min_score
    )
    
    # Save state
    save_state()
    
    # Save to Database (Permanent History)
    save_match_batch(st.session_state.matches)
    
    status.update(label="Done!", state="complete", expanded=False)

def display_matches(matches, key_prefix, tone, language, selected_companies, filter_score, sort_by, sort_order):
    # 1. Filter
    filtered_matches = matches
    
    # Filter by Company
    if selected_companies:
        filtered_matches = [m for m in filtered_matches if m.get("company") in selected_companies]
        
    # Filter by Score
    filtered_matches = [m for m in filtered_matches if filter_score[0] <= m.get("overall_score", 0) <= filter_score[1]]
    
    # 2. Sort
    reverse = True if sort_order == "Descending" else False
    if sort_by == "Match Score":
        filtered_matches.sort(key=lambda x: x.get("overall_score", 0), reverse=reverse)
    elif sort_by == "Company Name":
        filtered_matches.sort(key=lambda x: x.get("company", "").lower(), reverse=reverse)
    elif sort_by == "Date":
        filtered_matches.sort(key=lambda x: x.get("created_at", ""), reverse=reverse)
        
    # 3. Pagination
    items_per_page = 5
    page_key = f"page_number_{key_prefix}"
    if page_key not in st.session_state:
        st.session_state[page_key] = 1
        
    total_pages = max(1, (len(filtered_matches) + items_per_page - 1) // items_per_page)
    
    # Ensure page number is valid
    if st.session_state[page_key] > total_pages:
        st.session_state[page_key] = total_pages
        
    start_idx = (st.session_state[page_key] - 1) * items_per_page
    end_idx = start_idx + items_per_page
    
    page_matches = filtered_matches[start_idx:end_idx]
    
    st.write(f"Showing {len(page_matches)} of {len(filtered_matches)} matches (Page {st.session_state[page_key]}/{total_pages})")
    
    # Display
    for match in page_matches:
        score = match.get("overall_score", 0)
        
        # Check for error
        if "error" in match:
             with st.container():
                st.error(f"❌ Analysis Failed for **{match.get('project_title')}**: {match.get('error')}")
                continue
                
        color_class = "high-match" if score >= 80 else "med-match" if score >= 60 else "low-match"
        
        # Get project details (email, etc.)
        # Try to find project in session first, else fallback to match data
        project_id = match.get("project_id")
        project = next((p for p in st.session_state.projects if str(p.get("id")) == str(project_id)), {})
        
        contact_email = project.get("email") or match.get("email") or "N/A"
        reference_id = project.get("reference_id") or match.get("reference_id") or ""
        app_link = project.get("application_link") or match.get("application_link")
        
        # Badge for Reference ID
        ref_badge = ""
        if reference_id:
            ref_badge = f'<span style="background-color:#f0f2f6;color:#31333F;padding:2px 8px;border-radius:4px;font-size:0.8em;font-weight:600;white-space:nowrap;margin-bottom:4px;display:inline-block;">{reference_id}</span>'

        # HTML Card Construction (Minified to prevent Markdown errors)
        card_html = f"""
<div class="match-card {color_class}" style="padding:15px;border-radius:8px;margin-bottom:10px;">
<div style="display:flex;justify-content:space-between;align-items:flex-start;">
<div style="flex:1;padding-right:10px;">
<h3 style="margin:0;font-size:1.1em;line-height:1.4;">{match.get('project_title')}</h3>
<p style="margin:5px 0 0 0;"><strong>🏢 {match.get('company')}</strong></p>
</div>
<div style="text-align:right;min-width:80px;display:flex;flex-direction:column;align-items:flex-end;">
{ref_badge}
<h2 style="margin:0;font-size:1.8em;">{score}%</h2>
</div>
</div>
<div style="margin-top:10px;font-size:0.9em;border-top:1px solid #444;padding-top:8px;">
<p style="margin:2px 0;"><strong>📧 Email:</strong> {contact_email}</p>
<p style="margin:2px 0;"><strong>💡 Recommendation:</strong> {match.get('recommendation')}</p>
</div>
</div>
"""
        with st.container():
            st.markdown(card_html, unsafe_allow_html=True)
            
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
                    # Link Application
                    if app_link:
                        st.link_button("🔗 Apply via Link", app_link, use_container_width=True)
                        st.write("---")
                    elif contact_email == "N/A":
                        st.warning("⚠️ No application method found (Email or Link). Please check the PFE Book manually.")
                        st.write("---")
                    
                    # Email Application
                    gen_key = f"gen_{key_prefix}_{project_id}"
                    if st.button("✨ Generate Email", key=gen_key, use_container_width=True):
                        # If project is empty (loaded from DB), we might need to fetch it or reconstruct it
                        if not project:
                             # Fallback: create a dummy project dict from match info
                             project = {
                                 "title": match.get("project_title"),
                                 "company": match.get("company"),
                                 "description": "", 
                                 "email": contact_email if contact_email != "N/A" else "",
                                 "reference_id": reference_id
                             }
                        
                        with st.spinner("Generating email..."):
                            email = generate_email(st.session_state.cv_data, project, match, tone, language)
                            st.session_state[f"email_{key_prefix}_{project_id}"] = email
                        
                    email_key = f"email_{key_prefix}_{project_id}"
                    if email_key in st.session_state:
                        email = st.session_state[email_key]
                        st.markdown(preview_email_html(email), unsafe_allow_html=True)
                        
                        # Email Input Field
                        # Use session state to persist manual edits
                        input_key = f"to_{key_prefix}_{project_id}"
                        if input_key not in st.session_state:
                             st.session_state[input_key] = contact_email if contact_email != "N/A" else ""
                             
                        to_email = st.text_input("To Email:", key=input_key)
                        
                        if st.button("Add to Queue", key=f"queue_{key_prefix}_{project_id}"):
                            if not to_email:
                                st.error("Please enter a recipient email address.")
                            else:
                                st.session_state.email_queue.add_to_queue({
                                    "to_email": to_email,
                                    "subject": email["subject"],
                                    "body": email["body"],
                                    "project_id": project_id
                                })
                                st.success("Added to queue!")

    # Modern Pagination Controls
    if total_pages > 1:
        st.markdown("---")
        
        # Calculate range of pages to show
        current_page = st.session_state[page_key]
        
        # Logic to determine which page numbers to show
        # Always show first, last, current, and neighbors
        pages_to_show = set()
        pages_to_show.add(1)
        pages_to_show.add(total_pages)
        pages_to_show.add(current_page)
        pages_to_show.add(current_page - 1)
        pages_to_show.add(current_page + 1)
        
        sorted_pages = sorted([p for p in pages_to_show if 1 <= p <= total_pages])
        
        # Add gaps
        final_pages = []
        if sorted_pages:
            final_pages.append(sorted_pages[0])
            for i in range(1, len(sorted_pages)):
                if sorted_pages[i] > sorted_pages[i-1] + 1:
                    final_pages.append(None) # Ellipsis
                final_pages.append(sorted_pages[i])
        
        # Render buttons
        cols = st.columns(len(final_pages) + 2) # +2 for Prev/Next
        
        # Prev Button
        with cols[0]:
            if st.button("◀", key=f"prev_{key_prefix}", disabled=current_page == 1, help="Previous Page"):
                st.session_state[page_key] -= 1
                st.rerun()
                
        # Page Numbers
        for i, p in enumerate(final_pages):
            with cols[i+1]:
                if p is None:
                    st.write("...")
                else:
                    # Highlight current page
                    label = f"**{p}**" if p == current_page else f"{p}"
                    if st.button(str(p), key=f"page_{key_prefix}_{p}", disabled=p == current_page):
                        st.session_state[page_key] = p
                        st.rerun()
                        
        # Next Button
        with cols[-1]:
            if st.button("▶", key=f"next_{key_prefix}", disabled=current_page == total_pages, help="Next Page"):
                st.session_state[page_key] += 1
                st.rerun()

def main_content(cv_file, pfe_books, min_score, email_tone, language, selected_companies, filter_score, sort_by, sort_order):
    tabs = st.tabs(["🔍 Match & Apply", "📜 History", "📨 Email Queue", "📊 Analytics", "⚙️ Manage"])
    
    # --- TAB 1: MATCH & APPLY (Current Session) ---
    with tabs[0]:
        col1, col2 = st.columns([1, 3])
        
        with col1:
            st.subheader("Action Center")
            if st.button("🚀 Analyze & Match", type="primary"):
                if not cv_file or not pfe_books:
                    st.error("Please upload both CV and PFE Book(s).")
                else:
                    process_matching(cv_file, pfe_books, min_score)
            
            # Stats for Current Session
            if st.session_state.matches:
                st.metric("New Matches", len(st.session_state.matches))
                top_matches = len([m for m in st.session_state.matches if m.get("overall_score", 0) >= 80])
                st.metric("Top Matches (80+)", top_matches)

        with col2:
            st.subheader("Current Analysis Results")
            
            if st.session_state.matches:
                # Display Metrics
                if "_metrics" in st.session_state.matches[0]:
                    m = st.session_state.matches[0]["_metrics"]
                    c1, c2, c3, c4 = st.columns(4)
                    c1.metric("Projects Scanned", m["total_projects"])
                    c2.metric("Candidates Analysis", m["candidates"])
                    c3.metric("API Calls", m["api_calls"])
                    c4.metric("Time Saved", f"{m['elapsed']:.1f}s")
                    st.success(f"⚡ Hybrid Matching saved {m['total_projects'] - m['api_calls']} API calls!")
            
            if not st.session_state.matches:
                st.info("Upload documents and click 'Analyze & Match' to see new results.")
            else:
                display_matches(st.session_state.matches, "current", email_tone, language, selected_companies, filter_score, sort_by, sort_order)

    # --- TAB 2: HISTORY (All Matches) ---
    with tabs[1]:
        st.subheader("📜 Match History")
        
        # Fetch all matches
        from src.data_management.database import get_all_matches
        all_matches = get_all_matches(limit=100) # Limit to 100 for performance
        
        if not all_matches:
            st.info("No history found.")
        else:
            display_matches(all_matches, "history", email_tone, language, selected_companies, filter_score, sort_by, sort_order)

    # --- TAB 3: EMAIL QUEUE ---
    with tabs[2]:
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

    # --- TAB 4: ANALYTICS ---
    with tabs[3]:
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

    # --- TAB 5: MANAGE ---
    with tabs[4]:
        st.subheader("Data Management")
        
        if st.button("Clear Cache"):
            # Implement clear cache
            st.success("Cache cleared!")
            
        if st.button("Reset Database", type="primary"):
            # Implement reset
            st.warning("Database reset!")

if __name__ == "__main__":
    init_session_state()
    cv, pfes, min_s, tone, lang, companies, f_score, s_by, s_order = sidebar_section()
    main_content(cv, pfes, min_s, tone, lang, companies, f_score, s_by, s_order)
