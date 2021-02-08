from __future__ import print_function
import pickle
import os.path
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
import os
import pyttsx3
import speech_recognition as sr
import pytz
import subprocess
import datetime


def authenticate_google(pickle_file, json_file, scopes, app, version):
    creds = None
    # The file token.pickle stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists(pickle_file):
        with open(pickle_file, 'rb') as token:
            creds = pickle.load(token)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                json_file, scopes)
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open(pickle_file, 'wb') as token:
            pickle.dump(creds, token)
    service = build(app, version, credentials=creds)
    return service


def speak(text):
    engine = pyttsx3.init()
    rate = engine.getProperty('rate')
    engine.setProperty('rate', rate + 50)
    engine.say(text)
    engine.runAndWait()


def get_audio():
    r = sr.Recognizer()
    with sr.Microphone() as source:
        audio = r.listen(source)
        said = ""

        try:
            said = r.recognize_google(audio)
            print(said)
        except Exception as e:
            speak("i couldn't quite hear that ")

    return said.lower()


CHOICE = ["yes", "yep", "ok", "sure", "show me"]
# gmail keywords
GMAIL_SCOPES = ['https://www.googleapis.com/auth/gmail.modify']
KEYWORD = ["unread", "how many unread emails do i have", 'get unreads']
MORE_KEY = ["mark", "mark as read", "read"]
SENDER = ["how many emails did", "did i get any emails from"]
SENDER_KEYS = ["how", "many", "emails", "email", "i" "get", "recieve", "from", "any", "did", "give", "me"]
# youtube keywords
YT_SCOPES = ["https://www.googleapis.com/auth/youtube.readonly"]
SUB = ['who am i subscribed to', 'check my subscription list', 'check subscriptions', 'subscription list']
SPEC_SUBS = ['am i subscribed to', 'on my subscription list', 'am i subscribe to']
SPEC_HELP = ['am', 'i', 'subscribed', 'to', 'on', 'my', 'subscription', 'list', 'is', 'subscribe']
SEARCH = ['search', 'search on youtube']
# calendar keywords
CAL_SCOPES = ['https://www.googleapis.com/auth/calendar.readonly']
MONTHS = ["january", "february", "march", "april", "may", "june", "july", "august", "september", "october", "november",
          "december"]
DAYS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
DAY_EXTENTIONS = ["rd", "th", "st", "nd"]
CALENDAR_STR = ["what do i have", "do i have plans", "am i busy", "am i available"]
NOTE_STR = ["make a note", "write this down", "remember this"]


# GMAIL
def fix_time(date):
    # I made a separate method to fix the time because it bothers me
    ending = ''
    date = date.split('+')[0]  # gets rid of the +0000
    date = date.split(' ')  # i want to make the time into 12 hour format
    date.pop()
    time = date[-1].split(':')
    if time[0] > '12':
        time[0] = str(int(time[0]) - 12)
        ending = ' pm'
    elif time[0] == '00':
        time[0] = '12'
        ending = ' am'
    time = ':'.join(time)
    date[-1] = time
    date = ' '.join(date)
    return date + ending


def get_unread(service, userid='me', q='is:unread'):
    results = service.users().messages().list(userId=userid, labelIds=['UNREAD'], q=q).execute()
    messages = results.get('messages', [])

    if not messages:
        speak("You're all caught up!")
    else:
        speak(f"You have {len(messages)} unread messages")
        speak("Do you want to view messages?")
        print("Listening...")
        choice_text = get_audio()
        if choice_text in CHOICE:
            speak("Here are the top 5")
            for message in messages[:4]:
                msg = service.users().messages().get(userId=userid, id=message['id']).execute()
                email_info = msg['payload']['headers']
                for values in email_info:
                    if values["name"] == "From":
                        speak("You have a message from: " + values["value"])
                        speak("    " + msg['snippet'][:50] + "...")
        speak("Do you want to hear more")
        print("Listening...")
        choice_text_2 = get_audio()
        if choice_text_2 in CHOICE:
            speak("How many more would you like to hear")
            print("Listening...")
            num_times = get_audio()
            if num_times.isdigit():
                for message in messages[:int(num_times)]:
                    msg = service.users().messages().get(userId=userid, id=message['id']).execute()
                    email_info = msg['payload']['headers']
                    for values in email_info:
                        if values["name"] == "From":
                            speak("You have a message from: " + values["value"])
                            speak("    " + msg['snippet'][:50] + "...")
            else:
                speak("Couldn't quite understand you. Start all over sir.")
                Gmail().main()
        else:
            mark_read(service)


