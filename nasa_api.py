'''
nasa_api.py provides functionality to query for image data from the astronomy
picture of the day api from NASA. It aslo creates object representations of individual 
images from the returned JSON data. The images are then displayed using a web server
image gallery built using python, flask, jinja, html, css, and bootstrap.

Running this program will create a template directory in the directory from which it is run.
The template directory will contain a single html template file created from running this program.
The webserver and gallery will then be started with an initial query for 15 random images.
controls are provided in the interface to query for todays image, for a specific days
image, or n number of random images between 1-20 inclusive.

This was originally 3 separate files and really should be. The program was combined to 
a single file for ease of assignment submittal and marking.

Assignment details
CSD-3444 Emerging Technologies
First Python Assignment
Part 2
Student: Shawn Vogt c0757846
Date: March 13 ,2021
'''

# built in imports
import os
import sys
import subprocess
import json
import webbrowser as wb
import requests as reqs
from datetime import datetime, date
from threading import Timer
# colorama is a simple cross-platform API for printing colored terminal text from Python
# colorama is not listed as built in but I did not have to istall it, so it appears to be
# installed by default with python? Or maybe vs code installed it? 
# I am only using it in the automated dependency handling section.
# If colorama causes issues. Please follow the instructions listed below to comment out
from colorama import Fore 
from colorama import Style

# ---------------------------------------------------------------------------- #
#     Terry, I added automated dependency handling just to see if I could.     #
#    It will only function in machines with pip installed and i am not sure    #
#         how  it will react in machines with multiple versions of pip.        #
#             If it causes errors when you try to run this program             #
#                   please comment out from here (lines 50-95)                 #
# ---------------------------------------------------------------------------- #

# build list of pip installed packages
pip_list = subprocess.getoutput([sys.executable, '-m', 'pip', 'list'])
'''
pip_list will be a single string formated like below
'Package             Version\n------------------- ---------\pkgname             pkgversion\n...
to store just the package names split pip_list by \n keeping all but first 2 items,
split each item in list keeping only the first item in lower case
'''
avail_packages = [item.split()[0].lower()  for item in pip_list.split('\n')][2:]

# List of dependencies that may need to be installed (not builtin)
dependencies = ['flask'] # enter dependencies in lower case

missing_dependencies = []  # <- missisng dependencies will be added to this list

print("Checking for dependencies")
# iterate through dependencies and check if package is available for install
for dependency in dependencies:
    if not dependency in avail_packages:
        missing_dependencies.append(dependency)

# if there are missing dependencies, install using pip if user allows when prompted
if len(missing_dependencies) > 0: 
    print(f'{Fore.RED}You are missing the following dependencies {Fore.YELLOW}{missing_dependencies}{Style.RESET_ALL}')
    install = ''
    while install not in ['y','Y','n','N']:
        install = input('Would you like to install them automatically with pip (y/n)? ')
    if install in ['y','Y']:
        for dependency in missing_dependencies:
            try:
                '''
                The first method I used to install modules worked in this application but is not threadsafe
                and is intended to be run as a single process. It is also not supported by PyPA
                pip.main(['install', dependency])  
                Running pip as a SubProcess is however fully supported by PyPA
                '''
                subprocess.check_call([sys.executable, '-m', 'pip', 'install', dependency])
                missing_dependencies.remove(dependency) # any dependency install that raises an exception will not be removed
            except:
                print(f'Could not install module {dependency}')
  
# If there are still missing modules, notify user and quit program 
if len(missing_dependencies) > 0:
    print(f'{Fore.RED}please manually install {missing_dependencies} before running program again.{Style.RESET_ALL}')
    quit()

print("All dependencies are installed, continuing with module imports")

# ---------------------------------------------------------------------------- #
#                                    to here                                   #
# ---------------------------------------------------------------------------- #

# Non built in imports
from flask import Flask, render_template, request
from nasa_key import NASA_KEY

# ---------------------------------------------------------------------------- #
#                Interact with API and create NASAImage objects                #
# ---------------------------------------------------------------------------- #

# API Key for nasa apis
API_KEY = NASA_KEY

# base url for APOD (Astronomy Picture of the Day)
# documentation @ https://github.com/nasa/apod-api
baseUrl = 'https://api.nasa.gov/planetary/apod'

todays_date = str(datetime.today().date().strftime('%Y-%m-%d'))

