# Skill-Bridge-Analyzer

Candidate Name: Rithvik Balabhadra

Scenario Chosen: Skill-Bridge Career Navigator 

Estimated Time Spent: 7 hours(approx)

Quick Start:
● Prerequisites:
Python, pip, Gemini API key

● Run Commands:

pip install -r requirements.txt
python manage.py runserver

● Test Commands: python manage.py test

AI Disclosure:
● Did you use an AI assistant (Copilot, ChatGPT, etc.)? (Yes/No)
Yes

● How did you verify the suggestions?
I did not accept suggestions blindly. I verified them by integrating them step by step into the Django app, running the project locally, checking actual outputs on sample resumes and job descriptions, and refining anything that caused errors or felt too hardcoded or unrealistic. I especially checked whether the AI path and fallback path both worked as intended, whether JSON parsing was reliable, and whether the extracted/missing skills made sense for the given resume and JD.

● Give one example of a suggestion you rejected or changed:
One suggestion I changed was using a hardcoded skill database as the fallback logic. I felt that maintaining a static list of skills would look naive and too hardcoded, so I changed the design to derive candidate skills dynamically from the job description and then match them against the resume. I also chose not to rely on simple JD word-frequency counts for AI-generated priority; instead, I let Gemini reason about priority and used frequency-based scoring only in the fallback.

Tradeoffs & Prioritization:
● What did you cut to stay within the 4–6 hour limit?
I intentionally did not build a full resume parser with section-wise extraction, did not add authentication or database persistence, did not create a chatbot-style interface. I also avoided training any custom ML model from scratch and kept the frontend simple with Bootstrap-based templates. The focus was kept on making the two core features work well: gap analysis and roadmap generation.

● What would you build next if you had more time?
I would improve skill extraction using embeddings or a stronger semantic matching approach, add more reliable normalization for skill variants, improve roadmap quality with project/resource recommendations. I would also add better observability for whether the AI path or fallback path was used and improve the UI with charts or progress indicators.

● Known limitations:

Resume matching is still based on text matching rather semantic understanding.

Regex-based fallback extraction from JD can include noise or miss some lowercase/multi-word skills.

The roadmap is useful but still generic in some cases and not personalized to exact proficiency level.

Only PDF resumes are supported currently.
