# CV Analysis Prompt
CV_ANALYSIS_PROMPT = """
You are an expert HR AI assistant. Analyze the following CV text and extract structured information.
Return the output as a JSON object with the following keys:
- "personal_info": {{"name": str, "email": str, "phone": str, "linkedin": str, "github": str, "portfolio": str}}
- "education": [{{"degree": str, "institution": str, "year": str, "details": str}}]
- "experience": [{{"role": str, "company": str, "duration": str, "details": str}}]
- "skills": {{"technical": [str], "soft": [str], "languages": [str], "tools": [str]}}
- "projects": [{{"name": str, "description": str, "technologies": [str]}}]
- "domains_of_interest": [str] (Infer these from the CV)

CV TEXT:
{cv_text}
"""

# Project Extraction Prompt
PROJECT_EXTRACTION_PROMPT = """
You are an expert data extraction AI. Extract PFE (End of Studies Project) opportunities from the following text.
The text may contain multiple projects. Identify each distinct project.
Return the output as a JSON object with a key "projects" containing a list of objects.
Each project object must have:
- "title": str (The project title)
- "description": str (Full description)
- "company": str (Company name, if available)
- "technologies": [str] (List of required technologies)
- "domain": str (e.g., "Web Development", "Data Science", "Embedded Systems")
- "supervisor": str (Supervisor name if available, else "")
- "email": str (Contact email if available, else "")
- "reference_id": str (Any ID, Code, or Ref mentioned, else "")
- "application_method": "email" | "link" | "other" (How to apply)
- "application_link": str (The URL to apply if available, else "")

TEXT:
{text}
"""

# Matching Prompt
MATCHING_PROMPT = """
You are an expert PFE Matcher. Evaluate the compatibility between a student's CV and a PFE project.
Analyze skills, domain knowledge, and experience.

CV DATA:
{cv_data}

PROJECT DATA:
{project_data}

Return a JSON object with:
- "overall_score": int (0-100)
- "breakdown": {{"skills_match": int, "domain_match": int, "experience_match": int}}
- "matching_points": [str] (List of 3-5 key strengths)
- "gaps": [str] (List of missing skills or requirements)
- "recommendation": "Strong Match" | "Good Match" | "Potential Match" | "Low Match"
- "reasoning": str (Brief explanation of the score)
- "relevant_cv_snippets": [str] (Extract 2-3 sentences or bullet points from the CV that are most relevant to this project to be used in an email)
"""

# Email Generation Prompt
EMAIL_GENERATION_PROMPT = """
You are a professional career assistant writing a PFE application email.
Write a personalized email from the student to the company/supervisor.

CONTEXT:
- Student Name: {student_name}
- Project Title: {project_title}
- Company: {company_name}
- Tone: {tone} (e.g., "Formal", "Enthusiastic", "Academic")
- Language: {language} (e.g., "English", "French")

MATCHING INSIGHTS:
{match_data}

COMPANY RESEARCH:
{company_research}

INSTRUCTIONS:
1. Use a clear, professional subject line.
2. Start with a proper salutation.
3. Express genuine interest in the specific project.
4. Highlight relevant skills and experience using the matching insights.
5. Mention something specific about the company (from research) if available.
6. Keep it concise (under 200 words).
7. End with a call to action (interview request).

Return JSON:
{{
    "subject": "Email Subject",
    "body": "Email Body (HTML format allowed for paragraphs <p> and breaks <br>, but keep it simple)"
}}
"""
