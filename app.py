from flask import *
import os
import random
from werkzeug.utils import secure_filename
import sqlite3
import pandas as pd
import matplotlib
matplotlib.use('Agg') # Set backend before importing pyplot
import matplotlib.pyplot as plt
import smtplib
from email.message import EmailMessage
from datetime import datetime # Import datetime for email formatting

# Assuming NLP_test.py exists with these functions
try:
    from NLP_test import getReasponse, getReasponseenglish
except ImportError:
    # Provide dummy functions if the module doesn't exist, to avoid crashes
    print("Warning: NLP_test module not found. Using dummy responses.")
    def getReasponseenglish(text): return f"Dummy English response for: {text}"
    def getReasponse(text, lang): return f"Dummy {lang} response for: {text}"


# --- Configuration ---
DATABASE_NAME = 'databse.db'
UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg', 'gif', 'mp4', 'mov', 'avi', 'mp3', 'wav', 'ogg'} # Example allowed extensions
EMAIL_ADDRESS = 'cityengineeringcollegecec@gmail.com' # Replace with your email
EMAIL_PASSWORD = 'yiwt utww xbcc zpox' # Replace with your app password or use environment variables

app = Flask(__name__)
app.secret_key = os.urandom(24) # More secure secret key generation
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Ensure upload directory exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# --- Database Setup ---
def init_db():
    """Initializes the database and creates tables if they don't exist."""
    with sqlite3.connect(DATABASE_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute("CREATE TABLE IF NOT EXISTS students(name TEXT, email TEXT UNIQUE, studentid TEXT UNIQUE, phone TEXT, password TEXT)")
        cursor.execute("CREATE TABLE IF NOT EXISTS lectures(name TEXT, email TEXT UNIQUE, lectureid TEXT, phone TEXT, password TEXT)")
        cursor.execute('''CREATE TABLE IF NOT EXISTS attendance
                         (id INTEGER PRIMARY KEY AUTOINCREMENT,
                          date DATE NOT NULL,
                          branch TEXT NOT NULL,
                          semester TEXT NOT NULL,
                          student_id TEXT NOT NULL,
                          subject_id TEXT NOT NULL,
                          status TEXT NOT NULL,
                          UNIQUE(date, student_id, subject_id))''') # Added UNIQUE constraint
        cursor.execute('''CREATE TABLE IF NOT EXISTS marks
                         (id INTEGER PRIMARY KEY AUTOINCREMENT,
                          date DATE NOT NULL,
                          branch TEXT NOT NULL,
                          semester TEXT NOT NULL,
                          student_id TEXT NOT NULL,
                          subject_id TEXT NOT NULL,
                          marks TEXT NOT NULL,
                          UNIQUE(date, student_id, subject_id))''') # Added UNIQUE constraint
        cursor.execute('''CREATE TABLE IF NOT EXISTS timetable (
                          id INTEGER PRIMARY KEY AUTOINCREMENT,
                          branch_id TEXT NOT NULL,
                          semester TEXT NOT NULL,
                          day TEXT NOT NULL,
                          period1 TEXT, period2 TEXT, period3 TEXT, period4 TEXT,
                          period5 TEXT, period6 TEXT, period7 TEXT,
                          UNIQUE(branch_id, semester, day))''') # Added UNIQUE constraint
        cursor.execute('''CREATE TABLE IF NOT EXISTS study_materials (
                          id INTEGER PRIMARY KEY AUTOINCREMENT,
                          title TEXT NOT NULL,
                          description TEXT,
                          branch TEXT NOT NULL,
                          semester TEXT NOT NULL,
                          subject TEXT NOT NULL,
                          material_type TEXT NOT NULL,
                          file_path TEXT,
                          url TEXT,
                          created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS Events (
                          id INTEGER PRIMARY KEY AUTOINCREMENT,
                          Datetime TEXT NOT NULL,
                          title TEXT NOT NULL,
                          description TEXT NOT NULL)''')
        conn.commit()

# Call init_db() when the application starts
init_db()

# --- Email Function ---
def send_event_email(to_email_list, event_datetime_str, event_title, event_desc):
    """Sends event notification emails."""
    try:
        from_email_addr = EMAIL_ADDRESS
        from_email_pass = EMAIL_PASSWORD # Use app password
        subject = f"Event Notification: {event_title}"

        try:
            # Try to parse and format the date nicely
            date_obj = datetime.strptime(event_datetime_str, "%Y-%m-%dT%H:%M") # HTML datetime-local format
            date_formatted = date_obj.strftime("%B %d, %Y at %I:%M %p")
        except ValueError:
            date_formatted = event_datetime_str # Fallback to original string

        body = f"Dear Student,\n\nPlease note the following event:\n\nTitle: {event_title}\nDate & Time: {date_formatted}\nDescription: {event_desc}\n\nRegards,\nCity Engineering College"

        msg = EmailMessage()
        msg.set_content(body)
        msg['From'] = from_email_addr
        # msg['To'] = ', '.join(to_email_list) # Send individually to avoid exposing emails
        msg['Subject'] = subject

        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(from_email_addr, from_email_pass)
        # Send one email per recipient for privacy
        for email_addr in to_email_list:
             if email_addr: # Basic check
                 del msg['To'] # Remove previous To header
                 msg['To'] = email_addr
                 server.send_message(msg)
                 print(f"Sent event email to {email_addr}") # Log sending
        server.quit()
        print("Finished sending event emails.")
    except smtplib.SMTPAuthenticationError:
        print("Error: SMTP Authentication failed. Check email/password.")
    except Exception as e:
        print(f"Error sending email: {e}")


# --- Chatbot Helper Dictionaries & Functions ---

INTENT_KEYWORDS = {
    'get_timetable': ['timetable', 'time table', 'ಹೊತ್ತುಪಟ್ಟಿ', 'ಟೈಮ್ ಟೇಬಲ್', 'సమయ పట్టిక', 'టైం టేబుల్', 'நேர அட்டவணை', 'டைம் டேபிள்', 'पाठ्यक्रम तालिका', 'समय सारणी', 'टाइम टेबल'],
    'get_study_material': ['video', 'pdf', 'audio', 'source', 'link', 'material', 'notes', 'ವೀಡಿಯೊ', 'ಪಿಡಿಎಫ್', 'ಆಡಿಯೋ', 'ಮೂಲ', 'ಲಿಂಕ್', 'ವಸ್ತು', 'ಟಿಪ್ಪಣಿಗಳು', 'వీడియో', 'పిడిఎఫ్', 'ఆడియో', 'మూలం', 'లింక్', 'మెటీరియల్', 'గమనికలు', 'வீடியோ', 'பிடிஎஃப்', 'ஆடியோ', 'ஆதாரம்', 'இணைப்பு', 'பொருள்', 'குறிப்புகள்', 'वीडियो', 'पीडीएफ', 'ऑडियो', 'स्रोत', 'लिंक', 'सामग्री', 'नोट्स']
}

ENTITY_KEYWORDS = {
    'branch': {
        'CSE': ['computer science', 'cs', 'ಕಂಪ್ಯೂಟರ್ ಸೈನ್ಸ್', 'కంప్యూటర్ సైన్స్', 'கம்ப்யூட்டர் சயின்ஸ்', 'कंप्यूटर साइंस'],
        'ECE': ['electronics', 'ec', 'ಎಲೆಕ್ಟ್ರಾನಿಕ್ಸ್', 'ఎలక్ట్రానిక్స్', 'எலெக்ட்ரானிக்ஸ்', 'इलेक्ट्रॉनिक्स'],
        'ISE': ['information science', 'ise', 'ಸೂಚನಾ ವಿಜ್ಞಾನ', 'ಇನ್ಫಾರ್ಮಶನ್ ಸೈನ್ಸ್', 'సమాచారం శాస్త్రం', 'ఇన్ఫర్మేషన్ సైన్స్', 'தகவல் அறிவியல்', 'இந்பொர்மதிஒந் சயின்ஸ்', 'सूचना विज्ञान', 'इन्फॉर्मेशन साइंस'],
        'AIML': ['artificial intelligence', 'machine learning', 'aiml', 'ಕೃತಕ ಬುದ್ಧಿಮತ್ತೆ', 'ಯಂತ್ರ ಅಧ್ಯಯನ', 'ಆರ್ಟಿಫಿಷಿಯಲ್ ಇಂಟೆಲಿಜೆನ್ಸ್', 'కృత్రిమ బుద్ధి', 'యంత్ర అభ్యాసం', 'ఆర్టిఫిషియల్ ఇంటెలిజెన్స్', 'செயற்கை நுண்ணறிவு', 'இயந்திரக் கற்றல்', 'ஆர்ட்டிஃபிஷியல் இன்டெலிஜென்ஸ்', 'कृत्रिम बुद्धिमत्ता', 'मशीन लर्निंग', 'आर्टिफिशियल इंटेलिजेंस'],
        # Add ME, CE, EE keywords if needed
    },
    'semester': {
        '1': ['1st', 'first', '1ನೇ', 'ಮೊದಲನೇ', '1వ', 'మొదటి', 'முதலாவது', 'पहलां', 'प्रथम'],
        '2': ['2nd', 'second', '2ನೇ', 'ಎರಡನೇ', '2వ', 'రెండవ', 'இரண்டாம்', 'இரண்டாவது', 'दूसरा', 'द्वितीय'],
        '3': ['3rd', 'third', '3ನೇ', 'ಮೂರನೇ', '3వ', 'మూడవ', 'மூன்றாவது', 'மூன்றாம்', 'तीसरा', 'तृतीय'],
        '4': ['4th', 'four', '4ನೇ', 'ನಾಲ್ಕನೇ', '4వ', 'నాలుగవ', 'நான்காவது', 'நாலாம்', 'चौथा', 'चतुर्थ'],
        '5': ['5th', 'fifth', '5ನೇ', 'ಐದನೇ', '5వ', 'ఐదవ', 'ஐந்தாவது', 'ஐந்தாம்', 'पांचवा', 'पंचम'],
        '6': ['6th', 'sixth', '6ನೇ', 'ಆರನೇ', '6వ', 'ఆరవ', 'ஆறாவது', 'ஆறாம்', 'छठा', 'षष्ठ'],
        '7': ['7th', 'seventh', '7ನೇ', 'ಏಳನೇ', '7వ', 'ఏడవ', 'ஏழாவது', 'ஏழாம்', 'सातवां', 'सप्तम'],
        '8': ['8th', 'eight', '8ನೇ', 'ಎಂಟನೇ', '8వ', 'ఎనిమిదవ', 'எட்டாவது', 'எட்டாம்', 'आठवां', 'अष्टम']
    },
    'subject': {
        'DSA': ['data structure', 'datastructure', 'dsa', 'ಡೇಟಾ ಸ್ಟ್ರಕ್ಚರ್', 'ಡಿಎಸ್ಎ', 'డేటా స్ట్రక్చర్', 'డీఎస్ఎ', 'डाटा स्ट्रक्चर्स', 'डाटा संरचना', 'தரவு கட்டமைப்பு'],
        'DBMS': ['database', 'data base', 'dbms', 'ಡೇಟಾಬೇಸ್', 'ಡಿಬಿಎಂಎಸ್', 'డేటాబేస్', 'డిబిఎంఎస్', 'डेटाबेस', 'डीबीएमएस', 'தரவுத்தளம்'],
        'OS': ['operating system', 'operatingsystem', 'os', 'ಆಪರೇಟಿಂಗ್ ಸಿಸ್ಟಮ್', 'ఆపరేటింగ్ సిస్టమ్', 'ऑपरेटिंग सिस्टम', 'இயக்க முறைமை'],
        'CN': ['computer network', 'computernetwork', 'cn', 'ಕಂಪ್ಯೂಟರ್ ನೆಟ್ವರ್ಕ್', 'కంప్యూటర్ నెట్‌వర్క్', 'कंप्यूटर नेटवर्क', 'கணினி வலையமைப்பு'],
        'SE': ['software engineering', 'softwareengineering', 'se', 'ಸಾಫ್ಟ್‌ವೇರ್ ಎಂಜಿನಿಯರಿಂಗ್', 'సాఫ్ట్‌వేర్ ఇంజినీరింగ్', 'सॉफ्टवेयर इंजीनियरिंग', 'மென்பொருள் பொறியியல்'],
        'FSD': ['fullstack', 'fsd', 'full stack', 'ಪೂರ್ಣ ಸ್ಟ್ಯಾಕ್', 'ಫುಲ್ ಸ್ಟ್ಯಾಕ್', 'ఫుల్ స్టాక్', 'फुल स्टैक', 'முழு அடுக்கு'],
        'CC': ['cloud', 'cc', 'cloud computing', 'ಕ್ಲೌಡ್ ಕಂಪ್ಯೂಟಿಂಗ್', 'క్లోడ్ కంప్యూటింగ్', 'क्लाउड कंप्यूटिंग', 'கிளவுட் கம்ப்யூட்டிங்'],
        'BDA': ['big data', 'bda', 'analytics', 'ಬಿಗ್ ಡೇಟಾ', 'ಅನಾಲಿಟಿಕ್ಸ್', 'బిగ్ డేటా', 'ఆనలిటిక్స్', 'बिग डेटा', 'பிக் டேட்டா'],
        'CSMP': ['project', 'mini project', 'ಪ್ರಾಜೆಕ್ಟ್', 'ಮಿನಿ ಪ್ರಾಜೆಕ್ಟ್', 'ప్రాజెక్ట్', 'మినీ ప్రాజెక్ట్', 'प्रोजेक्ट', 'திட்டம்'], # Assuming CSMP for CSE/ISE etc. Add ECMP etc. if needed
        'INT': ['internship', 'int', 'ಇಂಟರ್ನ್‌ಷಿಪ್', 'ఇంటర్న్‌షిప్', 'इंटर्नशिप', 'பயிற்சி'],
        'M1': ['maths', 'mathematics', 'm1', 'ಗಣಿತ', 'గణితం', 'गणित', 'கணிதம்'],
        'M2': ['mathematics 2', 'm2', 'ಗಣಿತ 2', 'గణితం 2', 'गणित 2', 'கணிதம் 2'],
        'M3': ['mathematics 3', 'm3', 'ಗಣಿತ 3', 'గణితం 3', 'गणित 3', 'கணிதம் 3'],
        'M4': ['mathematics 4', 'm4', 'ಗಣಿತ 4', 'గణితం 4', 'गणित 4', 'கணிதம் 4'],
        'CHEM': ['chemistry', 'chem', 'ರಸಾಯನಶಾಸ್ತ್ರ', 'రసాయన శాస్త్రం', 'रसायन शास्त्र', 'வேதியியல்'],
        'PHY': ['physics', 'phy', 'ಭೌತಶಾಸ್ತ್ರ', 'ಫಿಸಿಕ್ಸ್', 'ఫిజిక్స్', 'భౌతిక శాస్త్రం', 'फिजिक्स', 'இயற்பியல்'],
        'OOP': ['oop', 'object oriented', 'ಆಬ್ಜೆಕ್ಟ್ ಓರಿಯೆಂಟೆಡ್', 'ఆబ్జెక్ట్ ఓరియెంటెడ్', 'ऑब्जेक्ट ओरिएंटेड', 'ஆப்ஜெக்ட் ஓரியண்டட்'],
        'COA': ['coa', 'computer organization', 'ಕಂಪ್ಯೂಟರ್ ಸಂಯೋಜನೆ', 'కంప్యూటర్ ఆర్గనైజేషన్', 'कंप्यूटर संगठन', 'கணினி அமைப்பு'],
        'EVN': ['evn', 'visualization', 'ವಿಸುಯಲೈಸೇಶನ್', 'విజువలైజేషన్', 'विज़ुअलाइज़ेशन', 'காட்சிப்படுத்தல்'],
        # 'AI': ['artificial', 'ai', 'ಕೃತಕ', 'ఆర్టిఫిషియల్', 'आर्टिफिशियल', 'செயற்கை'], # Added specific AI subject code
        'ML': ['machine', 'ml', 'ಯಂತ್ರ', 'మెషిన్', 'मशीन', 'யந்திர'], # Added specific ML subject code
        'NLP': ['nlp', 'natural language', 'ನೈಸರ್ಗಿಕ ಭಾಷೆ', 'నేచురల్ లాంగ్వేజ్', 'प्राकृतिक भाषा', 'இயற்கை மொழி'],
        'CGI': ['computer graphics', 'cg', 'cgi', 'ಕಂಪ್ಯೂಟರ್ ಗ್ರಾಫಿಕ್ಸ್', 'కంప్యూటర్ గ్రాఫిక్స్', 'कंप्यूटर ग्राफिक्स', 'கணினி கிராஃபிக்ஸ்'], # Added CGI
        # Add keywords for other subjects from your list (BME, NA, AE, DE, EMF, CS, AC, DC, AWP, VLSI, ME, ES(ECE), OC, WC, CIP, KAN, PAI, DSIA, RPADD, BCT, CAD, AUG, ADAI etc.)
    },
    'material_type': {
        'video': ['video', 'ವೀಡಿಯೊ','ವಿಡಿಯೋ', 'వీడియో', 'वीडियो', 'வீடியோ'],
        'pdf': ['pdf', 'ಪಿಡಿಎಫ್', 'పిడిఎఫ్', 'पीडीएफ', 'பிடிஎஃப்'],
        'audio': ['audio', 'ಆಡಿಯೋ', 'ఆడియో', 'ऑडियो', 'ஆடியோ'],
        'link': ['source', 'link', 'ಮೂಲ', 'లిಂಕ್', 'మూలం', 'स्रोत', 'लिंक', 'ஆதாரம்', 'இணைப்பு']
    }
}

ERROR_MESSAGES = {
    'get_timetable': {
         'branch': {
             'en': "Please specify the branch (e.g., CS, ECE) for the timetable.",
             'kn': "ದಯವಿಟ್ಟು ಹೊತ್ತುಪಟ್ಟಿಗಾಗಿ ಶಾಖೆಯನ್ನು (ಉದಾ., CS, ECE) ನಿರ್ದಿಷ್ಟಪಡಿಸಿ.",
             'te': "దయచేసి టైమ్ టేబుల్ కోసం శాఖను (ఉదా., CS, ECE) పేర్కొనండి.",
             'hi': "कृपया टाइमटेबल के लिए शाखा (उदा., CS, ECE) निर्दिष्ट करें।",
             'ta': "தயவுசெய்து நேர அட்டவணைக்கான பிரிவை (எ.கா., CS, ECE) குறிப்பிடவும்."
         },
         'semester': {
             'en': "Please specify the semester (e.g., 1st, 5th) for the timetable.",
             'kn': "ದಯವಿಟ್ಟು ಹೊತ್ತುಪಟ್ಟಿಗಾಗಿ ಸೆಮಿಸ್ಟರ್ (ಉದಾ., 1ನೇ, 5ನೇ) ನಿರ್ದಿಷ್ಟಪಡಿಸಿ.",
             'te': "దయచేసి టైమ్ టేబుల్ కోసం సెమిస్టర్ (ఉదా., 1వ, 5వ) పేర్కొనండి.",
             'hi': "कृपया टाइमटेबल के लिए सेमेस्टर (उदा., 1ला, 5वां) निर्दिष्ट करें।",
             'ta': "தயவுசெய்து நேர அட்டவணைக்கான செமஸ்டரை (எ.கா., 1வது, 5வது) குறிப்பிடவும்."
         }
     },
    'get_study_material': {
         'branch': {
             'en': "Please specify the branch (e.g., CS, ECE) for the study material.",
             'kn': "ದಯವಿಟ್ಟು ಅಧ್ಯಯನ ಸಾಮಗ್ರಿಗಾಗಿ ಶಾಖೆಯನ್ನು (ಉದಾ., CS, ECE) ನಿರ್ದಿಷ್ಟಪಡಿಸಿ.",
             'te': "దయచేసి అధ్యయన సామగ్రి కోసం శాఖను (ఉదా., CS, ECE) పేర్కొనండి.",
             'hi': "कृपया अध्ययन सामग्री के लिए शाखा (उदा., CS, ECE) निर्दिष्ट करें।",
             'ta': "தயவுசெய்து படிப்புப் பொருளுக்கான பிரிவை (எ.கா., CS, ECE) குறிப்பிடவும்."
         },
         'semester': {
             'en': "Please specify the semester (e.g., 1st, 5th) for the study material.",
             'kn': "ದಯವಿಟ್ಟು ಅಧ್ಯಯನ ಸಾಮಗ್ರಿಗಾಗಿ ಸೆಮಿಸ್ಟರ್ (ಉದಾ., 1ನೇ, 5ನೇ) ನಿರ್ದಿಷ್ಟಪಡಿಸಿ.",
             'te': "దయచేసి అధ్యయన సామగ్రి కోసం సెమిస్టర్ (ఉదా., 1వ, 5వ) పేర్కొనండి.",
             'hi': "कृपया अध्ययन सामग्री के लिए सेमेस्टर (उदा., 1ला, 5वां) निर्दिष्ट करें।",
             'ta': "தயவுசெய்து படிப்புப் பொருளுக்கான செமஸ்டரை (எ.கா., 1வது, 5வது) குறிப்பிடவும்."
         },
         'subject': {
             'en': "Please specify the subject (e.g., Database, OS) for the study material.",
             'kn': "ದಯವಿಟ್ಟು ಅಧ್ಯಯನ ಸಾಮಗ್ರಿಗಾಗಿ ವಿಷಯವನ್ನು (ಉದಾ., ಡೇಟಾಬೇಸ್, OS) ನಿರ್ದಿಷ್ಟಪಡಿಸಿ.",
             'te': "దయచేసి అధ్యయన సామగ్రి కోసం విషయం (ఉదా., డేటాబేస్, OS) పేర్కొనండి.",
             'hi': "कृपया अध्ययन सामग्री के लिए विषय (उदा., डेटाबेस, OS) निर्दिष्ट करें।",
             'ta': "தயவுசெய்து படிப்புப் பொருளுக்கான பாடத்தை (எ.கா., தரவுத்தளம், OS) குறிப்பிடவும்."
         },
         'material_type': {
             'en': "Please specify the material type (e.g., PDF, video, link) you are looking for.",
             'kn': "ದಯವಿಟ್ಟು ನೀವು ಹುಡುಕುತ್ತಿರುವ ವಸ್ತುವಿನ ಪ್ರಕಾರವನ್ನು (ಉದಾ., PDF, ವೀಡಿಯೊ, ಲಿಂಕ್) ನಿರ್ದಿಷ್ಟಪಡಿಸಿ.",
             'te': "దయచేసి మీరు వెతుకుతున్న మెటీరియల్ రకాన్ని (ఉదా., PDF, వీడియో, లింక్) పేర్కొనండి.",
             'hi': "कृपया आप जिस सामग्री प्रकार (उदा., PDF, वीडियो, लिंक) की तलाश कर रहे हैं उसे निर्दिष्ट करें।",
             'ta': "தயவுசெய்து நீங்கள் தேடும் பொருளின் வகையை (எ.கா., PDF, வீடியோ, இணைப்பு) குறிப்பிடவும்."
         }
     }
}

def parse_user_input(text, lang='en'):
    """Parses user input to find intent and entities."""
    text_lower = text.lower()
    detected_intent = None
    detected_entities = {}

    # 1. Detect Intent
    for intent, keywords in INTENT_KEYWORDS.items():
        if any(keyword in text_lower for keyword in keywords):
            detected_intent = intent
            break # Assume only one intent for now

    # 2. Extract Entities
    for entity_type, values in ENTITY_KEYWORDS.items():
        for entity_value, keywords in values.items():
            if any(keyword in text_lower for keyword in keywords):
                detected_entities[entity_type] = entity_value
                break # Take the first match for each entity type

    # If study material intent is detected, ensure material_type is explicitly set
    if detected_intent == 'get_study_material' and 'material_type' not in detected_entities:
         # Try to infer material type again specifically if intent known
         for m_type, keywords in ENTITY_KEYWORDS['material_type'].items():
              if any(keyword in text_lower for keyword in keywords):
                  detected_entities['material_type'] = m_type
                  break

    print(f"Detected Intent: {detected_intent}, Entities: {detected_entities}") # Debug print
    return detected_intent, detected_entities

def get_error_message(intent, entities, lang):
    """Generates an error message based on missing entities for an intent."""
    required_entities = []
    if intent == 'get_timetable':
        required_entities = ['branch', 'semester']
    elif intent == 'get_study_material':
        required_entities = ['branch', 'semester', 'subject', 'material_type']

    for entity in required_entities:
        if entity not in entities or not entities[entity]:
            try:
                # Use .get() for safer dictionary access
                return ERROR_MESSAGES.get(intent, {}).get(entity, {}).get(lang, ERROR_MESSAGES.get(intent, {}).get(entity, {}).get('en', "Missing information."))
            except KeyError:
                 return "Error: Could not find appropriate error message configuration." # Fallback

    return ERROR_MESSAGES.get(intent, {}).get('general', {}).get(lang, "Please provide more details.") # General fallback

def handle_timetable_request(original_message, branch, sem):
    """Handles timetable requests: queries DB and generates image response."""
    try:
        with sqlite3.connect(DATABASE_NAME) as conn:
            cursor = conn.cursor()
            # Parameterized query
            cursor.execute("SELECT * FROM timetable WHERE branch_id = ? AND semester = ?", (branch, sem))
            data = cursor.fetchall()

        if not data:
            # Handle case where timetable doesn't exist for the selection
            return render_template('chatbot2.html', res=[original_message, f"Sorry, timetable not found for {branch} Semester {sem}.", 'text'])

        # Time slot headers (adjust if columns change)
        columns = [
            'id', 'branch_id', 'semester', 'day',
            '9:00 - 9:50', '9:50 - 10:40', # Period 1, 2
            '11:00 - 11:50', '11:50 - 12:40', # Period 3, 4
            '1:20 - 2:10', '2:10 - 3:00', '3:00 - 3:50' # Period 5, 6, 7
        ]
        # Adjust column slicing based on actual table structure (assuming 11 columns: id, branch, sem, day, p1-p7)
        db_columns_count = 11
        if len(columns) != db_columns_count:
             print(f"Warning: Column definition count ({len(columns)}) mismatch with expected DB columns ({db_columns_count}). Adjust 'columns' list.")
             # Fallback or adjust based on actual table
             columns = [f'col_{i}' for i in range(db_columns_count)] # Generic fallback

        df = pd.DataFrame(data, columns=columns[:len(data[0])]) # Use actual number of columns from data

        # Drop unnecessary columns if they exist
        cols_to_drop = [col for col in ['id', 'branch_id', 'semester'] if col in df.columns]
        df = df.drop(cols_to_drop, axis=1)

        if 'day' not in df.columns:
            print("Error: 'day' column not found in DataFrame after potential drop.")
            return render_template('chatbot2.html', res=[original_message, "Error processing timetable data.", 'text'])

        df.set_index('day', inplace=True)

        # Re-add break/lunch columns if they were part of the original table structure or needed for display
        # This assumes your DB stores subjects directly. If it stored 'Break'/'Lunch', keep them.
        # If not, we insert them for display purposes.
        # Check if Break/Lunch columns need manual insertion based on your DB schema
        if '10:40 - 11:00' not in df.columns: # Assuming break time is not a stored column
            df.insert(2, '10:40 - 11:00', 'Break')
        if '12:40 - 1:20' not in df.columns: # Assuming lunch time is not a stored column
             df.insert(5, '12:40 - 1:20', 'Lunch')

        # Reorder columns to match the desired display order
        display_columns = [
             '9:00 - 9:50', '9:50 - 10:40', '10:40 - 11:00',
             '11:00 - 11:50', '11:50 - 12:40', '12:40 - 1:20',
             '1:20 - 2:10', '2:10 - 3:00', '3:00 - 3:50'
        ]
        df = df[display_columns] # Reindex DataFrame with display columns

        # Plotting
        fig, ax = plt.subplots(figsize=(14, max(3, len(df)*0.5))) # Adjust height based on rows
        ax.axis('off')

        table = ax.table(
            cellText=df.values,
            colLabels=df.columns,
            rowLabels=df.index,
            loc='center',
            cellLoc='center'
        )

        table.auto_set_font_size(False)
        table.set_fontsize(9) # Adjusted font size
        table.scale(1, 1.8) # Adjust scale

        # Style header and cells
        for key, cell in table.get_celld().items():
            cell.set_edgecolor('lightgrey') # Add cell borders
            cell.set_linewidth(0.5)
            if key[0] == 0: # Header row
                cell.set_text_props(weight='bold', color='white')
                cell.set_facecolor(var_primary_color) # Use primary color for header
            if key[1] == -1: # Index column (Day)
                 cell.set_text_props(weight='bold', color=var_primary_color)
                 cell.set_facecolor('#f0f0f0') # Light grey for day column
            # Highlight Break/Lunch cells
            if df.columns[key[1]] in ['10:40 - 11:00', '12:40 - 1:20'] and key[0] > 0:
                 cell.set_facecolor('#f0f0f0')
                 cell.set_text_props(weight='bold', color=var_text_secondary)


        plt.title(f"Timetable - {branch} Semester {sem}", fontsize=14, weight='bold', pad=20)
        img_path = os.path.join(app.config['UPLOAD_FOLDER'], f"timetable_{branch}_{sem}.png")
        plt.savefig(img_path, bbox_inches='tight', dpi=150)
        plt.close(fig) # Close the figure to free memory

        # Return relative path for URL generation
        img_url = url_for('static', filename=f'uploads/timetable_{branch}_{sem}.png')
        return render_template('chatbot2.html', res=[original_message, img_url, 'image'])

    except Exception as e:
        print(f"Error generating timetable image: {e}")
        return render_template('chatbot2.html', res=[original_message, "Sorry, I couldn't generate the timetable image.", 'text'])

def handle_study_material_request(original_message, entities):
    """Handles study material requests: queries DB and returns link/file info."""
    branch = entities.get('branch')
    sem = entities.get('semester')
    subject = entities.get('subject')
    material_type = entities.get('material_type')

    try:
        with sqlite3.connect(DATABASE_NAME) as conn:
            cursor = conn.cursor()
            # Parameterized query
            cursor.execute("""
                SELECT * FROM study_materials
                WHERE material_type = ? AND branch = ? AND semester = ? AND subject = ?
            """, (material_type, branch, sem, subject))
            data = cursor.fetchall()

        if not data:
            error_msg = f"No {material_type} materials found for {branch} Sem {sem}, Subject {subject}."
            return render_template('chatbot2.html', res=[original_message, error_msg, 'text'])

        row = random.choice(data)
        # Assuming row structure: (id, title, desc, branch, sem, subj, type, file_path, url, created_at)
        # Indices:                 0,     1,    2,      3,   4,    5,    6,         7,   8,          9
        # Need file_path (index 7) for files, url (index 8) for links

        response_data = row # Pass the whole row for context
        response_type = material_type # Use the detected type

        # Adjust response_type if it's a link stored in file_path or url needs formatting
        if material_type == 'link':
             response_type = 'link' # Keep as link
             # Ensure the link data passed is correct (index 8 is url)
             # The template expects res[1][8] for the link URL

        elif material_type in ['video', 'audio', 'pdf']:
             # Pass the full row, template expects res[1][7] which is the filename (file_path)
             pass # Template already handles this based on type

        else: # Should not happen if material_type is validated
             return render_template('chatbot2.html', res=[original_message, "Unknown material type found.", 'text'])


        return render_template('chatbot2.html', res=[original_message, response_data, response_type])

    except Exception as e:
        print(f"Error fetching study material: {e}")
        return render_template('chatbot2.html', res=[original_message, "Sorry, I couldn't fetch the study material.", 'text'])


# --- Flask Routes ---

@app.route('/')
def index():
    return render_template('index.html')

@app.route("/studentlogin")
def studentlogin():
    return render_template('student.html')

@app.route("/lecturelogin")
def lecturelogin():
    return render_template('lecture.html')

@app.route("/lecturehome")
def lecturehome():
    if 'name' not in session: # Basic check if logged in
         return redirect(url_for('lecturelogin'))
    return render_template('lecturepage.html')

@app.route("/studenthome")
def studenthome():
    if 'user' not in session: # Basic check if logged in
         return redirect(url_for('studentlogin'))
    # Pass the user data tuple directly
    return render_template('studentpage.html', result=session.get('user'))

@app.route("/chatbot1")
def chatbot1():
     # Add login check if needed
     # if 'user' not in session: return redirect(url_for('studentlogin'))
    return render_template('chatbot1.html')

@app.route("/chatbot2", methods = ['POST', 'GET'])
def chatbot2():
    # Add login check if needed
    # if 'user' not in session: return redirect(url_for('studentlogin'))

    if request.method == 'POST':
        messageInput = request.form.get('messageInput', '') # Use .get for safety
        original_message = messageInput # Keep original case for display
        messageInput_lower = messageInput.lower()
        lang = request.form.get('lang', 'en') # Default to 'en'

        # 1. Parse Input for Intent and Entities
        intent, entities = parse_user_input(messageInput_lower, lang)

        # 2. Handle Specific Intents
        if intent == 'get_timetable':
            branch = entities.get('branch')
            sem = entities.get('semester')
            if not branch or not sem:
                 error_msg = get_error_message('get_timetable', entities, lang)
                 return render_template('chatbot2.html', res=[original_message, error_msg, 'text'])
            return handle_timetable_request(original_message, branch, sem)

        elif intent == 'get_study_material':
            branch = entities.get('branch')
            sem = entities.get('semester')
            subject = entities.get('subject')
            m_type = entities.get('material_type')
            if not branch or not sem or not subject or not m_type:
                error_msg = get_error_message('get_study_material', entities, lang)
                return render_template('chatbot2.html', res=[original_message, error_msg, 'text'])
            return handle_study_material_request(original_message, entities)

        # 3. Handle General Chat
        else:
            try:
                if lang == 'en':
                    text = getReasponseenglish(messageInput_lower)
                else:
                    text = getReasponse(messageInput_lower, lang)
                return render_template('chatbot2.html', res = [original_message, text, 'text'])
            except Exception as e:
                 print(f"Error calling NLP function: {e}")
                 # Provide a generic error in the selected language
                 error_texts = {
                      'en': "Sorry, I couldn't process that request.",
                      'kn': "ಕ್ಷಮಿಸಿ, ಆ ವಿನಂತಿಯನ್ನು ಪ್ರಕ್ರಿಯೆಗೊಳಿಸಲು ನನಗೆ ಸಾಧ್ಯವಾಗಲಿಲ್ಲ.",
                      'te': "క్షమించండి, నేను ఆ అభ్యర్థనను ప్రాసెస్ చేయలేకపోయాను.",
                      'hi': "क्षमा करें, मैं उस अनुरोध को संसाधित नहीं कर सका।",
                      'ta': "மன்னிக்கவும், அந்த கோரிக்கையை என்னால் செயல்படுத்த முடியவில்லை."
                 }
                 return render_template('chatbot2.html', res = [original_message, error_texts.get(lang, error_texts['en']), 'text'])

    # For GET requests or if POST fails before returning
    return render_template('chatbot2.html')


@app.route('/upload', methods=['GET', 'POST'])
def upload():
    # Add login check
    if 'name' not in session: return redirect(url_for('lecturelogin'))

    message = None # To display success/error message
    if request.method == 'POST':
        try:
            title = request.form['title']
            description = request.form.get('description', '') # Optional
            branch = request.form['branch']
            semester = request.form['semester']
            subject = request.form['subject']
            material_type = request.form['material_type']

            file_path_to_save = None
            url = None
            filename_to_db = None

            if material_type in ['pdf', 'video', 'audio']:
                file_key = f'{material_type}_file' # e.g., 'pdf_file'
                if file_key not in request.files or not request.files[file_key].filename:
                     flash(f'No {material_type} file selected!', 'danger')
                     return redirect(request.url)

                file = request.files[file_key]
                # Add extension check if desired using ALLOWED_EXTENSIONS

                filename = secure_filename(file.filename)
                # Save to the upload folder
                file_path_to_save = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(file_path_to_save)
                filename_to_db = filename # Store only the filename in DB

            elif material_type == 'link':
                url = request.form.get('url')
                if not url:
                     flash('URL is required for link type.', 'danger')
                     return redirect(request.url)

            else:
                 flash('Invalid material type selected.', 'danger')
                 return redirect(request.url)

            with sqlite3.connect(DATABASE_NAME) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO study_materials
                    (title, description, branch, semester, subject, material_type, file_path, url)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (title, description, branch, semester, subject, material_type, filename_to_db, url))
                conn.commit()

            message = 'Material uploaded successfully!'
            # Use flash messages for better feedback
            flash(message, 'success')
            return redirect(url_for('upload')) # Redirect to GET after POST

        except Exception as e:
            print(f"Error during upload: {e}")
            flash(f'An error occurred during upload: {e}', 'danger')
            # Don't redirect on error, show form again with message
            return render_template('upload.html', message=f'An error occurred: {e}')

    # For GET request
    return render_template('upload.html', message=message) # Pass message from flash


