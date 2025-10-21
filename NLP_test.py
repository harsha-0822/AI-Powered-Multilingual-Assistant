import nltk
from nltk.stem.lancaster import LancasterStemmer
import pickle
import numpy as np
from keras.models import load_model
import json
import random
from googletrans import Translator
translator = Translator()

# Load prediction model
stemmer = LancasterStemmer()
model = load_model('chatbot_model.h5')
intents = json.loads(open('CEC.json').read())
words = pickle.load(open('words.pkl', 'rb'))
labels = pickle.load(open('labels.pkl', 'rb'))

def clean_up_sentence(sentence):
    sentence_words = nltk.word_tokenize(sentence)
    sentence_words = [stemmer.stem(word.lower()) for word in sentence_words]
    return sentence_words

def bow(sentence, words, show_details=True):
    sentence_words = clean_up_sentence(sentence)
    bag = [0] * len(words)
    for s in sentence_words:
        for i, w in enumerate(words):
            if w == s:
                bag[i] = 1
                if show_details:
                    print("found in bag: %s" % w)
    return np.array(bag)

def getResponse(ints, intents_json):
    
    tag = ints[0]['intent']
    list_of_intents = intents_json['intents']
    for i in list_of_intents:
        if(i['tag']== tag):
            global result
            result = random.choice(i['responses'])
            break
    return result

def predict_class(sentence, model):
    p = bow(sentence, words, show_details=False)
    res = model.predict(np.array([p]))[0]
    ERROR_THRESHOLD = 0.25
    results = [[i, r] for i, r in enumerate(res) if r > ERROR_THRESHOLD]
    results.sort(key=lambda x: x[1], reverse=True)
    print(results)
    return_list = []
    for r in results:
        return_list.append({"intent": labels[r[0]], "probability": str(r[1])})
    return return_list

def chatbot_response(text):
    ints = predict_class(text, model)
    res = getResponse(ints, intents)
    return res

def getReasponse(user_input, from_lang):
    to_lang = 'en'
    text_to_translate = translator.translate(user_input,src= from_lang,dest= to_lang)
    text = text_to_translate.text
    output = chatbot_response(text)
    from1_lang = 'en'
    to_lang = from_lang
    text_to_translate = translator.translate(output,src= from1_lang,dest= to_lang)
    text = text_to_translate.text
    return text

def getReasponseenglish(user_input):
    output = chatbot_response(user_input)
    return output


#  getReasponseenglish("what is your name")