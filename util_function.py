from datetime import datetime
import requests
from cryptography.fernet import Fernet
from telebot import types
from quickchart import QuickChart
from bs4 import BeautifulSoup
from selenium import webdriver
from distutils.util import strtobool
from firebase_admin import credentials, firestore
from selenium.webdriver.chrome.options import Options
from telebot.types import InlineKeyboardButton, InlineKeyboardMarkup
from datetime import date, datetime, timedelta
from typing import OrderedDict
import firebase_admin
from hashlib import sha256
import hmac
import hashlib
from firebase_admin import credentials, firestore
from rsa import encrypt
import telebot

DOMAIN = ""

def modify_string(string, string1):
    temp = f"{string} {string1}"

    new_string = ""

    if len(temp) > 16:
        new_string = temp[0:16]
        new_string += "..."
        return new_string
    
    else:
        return temp

def getNews(link, query):

    req = f'q={query}&lang=en'

    data = requests.get(f'https://gnews.io/api/v4/search?{req}&token=0d556add75fe40853913a0ef1cd7def5')

    try:
        news = data.json()['articles'][0]
    except:
        return [False]

    if link != news.get("url"):

        pub_at = news.get("publishedAt").split("T")[0]

        text = f'<b>#DAILYNEWS {news.get("title")}</b>\n\nBy <b><u>{news.get("source").get("name")}</u></b>, published on <b>{pub_at}</b>.\n\n<i>{news.get("content")}</i>\n\n<a href="{news.get("url")}">Want to continue reading? Click here!</a>\n\n'

        return [True, text, news.get("url")]
    
    else:
        return [False]

def update_info(db, id, first_name = None, last_name = None, up_news = None, link = None):
    usr = db.collection(u'users').document(str(id))

    # SE NON DEVO IMPOSTARE LE NEWS, ALLORA MI CREO/AGGIORNO L'UTENTE
    if up_news == None:

        if last_name == None:
            last_name = ""

        # SE NON ESISTE, CREA L'UTENTE CON L'IMPOSTAZIONE "FALSE" DELLE NEWS
        if usr.get().exists == False:
            usr.set({
                u'user_first': first_name,
                u'user_last' : last_name,
                u'news_service': False,
                u'title_game_on': "",
                u'url_news': "",
                u'id_game_on': ""

            })
        
        # ALTRIMENTI MI AGGIORNI SOLO IL TUTTO SENZA TOCCARE LE IMPOSTAZIONI
        else:
            usr.update({
                u'user_first': first_name,
                u'user_last' : last_name,
            })

    # ALTRIMENTI MI IMPOSTO LE NEWS
    else:
        usr.update({"news_service" : up_news[0], "title_game_on" : up_news[1], "id_game_on" : up_news[2]})
            


def bot_instance():
    TOKEN_KEY = ""
    return telebot.TeleBot(TOKEN_KEY)

def risultati_ricerca(query, user_id):
    arr = []

    # IN CASO CANCELLA
    print(query)
    
    
    data = call_to_db(query, "global")

    # SAREBBE MEGLIO FARE CONTROLLO SU DATI PRESI DALLE QUERY
    # OBBLIGATORIO GESTIRE GLI ERRORI CON UNA EXCEPTION
    for i in data:
        
        #Funzione che prende data in input e restituisce in dizionario con tutti i dati checkati per bene
        dict_query = check_query(i)

        r = create_result_query(dict_query, user_id)
        
        arr.append(r)
    
    return arr

def call_to_db(query, op, fields = None):

    header = {'Client-ID': 'j3khpmcz8atp5e4pn79sg83pvxmxlc', 'Authorization': 'Bearer 2nacdxpnv06mcz5dnymu2ldf0rlb2c'}

    if op == 'global':
        if type(query) == str:
            query.lower()
        body = f'fields name, involved_companies.company.name, involved_companies.developer, genres.name, release_dates.y, release_dates.human, platforms.name, summary, cover.url, cover.image_id; limit 10; search "{query}";'

    elif op == 'single':
        body = f'fields id, name, involved_companies.company.name, involved_companies.developer, genres.name, release_dates.y, release_dates.human, platforms.name, summary, cover.url, cover.image_id; where id = {query};'

    elif op == 'custom':
        body = f'fields id, {fields}; where id = {query};'


    response = requests.post('https://api.igdb.com/v4/games', headers=header, data=body)

    if(not response.ok):
        print(f'ERRORE {response.status_code} CON LA QUERY SU IGDB, ATTENZIONE DATI FALSATI')

    return response.json()