# --- Auth Routes ---

@app.route("/studentsignup", methods=['POST', 'GET'])
def studentsignup():
    if request.method == 'POST':
        fname = request.form.get('fname')
        lname = request.form.get('lname')
        email = request.form.get('email')
        studentid = request.form.get('studentid')
        phone = request.form.get('phone')
        password = request.form.get('password')
        name = f"{fname} {lname}".strip()

        if not all([name, email, studentid, phone, password]):
            flash("All fields are required!", "danger")
            return redirect(url_for('studentlogin')) # Show login page with error

        try:
            with sqlite3.connect(DATABASE_NAME) as conn:
                cursor = conn.cursor()
                # Use parameterized query
                cursor.execute("INSERT INTO students (name, email, studentid, phone, password) VALUES (?, ?, ?, ?, ?)",
                               (name, email, studentid, phone, password))
                conn.commit()
            flash("Signup successful! Please login.", "success")
            return redirect(url_for('studentlogin'))
        except sqlite3.IntegrityError:
             flash("Email or Student ID already exists.", "danger")
             return redirect(url_for('studentlogin')) # Show login page with error
        except Exception as e:
             print(f"Error during student signup: {e}")
             flash("An error occurred during signup.", "danger")
             return redirect(url_for('studentlogin'))

    # If GET request, redirect to login page (no separate signup page shown?)
    return redirect(url_for('studentlogin'))

