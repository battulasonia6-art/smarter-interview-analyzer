from flask import Flask, render_template, request, redirect, url_for, send_file, jsonify
import os
from PyPDF2 import PdfReader
from io import BytesIO
from fpdf import FPDF

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

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

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def analyze_resume(file_path):

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

    score = min(section_score + length_score, 100)

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

    global resume_score, answer_score

    analysis_text = generate_analysis_text(resume_score, answer_score)

    return render_template(
        "analysis_page.html",
        resume_score=resume_score,
        answer_score=answer_score,
        analysis_text=analysis_text
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

    resume_score, resume_text = analyze_resume(filepath)

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

    return jsonify({
        "score": answer_score
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

    pdf.cell(0,10,f"Resume Score: {resume_score}",0,1)
    pdf.multi_cell(0,10,resume_text[:2000])

    pdf.ln(5)

    pdf.cell(0,10,f"Answer Similarity Score: {answer_score}",0,1)
    pdf.multi_cell(0,10,answer_text)

    pdf_bytes = pdf.output(dest='S').encode('latin1')
    pdf_output = BytesIO(pdf_bytes)

    return send_file(
        pdf_output,
        as_attachment=True,
        download_name="analysis_report.pdf",
        mimetype="application/pdf"
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)