# definition of image to return when an error occurs parsing JSON data return from api
ERROR_IMAGE = {'media_type':'image',
               'title':'Error: Not Found',
               'date':todays_date,
               'url':'https://www.nasa.gov/sites/default/files/2cntrl_0.jpg',
               'explanation':'We are looking hard but could not find the requested image'}


class NASAImage():
    '''Creates a NASA Astonomy Picture of the Day object for a single image

    use:    
        NASAImage(json_data) 

    parameters: 
        json_data: The json data returned by NASA APOD api for a single image
    '''
    def __init__(self, json_data):
        # medoa_type key is sometimes missing is data and sometimes datatype is other 
        # both are not compatible with the gallery. Return an error image.
        if 'media_type' not in json_data.keys() or json_data['media_type'] == 'other':
            # self.copyright = self.date = self.url = self.hdurl = self.explanation = None
            # self.title = 'No Image fount for requested date'
            json_data = ERROR_IMAGE

        # copyright data is only available on some images
        try:
            self.copyright = json_data['copyright']
        except KeyError:
            self.copyright = "Not Available"
        
        self.title = json_data['title']
        self.date = json_data['date']
        # if we get this far and the media_type is not image then it is video. 
        # videos have a thumbnail_url key that can be used inplace of url key
        if json_data['media_type'] == 'image':
            self.url = json_data['url']
        else:
            self.url = json_data['thumbnail_url']
        # Some responses do not include an hdurl. In these cases replace hdurl with url
        try:
            self.hdurl = json_data['hdurl']
        except KeyError:
            self.hdurl = self.url
        self.explanation = json_data['explanation']

def getImages(request_url):
    '''
    Make api call to NASA and return a list of NASAImage objects
    '''
    response = reqs.get(request_url) 
    data = response.json() 

    # print(json.dumps(data, indent=4))  # NOTE: Useful for debugging purposes

    '''
    Individual image responses are dict, multiple image responses are a list of dict
    Put data in a list if type is dict to play nice with NASAImage class
    items in data that are type str are bad JSON, replace with error image. 
    '''
    if isinstance(data, dict):
        data = [data]
    for item in data:
        if isinstance(item, str):
            item = ERROR_IMAGE  # <- This here is where we replace the evil bad JSON
    
    return [NASAImage(photo) for photo in data]
    

# ---------------------------------------------------------------------------- #
#              create request strings for different request types              #
# ---------------------------------------------------------------------------- #
''' 
available api parameters 
date: a string in YYYY-MM-DD format. Use to get APOD for a specific date
start_date: a string in YYYY-MM-DD format. Use as a start date for a range of APOD's
end_date: a string in YYYY-MM-DD format. Use in conjunction with start date for a range of APOD's defaults to today
count: a positive integer no greater than 100. Use to get a random selection of images
thumbs: a boolian value. When true API returns URL of video thumbnail. If an APOD is not video this is ignored
api_key: string value of a valid api key must be used with request
'''

def getTodaysImage():
    ''' Create request string for todays image. Will return json for only a single file '''
    today = datetime.today().date().strftime('%Y-%m-%d')
    completeUrl = f'{baseUrl}?api_key={API_KEY}&date={today}&thumbs=true'
    return getImages(completeUrl)

def getRandomImages(count=15):
    ''' Create request string for n number of images. Max supported by NASA api = 100
    max = 20, min = 1
    type validation handled by server: if not an integer value a default of 10 is used'''
    count = max(1,min(count, 20))
    completeUrl = f'{baseUrl}?api_key={API_KEY}&count={count}&thumbs=true'
    return getImages(completeUrl)

def getImageByDate(apod_date):
    ''' Create request string for APOD for a specific date
    min = 1995-06-16, max = today 
    entering an out of range or poorly formated date will not break the program
    NASA APOD api will just return error code and this program will return an error image
    Client side validation recomended to prevent selection of out of range date (included in this program) '''
    completeUrl = f'{baseUrl}?api_key={API_KEY}&date={apod_date}&thumbs=true'
    return getImages(completeUrl)