@app.route("/studentsignin", methods=['POST', 'GET'])
def studentsignin():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        if not email or not password:
            flash("Email and password are required.", "warning")
            return redirect(url_for('studentlogin'))

        try:
            with sqlite3.connect(DATABASE_NAME) as conn:
                cursor = conn.cursor()
                # Use parameterized query
                cursor.execute("SELECT * FROM students WHERE email = ? AND password = ?", (email, password))
                result = cursor.fetchone()

            if result:
                session['user'] = result # Store user data tuple in session
                session['user_type'] = 'student' # Add user type
                return redirect(url_for('studenthome'))
            else:
                flash("Invalid email or password.", "danger")
                return redirect(url_for('studentlogin'))
        except Exception as e:
             print(f"Error during student signin: {e}")
             flash("An error occurred during login.", "danger")
             return redirect(url_for('studentlogin'))

    # If GET request, show login page
    return render_template('student.html')


@app.route("/lecturesignup", methods=['POST', 'GET'])
def lecturesignup():
    if request.method == 'POST':
        fname = request.form.get('fname')
        lname = request.form.get('lname')
        email = request.form.get('email')
        lectureid = request.form.get('lectureid') # This is Department in the form
        phone = request.form.get('phone')
        password = request.form.get('password')
        name = f"{fname} {lname}".strip()

        if not all([name, email, lectureid, phone, password]):
             flash("All fields are required!", "danger")
             return redirect(url_for('lecturelogin'))

        try:
            with sqlite3.connect(DATABASE_NAME) as conn:
                cursor = conn.cursor()
                # Use parameterized query
                cursor.execute("INSERT INTO lectures (name, email, lectureid, phone, password) VALUES (?, ?, ?, ?, ?)",
                               (name, email, lectureid, phone, password))
                conn.commit()
            flash("Signup successful! Please login.", "success")
            return redirect(url_for('lecturelogin'))
        except sqlite3.IntegrityError:
             flash("Email already exists.", "danger")
             return redirect(url_for('lecturelogin'))
        except Exception as e:
             print(f"Error during lecture signup: {e}")
             flash("An error occurred during signup.", "danger")
             return redirect(url_for('lecturelogin'))

    # If GET request, redirect to login page
    return redirect(url_for('lecturelogin'))


