from flask import Flask, render_template, request, redirect, url_for, send_file, jsonify
import os
from PyPDF2 import PdfReader
from io import BytesIO
from fpdf import FPDF

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
def extract_skills(text):

    skills_list = [
        "python","java","c++","sql","flask","django","machine learning",
        "deep learning","data analysis","pandas","numpy","tensorflow",
        "html","css","javascript","react","node","api","docker","aws"
    ]

    found = []
    text_lower = text.lower()

    for skill in skills_list:
        if skill in text_lower:
            found.append(skill)

    return found

UPLOAD_FOLDER = 'upload'
ALLOWED_EXTENSIONS = {'pdf'}

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

resume_score = 0
answer_score = 0
resume_text = ""
answer_text = ""

profile_name = ""
profile_email = ""
def resume_improvement(resume_text):

    suggestions = []

    text = resume_text.lower()

    if "projects" not in text:
        suggestions.append("Add a projects section to highlight practical work.")

    if "skills" not in text:
        suggestions.append("Include a skills section listing programming tools and technologies.")

    if "experience" not in text:
        suggestions.append("Add internship or work experience.")

    if len(resume_text.split()) < 200:
        suggestions.append("Increase resume details with achievements and project descriptions.")

    return suggestions

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def analyze_resume(file_path, job_description=""):

    reader = PdfReader(file_path)
    text = ""

    for page in reader.pages:
        text += page.extract_text() or ""

    word_count = len(text.split())

    sections = ["education","experience","skills","projects","contact"]

    section_score = 0

    for s in sections:
        if s in text.lower():
            section_score += 15

    length_score = min(word_count / 8, 40)

    base_score = section_score + length_score

    # JOB DESCRIPTION MATCH
    jd_score = 0

    if job_description:
        documents = [text, job_description]

        vectorizer = TfidfVectorizer(stop_words="english")
        tfidf_matrix = vectorizer.fit_transform(documents)

        similarity = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])
        jd_score = similarity[0][0] * 40

    score = min(base_score + jd_score, 100)

    return round(score,2), text

def calculate_similarity(resume_text, answer_text):

    if not resume_text.strip() or not answer_text.strip():
        return 0

    documents = [resume_text, answer_text]

    vectorizer = TfidfVectorizer(stop_words="english")

    tfidf_matrix = vectorizer.fit_transform(documents)

    similarity = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])

    score = round(float(similarity[0][0]) * 100, 2)

    return score


# ADD THIS FUNCTION BELOW
import language_tool_python

tool = language_tool_python.LanguageTool('en-US')

def advanced_answer_analysis(answer):

    matches = tool.check(answer)

    grammar_errors = len(matches)

    word_count = len(answer.split())

    grammar_score = max(100 - grammar_errors*5, 0)

    confidence_score = min(word_count * 2, 100)

    clarity_score = min(word_count * 1.5, 100)

    return {
        "grammar": grammar_score,
        "confidence": confidence_score,
        "clarity": clarity_score
    }


def generate_analysis_text(resume_score, answer_score):

    if resume_score == 0 and answer_score == 0:
        return "Upload resume and analyze your interview answer to generate insights."

    report = ""

    if resume_score < 40:
        report += "Resume structure is weak. Add clear sections like skills, projects and experience. "

    elif resume_score < 70:
        report += "Resume is moderate but can be improved with stronger project descriptions. "

    else:
        report += "Resume structure looks strong and well organized. "

    if answer_score < 40:
        report += "Your interview answer is not strongly related to your resume."

    elif answer_score < 70:
        report += "Your answer has partial relevance but could include more examples from your experience."

    else:
        report += "Your answer strongly matches your resume experience."

    return report


@app.route("/")
def root():
    return redirect(url_for("login_page"))


@app.route("/login", methods=["GET","POST"])
def login_page():

    if request.method == "POST":

        username = request.form.get("username")
        password = request.form.get("password")

        if username and password:
            return redirect(url_for("dashboard"))

        return render_template("login.html", error="Invalid credentials")

    return render_template("login.html")


@app.route("/register", methods=["GET","POST"])
def register_page():

    if request.method == "POST":
        return redirect(url_for("login_page"))

    return render_template("register.html")


@app.route("/dashboard")
def dashboard():
    global resume_score, answer_score
    return render_template("dashboard.html",resume_score=resume_score,answer_score=answer_score)