# ---------------------------------------------------------------------------- #
#               Set up templates folder and gallery html document              #
# ---------------------------------------------------------------------------- #
gallery_html = """
<html>
<head>
    <link rel="stylesheet" 
          href="https://maxcdn.bootstrapcdn.com/bootstrap/4.0.0/css/bootstrap.min.css"
          integrity="sha384-Gn5384xqQ1aoWXA+058RXPxPg6fy4IWvTNh0E263XmFcJlSAwiGgFAW/dAiS6JXm" crossorigin="anonymous">
    <!-- I would normally create separate .css file for custom css but I wanted to keep this submittal simple -->
    <style>
        /* set max width so main content does not distort */
        .inner-main {
            max-width: 1000px;
        }
        /* Customize carousel */
        #carousel {
            height: 60%;
        }
        .carousel-item{
            height: 100%;
            overflow: hidden;
        }
        .carousel-item img{
            width: 100%;
            height: 100%;
            object-fit: scale-down;
        }
        /* Customize carousel previous and next icons */
        #carousel > a.carousel-control-prev > span.carousel-control-prev-icon {
            background-image: url("data:image/svg+xml,%3csvg xmlns='http://www.w3.org/2000/svg' fill='%2367f3f3' width='8' height='8' viewBox='0 0 8 8'%3e%3cpath d='M5.25 0l-4 4 4 4 1.5-1.5L4.25 4l2.5-2.5L5.25 0z'/%3e%3c/svg%3e");
        }
        
        #carousel > a.carousel-control-next > span.carousel-control-next-icon {
            background-image: url("data:image/svg+xml,%3csvg xmlns='http://www.w3.org/2000/svg' fill='%2367f3f3' width='8' height='8' viewBox='0 0 8 8'%3e%3cpath d='M2.75 0l-1.5 1.5L3.75 4l-2.5 2.5L2.75 8l4-4-4-4z'/%3e%3c/svg%3e");
        }
        /* Customize carousel indicators - defaults are not visible on white background*/
        /* the style below makes them visible on both light and dark backgrounds */
        .carousel-indicators li {
            height: 10px;
            background-color: #ffffff;
            border-style: solid;
            border-color: #494949;
            border-width: 2px;
        }
        .carousel-indicators .active {
            height: 10px;
            background-color: #67f3f3;
            border-style: solid;
            border-color: #494949;
            border-width: 2px;
        }
        /* customize carousel caption */
        .carousel-caption {
            top: 0;
            bottom: 40px;
            left: 10%;
            right: 10%;
            overflow: auto;
        }
        /* Hide title and caption information */
        #show, #show * {
            display: none;
        }
        /* Show title and caption information on hover */
        .carousel-item:hover #show * {
            display: block;
        }
        .carousel-item:hover #show {
            background-color: rgba(0, 0, 0, 0.8);
        }

    </style>
    <title>Shawn's Simple NASA Photo Gallery NASA Photo Gallery</title>
</head>
<body>
    <header>
        <nav class="navbar navbar-light bg-light">
            <div class="container-fluid">
                <form action="/today">
                    <button type="submit" class="btn btn-outline-info">Get Today's APOD</button>
                </form>
                <form action="/date" method="GET">
                    <input class="date" type="date" id="date" min="1995-06-16" max="{{todays_date}}" name="date">
                    <button type="submit" class="btn btn-outline-info">Get APOD by Date</button>
                </form>
                <form class="d-flex" action="/random" method="GET">
                    <input type="number" class="form-control me-2" name="random_count" min=1 max=20 placeholder="Quantity" aria-label="Quantity">
                    <button type="submit" class="btn btn-outline-info">Get Random</button>
                </form>
            </div>
          </nav>
    </header>
    <main class="mx-5">
    <div class="mx-auto inner-main"> 
        <h1 class="text-center">Shawn's NASA APOD Photo Gallery</h1>
        <h5 class="text-center">These images are from the <a href="https://apod.nasa.gov/apod/astropix.html">NASA Astronomy Picture of the Day Webite</a></h5>
        
<!-- ----------------------------------------------------------------------- -->
<!--                           Bootstap Carousel                             -->
<!--                     Integrated with Flask and Jinja                     -->
<!-- ----------------------------------------------------------------------- -->

        <div id="carousel" class="carousel slide" data-ride="carousel">
            <ol class="carousel-indicators">
                <!-- for each image add a carousel indicator. For the first, add class active  -->
                {% for image in images %}
                    {% if loop.first %} <!-- loop.first evaluates true only on first loop -->
                        <li data-target="#carousel" data-slide-to="0" class="active"></li>
                    {% else %}
                        <li data-target="#carousel" data-slide-to={{loop.index0}}></li> <!-- loop.index is 1 based indexing and loop.index0 is 0 based indexing -->
                    {% endif %}
                {% endfor %}
            </ol>
            <div class="carousel-inner">
                {% for image in images %}
                    {% if loop.first %}
                        <div class="carousel-item active">
                    {% else %}
                        <div class="carousel-item">
                    {% endif %}
                    <img class="d-block w-100" src={{image.url}} alt={{image.url}}>
                    <div id="show" class="carousel-caption d-none d-md-block p-2">
                        <h5 >{{ image.title }}</h5>
                        <p>Date: {{image.date}} <br> Copyright: {{image.copyright}}
                        <p>{{ image.explanation }}</p>
                        <a href={{image.hdurl}} target="_blank">Link to highest resolution version of this image available from NASA.</a>
                    </div>
                    </div>
                {% endfor %}
            </div>
            <a class="carousel-control-prev" href="#carousel" role="button" data-slide="prev">
                <span class="carousel-control-prev-icon" aria-hidden="true"></span>
                <span class="sr-only">Previous</span>
            </a>
            <a class="carousel-control-next" href="#carousel" role="button" data-slide="next">
                <span class="carousel-control-next-icon" aria-hidden="true"></span>
                <span class="sr-only">Next</span>
            </a>
        </div>
        <p class="text-center">Mouse over image to pause slideshow and see image title and description</p>
    </div>
</main>

    <script src="https://code.jquery.com/jquery-3.2.1.slim.min.js"
        integrity="sha384-KJ3o2DKtIkvYIK3UENzmM7KCkRr/rE9/Qpg6aAZGJwFDMVNA/GpGFF93hXpG5KkN" crossorigin="anonymous">
        </script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/popper.js/1.12.9/umd/popper.min.js"
        integrity="sha384-ApNbgh9B+Y1QKtv3Rn7W3mgPxhU9K/ScQsAP7hUibX39j7fakFPskvXusvfa0b4Q" crossorigin="anonymous">
        </script>
    <script src="https://maxcdn.bootstrapcdn.com/bootstrap/4.0.0/js/bootstrap.min.js"
        integrity="sha384-JZR6Spejh4U02d8jOt6vLEHfe/JQGiRRSQQxSfFWpi1MquVdAyjUar5+76PVCmYl" crossorigin="anonymous">
        </script>

</body>

</html>
"""