def create_result_query(dict_query, user_id = None):
    
    r = types.InlineQueryResultArticle(
        id = dict_query.get("id"),
        title = dict_query.get("title"),
        input_message_content = create_input_message(dict_query),
        reply_markup=InlineKeyboardMarkup(keyboard= [ [InlineKeyboardButton("Add to list", callback_data = str(f'add_list-{dict_query.get("id")}')), InlineKeyboardButton("Reviews", login_url=types.LoginUrl(f'{DOMAIN}/{dict_query.get("id")}'))], [InlineKeyboardButton("Search a videogame", switch_inline_query_current_chat=""), InlineKeyboardButton("Search Price", callback_data=f"{dict_query.get('id')}-")] ] ),
        description = dict_query.get("year_date") + " - " + dict_query.get("genres"),
        thumb_url = dict_query.get("image"),
        thumb_height=10,
        thumb_width=10
    )

    return r

def check_query(single_result, type_image = None):
    query_dict = {}

    # check id
    try:
        query_dict["id"] = str(single_result['id'])
    
    except KeyError as key:
        query_dict["id"] = "Unknown id"

    #check nome
    try:
        query_dict["title"] = str(single_result['name'])

    except KeyError as key:
        query_dict["title"] = "Unknown name"

    #check sviluppatore
    try:
        for i in range (len(single_result['involved_companies'])):
            if  single_result['involved_companies'][i]['developer']:
                query_dict["developer"] = str(single_result['involved_companies'][i]['company']['name'])

    except KeyError as key:
        query_dict["developer"] = "Unknown developer"

    #check genere
    try:
        genres = ""
        for i in range(len(single_result['genres'])):
            if i == 1:
                genres += ", " + str(single_result['genres'][i]['name'])
                break
                
            
            genres += str(single_result['genres'][i]['name'])
        
        query_dict["genres"] = genres

    except KeyError as key:
        query_dict["genres"] = "Unknown genre(s)"

    #check data rilascio human
    try:
        query_dict["year_date"] = str(single_result['release_dates'][0]['y'])

    except KeyError as key:
        query_dict["year_date"] = "Unknown release date"

    #check data rilascio y
    try:
        query_dict["human_rdate"] = str(single_result['release_dates'][0]['human'])

    except KeyError as key:
        query_dict["human_rdate"] = "Unknown full release date"

    #check piattaforme
    try:
        platforms = ""
        for i in range (len(single_result['platforms'])):
            if i == (len(single_result['platforms']) - 1):
                # Non mettere virgole
                platforms += str(single_result['platforms'][i]['name'])

            else:
                #Altrimenti fallo
                platforms += str(f"{single_result['platforms'][i]['name']}, ")
        
        query_dict["platforms"] = platforms

    except KeyError as key:
        query_dict["platforms"] = "Unknown platform(s)"

    #check plot
    try:
        query_dict["plot"] = str(single_result['summary'])

    except KeyError as key:
        query_dict["plot"] = "Unknown plot"

    #check immagine
    try:
        if type_image == None:
            query_dict["image"] = str("https://images.igdb.com/igdb/image/upload/t_720p/" + single_result['cover']['image_id'] + ".jpg")
        
        else:
            query_dict["image"] = str(f"https://images.igdb.com/igdb/image/upload/t_{type_image}/" + single_result['cover']['image_id'] + ".jpg")

    except KeyError as key:
        link_stardard_image = "https://cdn1.iconfinder.com/data/icons/ui-set-6/100/Question_Mark-512.png"
        query_dict["image"] = link_stardard_image
    
    return query_dict

