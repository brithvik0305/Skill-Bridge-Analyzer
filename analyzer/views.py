from django.shortcuts import render
from django.http import HttpResponse
from .utils import process_resume_and_jd


def home(request):
    return render(request, 'index.html')


def analyze_resume(request):
    if request.method != 'POST':
        return HttpResponse("Method not allowed.", status=405)

    try:
        resume_file = request.FILES.get('resume')
        jd_text = request.POST.get('job_description', '').strip()

        if not resume_file:
            return HttpResponse("Resume file is required. Please upload a PDF.", status=400)

        if not resume_file.name.lower().endswith('.pdf'):
            return HttpResponse("Only PDF resumes are supported. Please upload a .pdf file.", status=400)

        if not jd_text:
            return HttpResponse("Job description is required. Please paste the job description.", status=400)

        if len(jd_text) < 50:
            return HttpResponse("Job description is too short. Please provide at least 50 characters.", status=400)

        result = process_resume_and_jd(resume_file, jd_text)

        return render(request, 'result.html', {"result": result})

    except ValueError as e:
        return HttpResponse(str(e), status=400)

    except Exception:
        return HttpResponse("Something went wrong on our end. Please try again.", status=500)