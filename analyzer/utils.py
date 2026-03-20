import os
import re
import json
import PyPDF2
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()



def get_gemini_model():
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("Missing GEMINI_API_KEY in environment")
    genai.configure(api_key=api_key)
    return genai.GenerativeModel("gemini-2.5-flash")


# ----------- TEXT EXTRACTION -----------

def extract_text(file):
    try:
        pdf = PyPDF2.PdfReader(file)
        text = ""
        for page in pdf.pages:
            if page.extract_text():
                text += page.extract_text() + " "
        return text.strip()
    except Exception as e:
        raise ValueError(f"Failed to read PDF: {str(e)}")


# ----------- CLEANING -----------

STOPWORDS = {
    "We", "The", "And", "With", "Experience", "Team",
    "Responsibilities", "Requirements", "Skills", "Must",
    "Please", "Monday", "Also", "Join", "Help", "Work",
    "Role", "Strong", "Good", "Your", "Have", "This",
    "That", "From", "Will", "Are", "Our", "For", "You",
    "Proficiency", "About", "Should", "Plus", "Been",
    "Such", "Both", "They", "Their", "What", "When",
    "Where", "Which", "Some", "More", "Other", "Into",
    "Over", "After", "Any", "All", "New", "Use", "May"
}

def clean_skills(skills):
    return list(set([
        s.strip() for s in skills
        if len(s.strip()) > 2 and s.strip() not in STOPWORDS and not s.strip().isdigit()
    ]))


# ----------- NORMALIZATION -----------

def normalize_skill(skill):
    skill = skill.lower().strip()
    replacements = {
        "c/c++": "c++",
        ".net": "dotnet",
        "node.js": "nodejs",
        "react.js": "react",
        "vue.js": "vue",
        "next.js": "nextjs",
    }
    return replacements.get(skill, skill)

def normalize_for_match(skill):
    return skill.lower().replace(".", "").replace(" ", "").replace("-", "")



def extract_job_skills_regex(jd_text):
    pattern = r'\b[A-Z][a-zA-Z0-9]*(?:[+#.\-][a-zA-Z0-9]+)*(?:\s+[A-Z][a-zA-Z0-9]*)*'
    matches = re.findall(pattern, jd_text)
    return clean_skills(matches)



def safe_json_extract(text):
    try:
        return json.loads(text)
    except Exception:
        match = re.search(r'\[.*\]', text, re.DOTALL)
        if match:
            return json.loads(match.group(0))
    raise ValueError("JSON parse failed — no valid array found")



def extract_gap_ai(jd_text):
    prompt = f"""
You are an expert hiring analyst.

Extract technical skills from the job description and assign each a priority.

Return ONLY a valid JSON array. No explanation. No markdown. No extra text.

Format:
[
  {{
    "skill": "React",
    "priority": "High",
    "reason": "Core frontend skill mentioned multiple times"
  }}
]

Priority rules:
- High: mentioned 3+ times or clearly required
- Medium: mentioned 1-2 times or listed as preferred
- Low: mentioned once or nice to have

Job Description:
{jd_text}
"""
    model = get_gemini_model()
    response = model.generate_content(prompt)
    text = response.text.strip()

    # strip markdown fences if Gemini wraps output
    text = re.sub(r'^```(?:json)?', '', text).strip()
    text = re.sub(r'```$', '', text).strip()

    data = safe_json_extract(text)

    for item in data:
        if "priority" in item:
            item["priority"] = item["priority"].capitalize()

    return data



def validate_ai_gap(data):
    return (
        isinstance(data, list) and
        len(data) > 0 and
        all(
            isinstance(item, dict) and
            "skill" in item and
            "priority" in item
            for item in data
        )
    )



def extract_user_skills(resume_text, job_skills):
    found = []
    resume_lower = resume_text.lower()

    for skill in job_skills:
        norm = normalize_skill(skill)
        if re.search(rf'\b{re.escape(norm)}\b', resume_lower):
            found.append(skill)

    return list(set(found))



def fallback_gap_analysis(user_skills, job_skills, jd_text):
    gap = list(set(job_skills) - set(user_skills))
    result = []

    for skill in gap:
        count = jd_text.lower().count(skill.lower())
        priority = "High" if count >= 3 else "Medium" if count == 2 else "Low"
        result.append({
            "skill": skill,
            "priority": priority,
            "reason": f"Mentioned {count} time(s) in job description"
        })

    return result