@app.route("/lecturesignin", methods=['POST', 'GET'])
def lecturesignin():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        if not email or not password:
            flash("Email and password are required.", "warning")
            return redirect(url_for('lecturelogin'))

        try:
            with sqlite3.connect(DATABASE_NAME) as conn:
                cursor = conn.cursor()
                 # Use parameterized query
                cursor.execute("SELECT * FROM lectures WHERE email = ? AND password = ?", (email, password))
                result = cursor.fetchone()

            if result:
                session['user'] = result # Store user data tuple
                session['user_type'] = 'lecture'
                session['name'] = result[0]      # Specific session vars seem redundant if 'user' is stored
                session['department'] = result[2]
                return redirect(url_for('lecturehome'))
            else:
                flash("Invalid email or password.", "danger")
                return redirect(url_for('lecturelogin'))
        except Exception as e:
             print(f"Error during lecture signin: {e}")
             flash("An error occurred during login.", "danger")
             return redirect(url_for('lecturelogin'))

    # If GET request, show login page
    return render_template('lecture.html')

# --- Faculty Function Routes ---

@app.route('/take_attendance', methods=['GET', 'POST'])
def take_attendance():
    if session.get('user_type') != 'lecture': # Auth check
         flash("Access denied.", "danger")
         return redirect(url_for('lecturelogin'))

    message = None
    students = []
    try:
        with sqlite3.connect(DATABASE_NAME) as conn:
            cursor = conn.cursor()
            # Fetch students only once on GET
            if request.method == 'GET':
                cursor.execute("SELECT name, email, studentid, phone, password FROM students") # Select specific columns
                students = cursor.fetchall() # Fetchall results

            if request.method == 'POST':
                # Fetch students again for POST context if needed, or pass from GET context
                cursor.execute("SELECT name, email, studentid, phone, password FROM students")
                students = cursor.fetchall()

                date = request.form.get('attendanceDate')
                student_id = request.form.get('student') # This is studentid (USN) from form
                subject_id = request.form.get('subject')
                status = request.form.get('attendanceStatus')
                branch = request.form.get('branch')
                semester = request.form.get('semester')

                if not all([date, student_id, subject_id, status, branch, semester]):
                    message = 'All fields are required!'
                else:
                    try:
                         # Use parameterized query
                        cursor.execute('''
                            INSERT INTO attendance (date, branch, semester, student_id, subject_id, status)
                            VALUES (?, ?, ?, ?, ?, ?)
                        ''', (date, branch, semester, student_id, subject_id, status))
                        conn.commit()
                        message = 'Attendance recorded successfully!'
                        flash(message, 'success') # Use flash message
                        return redirect(url_for('take_attendance')) # Redirect after success
                    except sqlite3.IntegrityError:
                        message = 'Attendance for this student and subject on this date already exists!'
                        flash(message, 'warning') # Use warning for existing record
                    except Exception as e:
                         message = f"Database error: {e}"
                         flash(message, 'danger')

    except Exception as e:
        message = f"An error occurred: {e}"
        flash(message, 'danger')

    return render_template('attendance.html', result=students, message=message) # Pass message from flash/POST