@app.route("/upload_resume_page")
def upload_resume_page():
    return render_template("upload_resume_page.html")


@app.route("/analysis_page")
def analysis_page():

    global resume_score, answer_score, resume_text

    analysis_text = generate_analysis_text(resume_score, answer_score)

    suggestions = resume_improvement(resume_text)

    return render_template(
        "analysis_page.html",
        resume_score=resume_score,
        answer_score=answer_score,
        analysis_text=analysis_text,
        suggestions=suggestions
    )

@app.route("/profile_page")
def profile_page():

    global profile_name, profile_email

    return render_template(
        "profile_page.html",
        username=profile_name,
        email=profile_email
    )


@app.route("/save_profile", methods=["POST"])
def save_profile():

    global profile_name, profile_email

    profile_name = request.form.get("username")
    profile_email = request.form.get("email")

    return jsonify({"status":"success"})


@app.route("/upload_resume", methods=["POST"])
def upload_resume():

    global resume_score, resume_text

    if 'resumeFile' not in request.files:
        return jsonify({"error":"No file part"}),400

    file = request.files['resumeFile']

    if file.filename == '' or not allowed_file(file.filename):
        return jsonify({"error":"Invalid file"}),400

    filepath = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)

    file.save(filepath)

    job_description = request.form.get("job_description","")
    resume_score, resume_text = analyze_resume(filepath, job_description)

    return jsonify({
        "score": resume_score,
        "text": resume_text,
        "url": url_for('uploaded_file', filename=file.filename)
    })
# DELETE UPLOADED RESUME
@app.route("/delete_resume", methods=["POST"])
def delete_resume():
    # Delete all files in the upload folder
    files = os.listdir(app.config['UPLOAD_FOLDER'])
    for f in files:
        os.remove(os.path.join(app.config['UPLOAD_FOLDER'], f))
    
    # Reset global resume variables
    global resume_score, resume_text
    resume_score = 0
    resume_text = ""

    return jsonify({"status": "success"})


@app.route("/uploaded/<filename>")
def uploaded_file(filename):
    return send_file(os.path.join(app.config['UPLOAD_FOLDER'], filename))


@app.route("/analyze_answer", methods=["POST"])
def analyze_answer_route():

    global answer_score, answer_text, resume_text

    data = request.json

    answer_text = data.get("answer","")

    answer_score = calculate_similarity(resume_text, answer_text)

    analysis = advanced_answer_analysis(answer_text)

    analysis = advanced_answer_analysis(answer_text)

    return jsonify({
    "score": answer_score,
    "grammar": analysis["grammar"],
    "confidence": analysis["confidence"],
    "clarity": analysis["clarity"]
})

@app.route("/download_analysis", methods=["GET","POST"])
def download_analysis():

    global resume_score, answer_score, resume_text, answer_text

    pdf = FPDF()
    pdf.add_page()

    pdf.set_font("Arial","B",16)
    pdf.cell(0,10,"Interview Analysis Report",0,1)

    pdf.set_font("Arial","",12)
    pdf.ln(5)

    def safe_text(text):
        if not text:
            return ""
        return text.encode("latin-1","replace").decode("latin-1")

    pdf.cell(0,10,f"Resume Score: {resume_score}",0,1)
    pdf.multi_cell(0,10,safe_text(resume_text[:2000]))

    pdf.ln(5)

    pdf.cell(0,10,f"Answer Similarity Score: {answer_score}",0,1)
    pdf.multi_cell(0,10,safe_text(answer_text))

    # Save PDF temporarily
    file_path = "analysis_report.pdf"
    pdf.output(file_path)

    return send_file(
        file_path,
        as_attachment=True,
        download_name="analysis_report.pdf"
    )
@app.route("/question_page")
def question_page():
    return render_template("question_page.html")
@app.route("/generate_questions", methods=["POST"])
def generate_questions():

    global resume_text

    data = request.json
    job_description = data.get("job_description", "")

    if not resume_text:
        return jsonify({"questions": []})

    combined = resume_text + " " + job_description

    skills = extract_skills(combined)

    questions = []

    for skill in skills[:5]:
        questions.append(f"Can you explain a project where you used {skill}?")
        questions.append(f"What challenges did you face while working with {skill}?")

    questions.append("Tell me about a challenging project you worked on.")
    questions.append("How do you handle tight deadlines in projects?")
    questions.append("Why are you interested in this role?")

    return jsonify({"questions": questions})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)