def mark_read(service, userid='me', q='is:unread'):
    results = service.users().messages().list(userId=userid, labelIds=['UNREAD'], q=q).execute()
    messages = results.get('messages', [])
    speak("Would you like to me to mark emails as read?")
    print("Listening...")
    choice_text = get_audio()
    if choice_text in CHOICE:
        speak("How many?")
        print("Listening...")
        num_text = get_audio()
        if num_text.isdigit():
            for message in messages[:int(num_text)]:
                service.users().messages().modify(userId=userid, id=message['id'], body={'removeLabelIds': ['UNREAD']}).execute()
            speak(f"Marked {num_text} as read.")
        else:
            speak("Couldn't quite understand you. Start all over sir.")
    else:
        Gmail().main()


def get_sender(service, sender, userid='me'):
    results = service.users().messages().list(userId=userid, labelIds=['INBOX'], q=("from:" + sender)).execute()
    messages = results.get('messages', [])
    if not messages:
        speak(f"You have no messages from {sender}")
    else:
        speak(f"You have {len(messages)} from {sender}")
        speak("Here are the latest 3:")
        for message in messages[:3]:
            msg = service.users().messages().get(userId=userid, id=message['id']).execute()
            # sender_emails is now a an array containing 26 dictionaries. You want to look for the subject and the date
            sender_emails = msg['payload']['headers']
            for i in range(len(sender_emails)):
                if sender_emails[i]['name'] == 'Subject':
                    subject = sender_emails[i]['value']
                if sender_emails[i]['name'] == 'Date':
                    date = sender_emails[i]['value']
            speak(f"Subject: {subject} \nDate: {fix_time(date)}\n")
    Gmail().main()


class Gmail:
    def __init__(self):
        self.SERVICE = authenticate_google('gmail_token.pickle', 'gmail_creds.json', GMAIL_SCOPES, 'gmail', 'v1')
        print("Authentication for Gmail: completed")

    def main(self):
        text = get_audio()
        if text in KEYWORD:
            get_unread(self.SERVICE)
        elif text in MORE_KEY:
            mark_read(self.SERVICE)
        for phrase in SENDER:
            if phrase in text:
                for word in text.split():
                    if word not in SENDER_KEYS:
                        get_sender(self.SERVICE, word)


# CALENDAR
def get_events(day, service):
    date = datetime.datetime.combine(day, datetime.datetime.min.time())
    end_date = datetime.datetime.combine(day, datetime.datetime.max.time())
    utc = pytz.UTC
    date = date.astimezone(utc)
    end_date = end_date.astimezone(utc)

    events_result = service.events().list(calendarId='primary', timeMin=date.isoformat(), timeMax=end_date.isoformat(), singleEvents=True, orderBy='startTime').execute()
    events = events_result.get('items', [])

    if not events:
        speak('No upcoming events found.')
    else:
        speak(f"You have {len(events)} events on this day.")

        for event in events:
            start = event['start'].get('dateTime', event['start'].get('date'))
            print(start, event['summary'])
            start_time = str(start.split("T")[1].split("-")[0])
            if int(start_time.split(":")[0]) < 12:
                start_time = start_time + "am"
            else:
                start_time = str(int(start_time.split(":")[0]) - 12) + start_time.split(":")[1]
                start_time = start_time + "pm"

            speak(event["summary"] + " at " + start_time)
    Calendar().main()


def get_date(text):
    text = text.lower()
    today = datetime.date.today()

    if text.count("today") > 0:
        return today

    day = -1
    day_of_week = -1
    month = -1
    year = today.year

    for word in text.split():
        if word in MONTHS:
            month = MONTHS.index(word) + 1
        elif word in DAYS:
            day_of_week = DAYS.index(word)
        elif word.isdigit():
            day = int(word)
        else:
            for ext in DAY_EXTENTIONS:
                found = word.find(ext)
                if found > 0:
                    try:
                        day = int(word[:found])
                    except:
                        pass

    if month < today.month and month != -1:
        year = year + 1

    if month == -1 and day != -1:
        if day < today.day:
            month = today.month + 1
        else:
            month = today.month

    if month == -1 and day == -1 and day_of_week != -1:
        current_day_of_week = today.weekday()
        dif = day_of_week - current_day_of_week

        if dif < 0:
            dif += 7
            if text.count("next") >= 1:
                dif += 7

        return today + datetime.timedelta(dif)

    if day != -1:
        return datetime.date(month=month, day=day, year=year)


def note(text):
    date = datetime.datetime.now()
    file_name = str(date).replace(":", "-") + "-note.txt"
    with open(file_name, "w") as f:
        f.write(text)
    coderunner = "/System/Applications/CodeRunner3.app/Contents/MacOS/CodeRunner"
    subprocess.Popen([coderunner, file_name])
    Calendar().main()


