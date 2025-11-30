import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from typing import List, Dict, Any

def plot_score_distribution(matches: List[Dict[str, Any]]):
    """Plot histogram of match scores."""
    if not matches:
        return go.Figure()
        
    scores = [m.get("overall_score", 0) for m in matches]
    df = pd.DataFrame({"Score": scores})
    
    fig = px.histogram(
        df, 
        x="Score", 
        nbins=20, 
        title="Match Score Distribution",
        color_discrete_sequence=['#636EFA']
    )
    fig.update_layout(bargap=0.1)
    return fig

def plot_skills_coverage(cv_data: Dict[str, Any], matches: List[Dict[str, Any]]):
    """Plot heatmap of matched skills (simplified as bar chart for now)."""
    # This is complex to extract from current match structure without deeper parsing
    # We'll plot top companies instead for now as it's more readily available
    return plot_company_breakdown(matches)

def plot_company_breakdown(matches: List[Dict[str, Any]]):
    """Plot bar chart of projects per company."""
    if not matches:
        return go.Figure()
        
    companies = [m.get("company", "Unknown") for m in matches]
    df = pd.DataFrame({"Company": companies})
    counts = df["Company"].value_counts().reset_index()
    counts.columns = ["Company", "Count"]
    
    fig = px.bar(
        counts.head(15), 
        x="Company", 
        y="Count", 
        title="Top Companies by Matches",
        color="Count"
    )
    return fig

def plot_application_timeline(history: List[Dict[str, Any]]):
    """Plot timeline of applications."""
    if not history:
        return go.Figure()
        
    df = pd.DataFrame(history)
    if "sent_at" not in df.columns:
        return go.Figure()
        
    # Convert to datetime
    df["sent_at"] = pd.to_datetime(df["sent_at"])
    df = df.dropna(subset=["sent_at"])
    
    if df.empty:
        return go.Figure()
        
    daily_counts = df.groupby(df["sent_at"].dt.date).size().reset_index(name="Count")
    
    fig = px.line(
        daily_counts, 
        x="sent_at", 
        y="Count", 
        title="Applications Sent Over Time",
        markers=True
    )
    return fig
