from datetime import date, datetime, timedelta
import telebot
from typing import OrderedDict
import firebase_admin
from hashlib import sha256
import hmac
import hashlib
from flask import Flask, jsonify, render_template, request, redirect, make_response
from firebase_admin import credentials, firestore
from rsa import encrypt
from util_function import *
import collections

DOMAIN = ""
app = Flask(__name__)

cred = credentials.Certificate("")
firebase_admin.initialize_app(cred)
db = firestore.client()

@app.route("/review/<game_id>/", methods=['GET', 'POST'])
def pag_review_user(game_id):

    bot = bot_instance()

    cookie_info = request.cookies.get('token_rev')
    sup = []

    if cookie_info != "null" and type(cookie_info) == str:

        byte_info = str.encode(cookie_info)
        info_user_rev = dict_user(decrypt_message(byte_info))

        # PER CREARE IL NUOVO COMMENTO E INSERIRLO NEL DB
        new_doc = db.collection(u'comments').document(str(info_user_rev.get('id')) + str(game_id))

#------------------------------------------------------------------------------------------------
        # USARE update_info()

        update_info(db, info_user_rev.get('id'), info_user_rev.get('first_name'), info_user_rev.get('last_name'))
#------------------------------------------------------------------------------------------------

        # QUESTA FUNZIONE VALE SOLO QUANDO SI RICARICA LA PAGINA, NON SI ATTIVA ALLA PRIMA VISITA.
        # MA SOLO QUANDO L'UTENTE VUOLE DIGITARE UN COMMENTO E PREME "SEND"
        if request.form.get("text_field") != None and request.form.get("text_field") != "":

            # VEDERE SE LASCIARE OPPURE NO
            if new_doc.get().exists == False:

                new_doc.set({
                    u'date': datetime.today().strftime('%d/%m %H:%M'),
                    u'game_id': game_id,
                    u'user_id': info_user_rev.get('id'),
                    u'text_message': request.form.get("text_field"),
                })
            
            sup.append(False)
        
        else:
            if new_doc.get().exists == False:
                sup.append(True)
            
            else:
                sup.append(False)

    else:
        # NON MOSTRARE LA BARRA DEI COMMENTI
        sup.append(False)
    

    # QUA SI PRENDONO I COMMENTI ( fare sempre )

    docs = db.collection(u'comments').where(u'game_id', u'==', game_id)
    info = check_query(call_to_db(game_id, "custom", "name, cover.url, cover.image_id")[0], "720p")
    sup.append(info.get('title'))
    sup.append(info.get('image'))
    
    arr = []
    
    if len(docs.get()) != 0:
        for i in docs.get():
            my_dict = {}
            my_dict['date'] = i.to_dict().get('date')
            my_dict['text'] = i.to_dict().get('text_message')

            # SI PRENDONO I DATI DELL'UTENTE
            user_info = db.collection(u'users').document(i.to_dict().get('user_id')).get()
            my_dict['name'] = modify_string(user_info.to_dict().get('user_first'), user_info.to_dict().get('user_last'))
            
            try:
                img = bot.get_user_profile_photos(i.to_dict().get('user_id')).photos[0][2]
                url_img = bot.get_file_url(img.file_id)
            except:
                url_img = 'https://villadewinckels.it/wp-content/uploads/2021/05/default-user-image.png'
            
            my_dict['pfp'] = url_img
            arr.append(my_dict)

    return render_template("review_page_user.jinja2", data=arr, info=sup)


@app.route("/<game_id>/", methods=['GET'])
def info_page(game_id):

    request_data = request.args.to_dict()

    # SE CI SONO DATI, FARE IL CHECK
    if len(request_data) != 0:
        if check_data_login(request_data):
            # SE IL CHECK E' ANDATO A BUON FINE, ALLORA IMPOSTA I COOKIE E RITORNA QUELL'URL
            encrypt_data = encrypt_message(getdata(request_data))
            response = make_response(redirect(f"{DOMAIN}/review/{game_id}/"))
            response.set_cookie(key='token_rev', value=encrypt_data, expires=(datetime.utcnow() + timedelta(days=366)).strftime("%a, %d %b %Y %H:%M:%S GMT"))
            return response
        
    # SE IL CHECK DEI DATI NON E' ANDATO A BUON FINE OPPURE SE E' TUTTO VUOTO
    print("CONTROLLO ERRATO O DATI ASSENTI")
    response = make_response(redirect(f"{DOMAIN}/review/{game_id}/"))
    response.set_cookie(key='token_rev', value="null")
    return response

   

   



app.run(host="0.0.0.0", port=8080, debug=True)


