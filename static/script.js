let darkMode = true;

function toggleMode() {
    if(darkMode){
        document.body.classList.add("light");
        darkMode = false;
    } else {
        document.body.classList.remove("light");
        darkMode = true;
    }
}

function uploadResumeFile(){
    let fileInput = document.getElementById("resumeFile");
    if(!fileInput || fileInput.files.length === 0){
        alert("Please select a resume file.");
        return;
    }

    let formData = new FormData();
    formData.append("resumeFile", fileInput.files[0]);
    let jobDesc = document.getElementById("jobDescription");
if(jobDesc){
    formData.append("job_description", jobDesc.value);
}

    fetch("/upload_resume",{
        method:"POST",
        body:formData
    })
    .then(res => res.json())
    .then(data => {
        if(data.error){ alert(data.error); return; }

        let score = data.score || 0;
        document.getElementById("resumeScoreFill").style.width = score+"%";
        document.getElementById("resumeScoreText").innerText = score+"%";

        alert("Resume uploaded successfully. Score: " + score + "%");
    }).catch(err=>{console.log(err);alert("Upload failed.");});
}

function analyzeAnswer(){
    let answer = document.getElementById("answerText").value.trim();
    if(answer===""){alert("Please enter your interview answer."); return;}

    fetch("/analyze_answer",{
        method:"POST",
        headers:{"Content-Type":"application/json"},
        body:JSON.stringify({answer:answer})
    }).then(res=>res.json()).then(data=>{
        let score = data.score || 0;
        document.getElementById("answerScoreFill").style.width = score+"%";
        document.getElementById("answerScoreText").innerText = score+"%";
        updateChart(score);
    }).catch(err=>{console.log(err);alert("Analysis failed.");});
}

function showLogoutButton(){
    let btn = document.getElementById("logoutConfirmBtn");
    btn.style.display = "block";
}

function logout(){
    window.location.href="/login";
}

let chart;
function updateChart(score){
    let canvas = document.getElementById("analysisChart");
    if(!canvas) return;
    if(chart){ chart.destroy(); }
    chart = new Chart(canvas,{
        type:"bar",
        data:{
            labels:["Clarity","Confidence","Structure"],
            datasets:[{label:"Score",data:[Math.max(score-10,0),score,Math.max(score-20,0)]}]
        },
        options:{responsive:true,scales:{y:{beginAtZero:true,max:100}}}
    });
}

function downloadReport(){
    let resumeScore = document.getElementById("resumeScoreText")?.innerText || "0%";
    let answerScore = document.getElementById("answerScoreText")?.innerText || "0%";
    let answerText = document.getElementById("answerText")?.value || "";

    fetch("/download_analysis",{
        method:"POST",
        headers:{"Content-Type":"application/json"},
        body:JSON.stringify({resume_score:resumeScore,answer_score:answerScore,answer_text:answerText})
    }).then(res=>res.blob()).then(blob=>{
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = "analysis_report.pdf";
        document.body.appendChild(a);
        a.click();
        a.remove();
    });
}

/* --------- FIXED FUNCTIONS (ADDED ONLY) --------- */

function sendAnswer(){
    analyzeAnswer();
}

function startVoice(){

    if(!('webkitSpeechRecognition' in window)){
        alert("Voice recognition not supported in this browser");
        return;
    }

    let recognition = new webkitSpeechRecognition();
    recognition.lang = "en-US";
    recognition.interimResults = false;

    recognition.onresult = function(event){
        let transcript = event.results[0][0].transcript;
        let textarea = document.getElementById("answerText");
        textarea.value += " " + transcript;
    };

    recognition.start();
}