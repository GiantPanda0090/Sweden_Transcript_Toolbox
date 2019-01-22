from django.http import HttpResponse
from django.template import loader
from PyPDF2 import PdfFileReader
import re
import pprint

from django.shortcuts import render
from django.conf import settings
from django.core.files.storage import FileSystemStorage
from ast import literal_eval


def translate(ects):
    result = 0.0
    '''
    A = 5
    B = 4,5
    C = 4
    D = 3,5
    E = 3
    F = 0
    '''
    if 'A' in ects:
        result =5.0
    elif 'B' in ects:
        result =4.5
    elif 'C' in ects:
        result=4.0
    elif 'D' in ects:
        result =3.5
    elif 'E' in ects:
        result=3
    elif 'F' in ects:
        result=0
    else:
        result=0
    return result

def get_gpa(combin_lst):
    grades_credit=[]
    credit=[]
    for combin in combin_lst:
        grades_credit.append(float(combin[0])*float(combin[1]))
        credit.append(float(combin[1]))
    gpa=total(grades_credit)/total(credit)
    return gpa

def total(lst):
    sum=0
    for item in lst:
        sum=sum+item
    return sum

def processor(request):
    gpa=0.0
    # Total (Grades x (number of compulsory credits))/[Total (number of compulsory credits)] + 0.2 (if the student has acted as a mentor for an exchange student coming to KTH).
    if request.method == 'POST':
        dict = request.POST.dict()
        del dict['csrfmiddlewaretoken']
        del dict['select_course']
        list = []
        test_list=[]
        for key, item in dict.items():
            print(type(item))

            course_content =  literal_eval(item)
            if '_' in key and key != 'select_course':
                uni_coursecode = re.split('_', key)
            credit = course_content['ECTS Credit']
            ects = course_content['Grade']
            grades =translate(ects)
            if grades >0:
                list.append((grades,credit))
        gpa=get_gpa(list)


    return render(request, 'processor.html', {
        'content': gpa
    })


def simple_upload(request):
    if request.method == 'POST':
        if request.FILES['myfile']:
            myfile = request.FILES['myfile']
            fs = FileSystemStorage()
            if fs.exists('source/' + myfile.name):
                fs.delete('source/' + myfile.name)
            filename = fs.save('source/' + myfile.name, myfile)
            uploaded_file_url = fs.url(filename)
            (dict, titles) = process(uploaded_file_url)
            # pprint.pprint(dict)
            fs.delete('source/' + myfile.name)
            return render(request, 'uploader.html', {
                'uploaded_file_url': uploaded_file_url,
                'dict': dict,
                'titles': titles
            })
        elif request.form['select_course'] == 'Submit for Analyze':
            pprint.pprint(request.form)
        else:
            pprint.pprint(request.form)
    return render(request, 'uploader.html')


def main(request):
    template = loader.get_template('index.html')


    context = {

    }
    return HttpResponse(template.render(context, request))


def process(filepath):
    with open(filepath, 'rb') as pdf_file:
        pdf_reader = PdfFileReader(pdf_file)
        data = {}
        out = {}
        for page_nr in range(pdf_reader.getNumPages()):
            page = pdf_reader.getPage(page_nr)
            text = page.extractText()
            # uni name
            uni_name_dash = re.search('(\w*\s)*\w*\_{3,}', text)
            if uni_name_dash:
                uni_text = {'name': "", 'text': ''}
                uni_name = re.match('[A-Z,a-z,\s]*', uni_name_dash.group())
                out[uni_name.group()] = {}
                out[uni_name.group()]['University Name'], uni_text['name'] = uni_name.group(), uni_name.group()
                if len(uni_text['name']) > 0:
                    data[uni_text['name']] = uni_text
                    uni_text['text'] = text
            else:
                uni_text['text'] = uni_text['text'] + text

        data[uni_text['name']] = (uni_text)
        for uni, content in data.items():
            course_dict = {}
            course_list = []
            content['text'] = re.sub(
                'Official Transcript of Records forCheck the certificate at\: https\:\/\/www\.student\.ladok\.se\/verifieraCivic registration number\: [\d,\w]+ Verification code: [\d,\w]+Verifiable through [\d,\w,\(,\),\-]+',
                '', content['text'])
            course_content = re.split(
                '[\w,\s]+____________________________________________________________________________________Courses------- Credits_-------_Grade-----Date----------Note----'
                , re.split(
                    r'Credits obtained in unfinished courses-------------------------------------- Credits_-------_Grade-----Date----------Note----',
                    content['text'])[0])
            course_list = re.split(r'([A-Z,0-9]{6}\s)', course_content[1])
            # load
            i = 1
            titles = []
            while i < len(course_list) - 1:
                per_course_dict = {}
                name_rest = re.split('_', course_list[i + 1])
                namewithcredit = name_rest[0]
                course_credit = re.split('(\d+\.\d+)', namewithcredit)
                if course_credit[0][len(course_credit[0]) - 1] == ' ':
                    course_credit[0] = course_credit[0] + course_credit[1][0]
                    course_credit[1] = course_credit[1][1:]
                per_course_dict['Course Name'] = course_credit[0]
                per_course_dict['ECTS Credit'] = course_credit[1]
                rest = name_rest[1]
                grade_date_credit = re.split('(\(\s\d+\.\d+\)|\(\d+\.\d+\))', rest)
                grade_date_note = re.split('(\d+\-\d+\-\d{2})', grade_date_credit[0])
                per_course_dict['Grade'] = grade_date_note[0]
                per_course_dict['Date'] = grade_date_note[1]
                per_course_dict['Note'] = grade_date_note[2]
                i_couse = 1
                per_course_dict['Course Content'] = []
                while i_couse < len(grade_date_credit):
                    subcourse_dict = {}
                    subcourse_dict['Credit'] = re.search('\d+\.\d+', grade_date_credit[i_couse]).group()
                    subgrade_date_note = re.split('(\d+\-\d+\-\d{2})', grade_date_credit[i_couse + 1])
                    if len(subgrade_date_note) > 1:
                        subcourse_dict['Grade'] = subgrade_date_note[0]
                        subcourse_dict['Date'] = subgrade_date_note[1]
                        per_course_dict['Course Content'].append(subcourse_dict)
                    i_couse += 2
                if len(titles) <= 0:
                    titles.append('Select')
                    titles.append('Course Code')
                    for title in per_course_dict.keys():
                        titles.append(title)

                course_dict[course_list[i]] = per_course_dict
                i += 2
            # load in out
            out[uni]['Course'] = course_dict

    return (out, titles)

    ##main class trigger


if __name__ == "__main__":
    main()