@app.route('/view_attendance', methods=['GET', 'POST'])
def view_attendance():
    # Auth check - could be student or lecture? Adjust as needed
    if 'user' not in session:
        return redirect(url_for('index')) # Or specific login

    attendance_result = None
    if request.method == 'POST':
        try:
            subject_id = request.form.get('subject')
            branch = request.form.get('branch')
            semester = request.form.get('semester')

            if not all([subject_id, branch, semester]):
                 flash("Please select Branch, Semester, and Subject.", "warning")
            else:
                with sqlite3.connect(DATABASE_NAME) as conn:
                    cursor = conn.cursor()
                    # Use parameterized query
                    cursor.execute('''
                        SELECT id, date, branch, semester, student_id, subject_id, status FROM attendance
                        WHERE branch = ? AND semester = ? AND subject_id = ? ORDER BY date, student_id
                    ''', (branch, semester, subject_id))
                    attendance_result = cursor.fetchall()
                    if not attendance_result:
                         flash("No attendance records found for the selected criteria.", "info")

        except Exception as e:
            print(f"Error viewing attendance: {e}")
            flash(f"An error occurred: {e}", "danger")

    # Render template for both GET and POST (showing results if POST was successful)
    return render_template('viewattendance.html', result=attendance_result)


@app.route('/add_marks', methods=['GET', 'POST'])
def add_marks():
    if session.get('user_type') != 'lecture': # Auth check
         flash("Access denied.", "danger")
         return redirect(url_for('lecturelogin'))

    message = None
    students = []
    try:
         with sqlite3.connect(DATABASE_NAME) as conn:
            cursor = conn.cursor()
            # Fetch students needed for the dropdown
            cursor.execute("SELECT name, email, studentid, phone, password FROM students")
            students = cursor.fetchall()

            if request.method == 'POST':
                date = request.form.get('marksDate')
                student_id = request.form.get('student') # USN
                subject_id = request.form.get('subject')
                marks = request.form.get('marks')
                branch = request.form.get('branch')
                semester = request.form.get('semester')

                if not all([date, student_id, subject_id, marks, branch, semester]):
                    message = 'All fields are required!'
                else:
                     # Optional: Add validation for marks (e.g., is numeric, within range)
                    try:
                        # Use parameterized query
                        cursor.execute('''
                            INSERT INTO marks (date, branch, semester, student_id, subject_id, marks)
                            VALUES (?, ?, ?, ?, ?, ?)
                        ''', (date, branch, semester, student_id, subject_id, marks))
                        conn.commit()
                        message = 'Marks updated successfully!'
                        flash(message, 'success')
                        return redirect(url_for('add_marks')) # Redirect after success
                    except sqlite3.IntegrityError:
                        message = 'Marks for this student and subject on this date already exist!'
                        flash(message, 'warning')
                    except Exception as e:
                        message = f"Database error: {e}"
                        flash(message, 'danger')

    except Exception as e:
        message = f"An error occurred: {e}"
        flash(message, 'danger')

    return render_template('marks.html', result=students, message=message)