def analyze_gap_hybrid(user_skills, job_skills, jd_text):
    try:
        ai_output = extract_gap_ai(jd_text)

        if not validate_ai_gap(ai_output):
            raise Exception("AI output validation failed")

        gap_set = {
            normalize_for_match(s)
            for s in (set(job_skills) - set(user_skills))
        }

        filtered = [
            i for i in ai_output
            if "skill" in i and normalize_for_match(i["skill"]) in gap_set
        ]

        if not filtered:
            raise Exception("AI output had no matching gap skills")

        return filtered, "ai"

    except Exception as e:
        print(f"Gap AI fallback triggered: {str(e)}")
        return fallback_gap_analysis(user_skills, job_skills, jd_text), "fallback"



def detect_partial_skills(resume_text, gap_skills):
    resume_lower = resume_text.lower()

    mapping = {
        "Kubernetes": "docker",
        "FastAPI": "flask",
        "TypeScript": "javascript",
        "Next.js": "react",
        "Spark": "hadoop",
        "PyTorch": "tensorflow",
        "Terraform": "aws",
    }

    return [
        {"skill": s, "reason": f"You know {mapping[s]} — {s} is the next step"}
        for s in gap_skills
        if s in mapping and mapping[s] in resume_lower
    ]



def calculate_match_score(user_skills, job_skills):
    if not job_skills:
        return 0
    return round(len(user_skills) / len(job_skills) * 100)



def generate_roadmap_ai(user_skills, gap_skills, partial_skills):
    prompt = f"""
You are a career coach helping someone prepare for a job.

Create a realistic 30-60-90 day learning roadmap based on their skill gaps.

User already knows: {user_skills}
Missing skills: {gap_skills}
Partially known skills: {partial_skills}

Rules:
- 30 days: focus on the most critical missing skills
- 60 days: build hands-on projects using those skills
- 90 days: tackle advanced or stretch skills

Return ONLY valid JSON. No explanation. No markdown.

Format:
{{
  "30_days": ["Action item 1", "Action item 2"],
  "60_days": ["Action item 1", "Action item 2"],
  "90_days": ["Action item 1", "Action item 2"]
}}
"""
    model = get_gemini_model()
    response = model.generate_content(prompt)
    text = response.text.strip()

    text = re.sub(r'^```(?:json)?', '', text).strip()
    text = re.sub(r'```$', '', text).strip()

    match = re.search(r'\{.*\}', text, re.DOTALL)
    if match:
        return json.loads(match.group(0))

    raise ValueError("Could not parse roadmap JSON")



def validate_roadmap(data):
    return (
        isinstance(data, dict) and
        all(
            k in data and isinstance(data[k], list) and len(data[k]) > 0
            for k in ["30_days", "60_days", "90_days"]
        )
    )



def fallback_roadmap(gap_skills):
    if not gap_skills:
        return {
            "30_days": ["Review fundamentals of your target role"],
            "60_days": ["Build a small project to demonstrate your skills"],
            "90_days": ["Apply to roles and prepare for interviews"]
        }

    third = max(1, len(gap_skills) // 3)
    early = gap_skills[:third]
    mid = gap_skills[third:third * 2]
    late = gap_skills[third * 2:]

    return {
        "30_days": [f"Learn basics of {s}" for s in early] +
                   (["Start with free tutorials and documentation"] if not early else []),
        "60_days": [f"Build a hands-on project using {s}" for s in mid] +
                   (["Practice with small exercises"] if not mid else []),
        "90_days": [f"Go advanced with {s} and add it to your portfolio" for s in late] +
                   (["Polish your resume and apply to roles"] if not late else [])
    }



def generate_roadmap_hybrid(user_skills, gap_skills, partial_skills):
    try:
        data = generate_roadmap_ai(user_skills, gap_skills, partial_skills)

        if not validate_roadmap(data):
            raise Exception("Roadmap validation failed")

        return data, "ai"

    except Exception as e:
        print(f"Roadmap AI fallback triggered: {str(e)}")
        return fallback_roadmap(gap_skills), "fallback"



def process_resume_and_jd(resume_file, jd_text):
    resume_text = extract_text(resume_file)

    if not resume_text:
        raise ValueError("Could not extract text from resume. Please check your PDF.")

    job_skills = extract_job_skills_regex(jd_text)

    if not job_skills:
        raise ValueError("Could not identify any skills from the job description.")

    user_skills = extract_user_skills(resume_text, job_skills)

    gap_analysis, source = analyze_gap_hybrid(user_skills, job_skills, jd_text)

    gap_names = [g["skill"] for g in gap_analysis]

    partial = detect_partial_skills(resume_text, gap_names)

    roadmap, roadmap_source = generate_roadmap_hybrid(
        user_skills,
        gap_names,
        [p["skill"] for p in partial]
    )

    return {
        "matched": user_skills,
        "missing": gap_names,
        "partial": partial,
        "gap_analysis": gap_analysis,
        "match_score": calculate_match_score(user_skills, job_skills),
        "roadmap": roadmap,
        "source": source,
        "roadmap_source": roadmap_source
    }