def create_input_message(dict_query):

    r = types.InputTextMessageContent(

                        f'<b>TITLE:</b>\n{dict_query.get("title")} - {dict_query.get("developer")} \n \n' +
                        f'<b>GENRES:</b>\n{dict_query.get("genres")} \n \n' +
                        f'<b>RELEASE IN:</b>\n{dict_query.get("human_rdate")} \n \n' +
                        f'<b>PLATFORMS:</b>\n{dict_query.get("platforms")} \n \n' +
                        f'<b>PLOT:</b>\n{dict_query.get("plot")}' +
                        '\n<a href="'+dict_query.get("image")+'">&#8205;</a>',
                        parse_mode= 'HTML'
                        )

    return r

def getChart(label, data, tot):
    qc = QuickChart()

    qc.width = 400
    qc.height = 400
    qc.background_color = 'white'

    

    qc.config = {
                    "type": "doughnut",
                    "data": {
                        "labels": label,
                        "datasets": [{
                            "data": data,
                            'backgroundColor': ["#264653", "#2A9D8F", "#E9C46A", "#F4A261", "#E76F51"],
                            'borderColor' : "black",
                            'borderWidth': 1.5,
                        }]
                    },
                    "options": {
                        "plugins" : { 
                            "datalabels":{
                                'align': 'center',
                                'display': True,
                                'color': 'white',
                                'backgroundColor': "black",
                                'borderRadius': 25,
                                'font': {
                                    'size': 25,
                                }
                            },

                    'doughnutlabel': {
                        'labels': [{
                        'text': tot,
                        'color': 'black',
                        'font': {
                            'size': 30,
                            'weight': 'bold'
                        }
                      }, {
                        'color': 'black',
                        'text': 'total searches',
                        }]
                    }
                }
            }
        }   

    return qc.get_short_url()


def placeholder(status):

    if status:
        return "on"
    
    else:
        return "off"

def getdata(request_data):

    # GENERAZIONE STRINGA DELLE INFO DELL'UTENTE
    string = ""
    for key in sorted(request_data):
        string += f"{key}={request_data[key]}\n"
    
    return string.rstrip(string[-1])

def dict_user(message):
    msg = message.split('\n')

    temp_dict = {'id'         : '',
                 'first_name' : '',
                 'last_name'  : '',
                 'photo_url'  : "https://villadewinckels.it/wp-content/uploads/2021/05/default-user-image.png"
                }

    for i in msg:
        info = i.split("=")
        temp_dict.update({info[0] : info[1]})

    return temp_dict


def check_data_login(request_data):
    
    BOT_TOKEN = '5269272556:AAHx5ce4Y5lmanTByfqi348W76MayfHg8r4'

    # MI PRENDO L'HASH E LO TOLGO DAL DATA
    hash = request_data.get('hash')
    request_data.pop('hash', None)

    # HASH DEL TOKEN DEL BOT
    secret_key = hashlib.sha256(BOT_TOKEN.encode()).digest()
    
    # STRINGA DELLE INFO DELL'UTENTE
    total_params = getdata(request_data)

    # HASH DEL TOKEN E DELLA STRINGA DELLE INFO DELL'UTENTE + HEXA
    received_hash = hmac.new(secret_key, msg=total_params.encode(), digestmod=hashlib.sha256).hexdigest()

    # CONTROLLI FINALI
    if hash == received_hash:
        return True

    else:
        return False

def generate_key():
    # CHIAMARE SOLO UNA VOLTA PER GENERARE UNA CHIAVE
    key = Fernet.generate_key()
    with open("secret.key", "wb") as key_file:
        key_file.write(key)

def load_key():
    # CARICA LA CHIAVE PER LA CRIPTAZIONE E DECRIPTAZIONE
    return open("secret.key", "rb").read()

def encrypt_message(message):

    key = load_key()
    encoded_message = message.encode()
    f = Fernet(key)
    encrypted_message = f.encrypt(encoded_message)

    return encrypted_message

def decrypt_message(encrypted_message):

    key = load_key()
    f = Fernet(key)
    decrypted_message = f.decrypt(encrypted_message)

    return decrypted_message.decode()

