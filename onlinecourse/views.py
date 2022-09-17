from django.shortcuts import render
from django.http import HttpResponseRedirect
# <HINT> Import any new Models here
from .models import Course, Enrollment, Submission, Question, Choice
from django.contrib.auth.models import User
from django.shortcuts import get_object_or_404, render, redirect
from django.urls import reverse
from django.views import generic
from django.contrib.auth import login, logout, authenticate
import logging
import json
# Get an instance of a logger
logger = logging.getLogger(__name__)
# Create your views here.


def registration_request(request):
    context = {}
    if request.method == 'GET':
        return render(request, 'onlinecourse/user_registration_bootstrap.html', context)
    elif request.method == 'POST':
        # Check if user exists
        username = request.POST['username']
        password = request.POST['psw']
        first_name = request.POST['firstname']
        last_name = request.POST['lastname']
        user_exist = False
        try:
            User.objects.get(username=username)
            user_exist = True
        except:
            logger.error("New user")
        if not user_exist:
            user = User.objects.create_user(username=username, first_name=first_name, last_name=last_name,
                                            password=password)
            login(request, user)
            return redirect("onlinecourse:index")
        else:
            context['message'] = "User already exists."
            return render(request, 'onlinecourse/user_registration_bootstrap.html', context)


def login_request(request):
    context = {}
    if request.method == "POST":
        username = request.POST['username']
        password = request.POST['psw']
        user = authenticate(username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect('onlinecourse:index')
        else:
            context['message'] = "Invalid username or password."
            return render(request, 'onlinecourse/user_login_bootstrap.html', context)
    else:
        return render(request, 'onlinecourse/user_login_bootstrap.html', context)


def logout_request(request):
    logout(request)
    return redirect('onlinecourse:index')


def check_if_enrolled(user, course):
    is_enrolled = False
    if user.id is not None:
        # Check if user enrolled
        num_results = Enrollment.objects.filter(user=user, course=course).count()
        if num_results > 0:
            is_enrolled = True
    return is_enrolled


# CourseListView
class CourseListView(generic.ListView):
    template_name = 'onlinecourse/course_list_bootstrap.html'
    context_object_name = 'course_list'

    def get_queryset(self):
        user = self.request.user
        courses = Course.objects.order_by('-total_enrollment')[:10]
        for course in courses:
            if user.is_authenticated:
                course.is_enrolled = check_if_enrolled(user, course)
        return courses


class CourseDetailView(generic.DetailView):
    model = Course
    template_name = 'onlinecourse/course_detail_bootstrap.html'


def enroll(request, course_id):
    course = get_object_or_404(Course, pk=course_id)
    user = request.user

    is_enrolled = check_if_enrolled(user, course)
    if not is_enrolled and user.is_authenticated:
        # Create an enrollment
        Enrollment.objects.create(user=user, course=course, mode='honor')
        course.total_enrollment += 1
        course.save()

    return HttpResponseRedirect(reverse(viewname='onlinecourse:course_details', args=(course.id,)))


# <HINT> Create a submit view to create an exam submission record for a course enrollment,
# you may implement it based on following logic:
         # Get user and course object, then get the associated enrollment object created when the user enrolled the course
         # Create a submission object referring to the enrollment
         # Collect the selected choices from exam form
         # Add each selected choice object to the submission object
         # Redirect to show_exam_result with the submission id
def submit(request, course_id):
    course = get_object_or_404(Course, pk=course_id)
    user = request.user
    enrollment = Enrollment.objects.get(course=course)
    print('enter submit')
    answers = extract_answers(request)
    choices = []
    submission = Submission.objects.create(enrollment_id = enrollment.id)
    submission.save()
    for answer in answers:
        choice = Choice.objects.get(id=answer)
        choice.submission_set.add(submission)
        choices.append(choice)    

    return HttpResponseRedirect(reverse(viewname='onlinecourse:show_exam_result', args=(course.id,submission.id,)))

# <HINT> A example method to collect the selected choices from the exam form from the request object
def extract_answers(request):
   submitted_anwsers = []
   for key in request.POST:
       if key.startswith('choice'):
           value = request.POST[key]
           choice_id = int(value)
           submitted_anwsers.append(choice_id)
   return submitted_anwsers


# <HINT> Create an exam result view to check if learner passed exam and show their question results and result for each question,
# you may implement it based on the following logic:
        # Get course and submission based on their ids
        # Get the selected choice ids from the submission record
        # For each selected choice, check if it is a correct answer or not
        # Calculate the total score
#def show_exam_result(request, course_id, submission_id):
def show_exam_result(request, course_id, submission_id):
    course = get_object_or_404(Course, pk=course_id)
    submission = get_object_or_404(Submission, pk=submission_id)
    
    correctChoice = []    
    for choice in submission.choices.all():
        if choice.is_correct:
            correctChoice.append(choice)        
    
    resultQuestionArray = []
    correctAnswerCount = 0
    totalQuestionCount = 0
    for lesson in course.lesson_set.all():
        totalQuestionCount = lesson.question_set.all().count() + totalQuestionCount
        for question in lesson.question_set.all():
            resultQuestion = ResultQuestion()
            resultQuestion.formatted_choices = []
            resultQuestion.question_title = question.question_text
            
            choicesArray = submission.choices.filter(question__id=question.id)            
            choicesId = []
            
            for submissionChoice in choicesArray:
                choicesId.append(submissionChoice.id)
            if question.is_get_score(choicesId):
                correctAnswerCount = correctAnswerCount + 1

            questionChoices = Choice.objects.filter(question__id=question.id)

            for questionChoice in questionChoices:
                formattedChoice = FormattedChoice()
                formattedChoice.choice_title = questionChoice.choice_text
                formattedChoice.css_class = "text-dark"

                if choicesArray.filter(id=questionChoice.id).count() > 0 :
                    if questionChoice.is_correct:
                        formattedChoice.css_class = "font-weight-bold text-success"
                elif questionChoice.is_correct:
                    formattedChoice.css_class = "font-weight-bold text-warning"

                resultQuestion.formatted_choices.append(formattedChoice)
            resultQuestionArray.append(resultQuestion)
            

    result = (correctAnswerCount/ totalQuestionCount)*100
    
    context = {}
    context['grade'] = result
    context['course'] = course
    context['submission'] = submission
    context['result_question_array'] = resultQuestionArray
    return render(request, 'onlinecourse/exam_result_bootstrap.html', context)


    #return HttpResponseRedirect(reverse(viewname='onlinecourse/exam_result_bootstrap.html', args=(course.id,submission.id,)))



class ResultQuestion():
    question_title = ""
    formatted_choices = []

class FormattedChoice():
    choice_title = ""
    css_class = ""