class Calendar:
    def __init__(self):
        self.SERVICE = authenticate_google('calendar_token.pickle', 'calendar_creds.json', CAL_SCOPES, 'calendar', 'v3')
        print("Authorization for Google Calendar: completed")

    def main(self):
        text = get_audio()
        for phrase in CALENDAR_STR:
            if phrase in text:
                date = get_date(text)
                if date:
                    get_events(date, self.SERVICE)
                else:
                    speak("Give me a date sir")
        for phrase in NOTE_STR:
            if phrase in text:
                speak("What would you like me to write down?")
                print("I'm listening")
                note_text = get_audio()
                note(note_text)
                speak("I've made a note of that.")


# YOUTUBE
def get_last_post_date(date):
    return date[:10]


def get_subs_list(service):
    # there are 5 dictionaries in response. We're only interested in the items, which has the youtubers I am subscribed
    # to, and the nexPageToken just in case the user wants to go to the next page
    response = service.subscriptions().list(part="snippet", maxResults=10, mine=True, ).execute()
    speak('do you want a description of the channel')
    print('Listening...')
    choice_text = get_audio()
    for i in range(len(response['items'])):
        youtuber = response['items'][i]['snippet']['title']  # gives me youtuber's name
        description = response['items'][i]['snippet']['description']  # gives me youtuber's channel description
        last_post = response['items'][i]['snippet']['publishedAt']  # gives me youtuber's last listed video
        speak(f'{youtuber} last posted on {get_last_post_date(last_post)}')
        if choice_text in CHOICE:
            speak(description)
    Youtube().main()


def get_specific_youtuber(service, youtuber):
    # the maximum amount of channels is 50 per page so create a list of all the subscription and then compare what the
    # user said to what they are subscribed to
    response = service.subscriptions().list(part="snippet", maxResults=50, mine=True).execute()
    total_subs = response['pageInfo']['totalResults']
    nextPageToken = response['nextPageToken']
    youtuber_list = []
    for i in range(len(response['items'])):
        youtuber_list.append(response['items'][i]['snippet']['title'])
    for i in range(int(total_subs / 50) - 1):
        response = service.subscriptions().list(part="snippet", maxResults=50, mine=True, pageToken=nextPageToken).execute()
        nextPageToken = response['nextPageToken']
        for j in range(len(response['items'])):
            youtuber_list.append(response['items'][j]['snippet']['title'])
    if youtuber in youtuber_list:
        speak(f"You are subscribed to {youtuber}.")

    else:
        speak(f"Seems like {youtuber} is not on your subscription list")
    Youtube().main()


def search(service):
    speak('What would you like me to search up')
    print('Listening...')
    search_text = get_audio()
    response = service.search().list(part='snippet', maxResults=5, pageToken='', q='search_text').execute()
    video_id = response['items'][1]['id']['videoId']
    speak(f"getting videos on {search_text}")
    for i in range(len(response['items'])):
        youtuber = response['items'][i]['snippet']['channelTitle']
        video_title = response['items'][i]['snippet']['title']
        last_post = response['items'][i]['snippet']['publishedAt']
        speak(f'{youtuber} made a video about {search_text} titled {video_title} on {get_last_post_date(last_post)}')
    speak("Would you like to hear related videos?")
    print('Listening...')
    related_text = get_audio()
    if related_text in CHOICE:
        related_search(service, video_id, search_text)
    else:
        Youtube().main()


def related_search(service, video_id, search_text):
    speak("Here are related video based on the first result")
    response = service.search().list(part='snippet', maxResults=5, relatedToVideoId=video_id, type="video").execute()
    for i in range(len(response['items'])):
        youtuber = response['items'][i]['snippet']['channelTitle']
        video_title = response['items'][i]['snippet']['title']
        last_post = response['items'][i]['snippet']['publishedAt']
        speak(f'{youtuber} made a video about {search_text} titled {video_title} on {get_last_post_date(last_post)}')
    Youtube().main()

class Youtube:
    def __init__(self):
        self.SERVICE = authenticate_google('youtube_token.pickle', 'youtube_creds.json', YT_SCOPES, 'youtube', 'v3')
        print("Authorization for Youtube: completed")

    def main(self):
        text = get_audio()
        if text in SEARCH:
            search(self.SERVICE)
        elif text in SUB:
            get_subs_list(self.SERVICE)
        else:
            for phrase in SPEC_SUBS:
                if phrase in text:
                    for word in text.split():
                        if word not in SPEC_HELP:
                            get_specific_youtuber(self.SERVICE, word)


INIT = ['awaken google', 'turn on google', 'start initializing', 'google start', 'ok google', 'hey google', 'Google']
while True:
    text = get_audio()
    if text in INIT:
        Youtube().main()
        Gmail().main()
        Calendar().main()