os.chdir(sys.path[0])  # ensure we are working in the directory this file was executed

# ---------- create templates directory if it does not already exist --------- #

if not os.path.exists("templates"):  # Check if directory exists
            os.mkdir("templates")  # Make directory

# ----- open nasa_gallery.html and write gallery_html string to the file ----- #
# ------------------------- whether it exists or not ------------------------- #

with open('./templates/nasa_gallery.html', 'w') as gallery:
    gallery.write(gallery_html)


# ---------------------------------------------------------------------------- #
#                  Start gallery server and launch web browser                 #
#   Note: this server will not scale well and is not designed for deployment   #
# ---------------------------------------------------------------------------- #

# Create Flask instance
app = Flask(__name__)

app.config['DEBUG'] = False  # Set true for live updates when editing code
# Note: Two browser tabs will open when this program is run if DEBUG is set True. 


# ----------------------------- default end point ---------------------------- #

@app.route('/', methods=['GET'])
def home():
    images = getRandomImages(15)
    return render_template('nasa_gallery.html', images=images, todays_date=todays_date)

# -------------------------- APOD for today endpoint ------------------------- #

@app.route('/today', methods=['GET'])
def today():
    images = getTodaysImage()
    return render_template('nasa_gallery.html', images=images, todays_date=todays_date)

# --------------------------- APOD by date endpoint -------------------------- #

@app.route('/date', methods=['GET'])
def date():
    date = request.args.get('date', type=str)
    images = getImageByDate(date)
    return render_template('nasa_gallery.html', images=images, todays_date=todays_date)

# ----------------------- APOD by random count endpoint ---------------------- #

@app.route('/random', methods=['GET'])
def random():
    random_count = request.args.get('random_count', default=10, type=int)
    images = getRandomImages(random_count)
    return render_template('nasa_gallery.html', images=images, todays_date=todays_date)


def openb():
    ''' Opens a webbrowser to port 5000 on localhost '''
    wb.open('http://localhost:5000')

# Wait 2 second before opening web browser to give server time to start
Timer(2, openb).start()

app.run()