@app.route('/view_marks', methods=['GET', 'POST'])
def view_marks():
     # Auth check - could be student or lecture? Adjust as needed
    if 'user' not in session:
        return redirect(url_for('index')) # Or specific login

    marks_result = None
    if request.method == 'POST':
        try:
            subject_id = request.form.get('subject')
            branch = request.form.get('branch')
            semester = request.form.get('semester')

            if not all([subject_id, branch, semester]):
                 flash("Please select Branch, Semester, and Subject.", "warning")
            else:
                with sqlite3.connect(DATABASE_NAME) as conn:
                    cursor = conn.cursor()
                    # Use parameterized query
                    cursor.execute('''
                        SELECT id, date, branch, semester, student_id, subject_id, marks FROM marks
                        WHERE branch = ? AND semester = ? AND subject_id = ? ORDER BY date, student_id
                    ''', (branch, semester, subject_id))
                    marks_result = cursor.fetchall()
                    if not marks_result:
                         flash("No marks records found for the selected criteria.", "info")

        except Exception as e:
            print(f"Error viewing marks: {e}")
            flash(f"An error occurred: {e}", "danger")

    return render_template('viewmarks.html', result=marks_result)


@app.route('/timetable', methods=['GET', 'POST'])
def timetable():
    if session.get('user_type') != 'lecture': # Auth check
         flash("Access denied.", "danger")
         return redirect(url_for('lecturelogin'))

    if request.method == 'POST':
        try:
            branch = request.form['branch']
            semester = request.form['sem'] # 'sem' from form

            with sqlite3.connect(DATABASE_NAME) as conn:
                cursor = conn.cursor()

                # Use INSERT OR REPLACE with UNIQUE constraint for easier updates
                days = ['mon', 'tue', 'wed', 'thu', 'fri', 'sat']
                for day in days:
                    periods = [request.form.get(f'{day}{i}', '') for i in range(1, 8)] # p1 to p7

                    cursor.execute('''
                        INSERT OR REPLACE INTO timetable
                        (branch_id, semester, day, period1, period2, period3, period4, period5, period6, period7)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (branch, semester, day, *periods))
                conn.commit()
            flash(f'Timetable for {branch} Semester {semester} updated successfully!', 'success')
            return redirect(url_for('timetable')) # Redirect after successful POST
        except Exception as e:
             print(f"Error updating timetable: {e}")
             flash(f"An error occurred: {e}", "danger")
             # Fall through to render GET template with error

    # For GET requests
    return render_template('timetable.html')


@app.route('/view_timetable') # Removed methods, GET only by default
def view_timetable_form():
     # Auth check - Student or Lecture?
     if 'user' not in session:
         return redirect(url_for('index'))
     # This route just shows the selection form
     return render_template('viewtimetable_select.html') # Need a new template for selection


@app.route('/view_timetable_details', methods=['POST']) # Specific route for POST
def view_timetable_details():
     # Auth check
     if 'user' not in session:
         return redirect(url_for('index'))

     timetable_dict = {} # Use dict for easier template access
     branch = request.form.get('branch')
     semester = request.form.get('semester')

     if not branch or not semester:
         flash("Please select both Branch and Semester.", "warning")
         return redirect(url_for('view_timetable_form'))

     try:
         with sqlite3.connect(DATABASE_NAME) as conn:
            cursor = conn.cursor()
            # Parameterized query
            cursor.execute("""
                SELECT day, period1, period2, period3, period4, period5, period6, period7
                FROM timetable WHERE branch_id = ? AND semester = ?
            """, (branch, semester))
            timetable_data = cursor.fetchall()

         if not timetable_data:
             flash(f"Timetable not found for {branch} Semester {semester}.", "info")
             return redirect(url_for('view_timetable_form'))

         # Convert list of tuples to dictionary keyed by day
         for entry in timetable_data:
             day = entry[0]
             timetable_dict[day] = {
                 '1': entry[1], '2': entry[2], '3': entry[3], '4': entry[4],
                 '5': entry[5], '6': entry[6], '7': entry[7]
             }

     except Exception as e:
         print(f"Error fetching timetable details: {e}")
         flash("An error occurred while fetching the timetable.", "danger")
         return redirect(url_for('view_timetable_form'))

     # Pass the dictionary to the display template
     return render_template('viewtimetable_display.html', timetable=timetable_dict, branch=branch, semester=semester) # Need another template for display


@app.route('/addevents', methods=['GET', 'POST'])
def addevents():
    if session.get('user_type') != 'lecture': # Auth check
         flash("Access denied.", "danger")
         return redirect(url_for('lecturelogin'))

    message = None
    events = []
    try:
        with sqlite3.connect(DATABASE_NAME) as conn:
            cursor = conn.cursor()

            if request.method == 'POST':
                event_datetime = request.form.get('datetime')
                event_title = request.form.get('title')
                event_desc = request.form.get('desc')

                if not all([event_datetime, event_title, event_desc]):
                    message = "All event fields are required!"
                    flash(message, 'warning')
                else:
                    try:
                        # Parameterized query
                        cursor.execute("INSERT INTO Events (Datetime, title, description) VALUES (?, ?, ?)",
                                       (event_datetime, event_title, event_desc))
                        conn.commit()
                        message = "Event added successfully!"
                        flash(message, 'success')

                        # Fetch student emails for notification
                        cursor.execute("SELECT email FROM students")
                        student_emails = [row[0] for row in cursor.fetchall()]

                        # Send email (run in background?)
                        if student_emails:
                             send_event_email(student_emails, event_datetime, event_title, event_desc)
                        else:
                             print("No student emails found to send event notification.")

                        return redirect(url_for('addevents')) # Redirect to GET after success

                    except Exception as e:
                        message = f"Database error: {e}"
                        flash(message, 'danger')

            # Fetch existing events for display on GET and after POST errors
            cursor.execute("SELECT id, Datetime, title, description FROM Events ORDER BY Datetime DESC")
            events = cursor.fetchall()

    except Exception as e:
        message = f"An error occurred: {e}"
        flash(message, 'danger') # Flash the error

    # Render template for GET or if POST had errors
    return render_template("addevents.html", result=events, message=message) # Pass message from flash/POST


# --- Logout ---
@app.route('/logout')
def logout():
    session.clear() # Clear all session variables
    flash("You have been logged out.", "info")
    return redirect(url_for('index'))

# --- Main Execution ---
if __name__ == "__main__":
    # Consider setting debug=False for production
    app.run(debug=True, use_reloader=True)