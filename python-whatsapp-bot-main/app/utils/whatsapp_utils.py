import logging
from flask import current_app, jsonify
import json
import requests
import os
import requests 
import tempfile
from openai import OpenAI
import shelve 

from start.assistants_quickstart import generate_response
import re


def log_http_response(response):
    logging.info(f"Status: {response.status_code}")
    logging.info(f"Content-type: {response.headers.get('content-type')}")
    logging.info(f"Body: {response.text}")


def get_text_message_input(recipient, text):
    return json.dumps(
        {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": recipient,
            "type": "text",
            "text": {"preview_url": False, "body": text},
        }
    )


#def generate_response(response):
    # Return text in uppercase
    #return response.upper()


def send_message(data):
    headers = {
        "Content-type": "application/json",
        "Authorization": f"Bearer {current_app.config['ACCESS_TOKEN']}",
    }

    url = f"https://graph.facebook.com/{current_app.config['VERSION']}/{current_app.config['PHONE_NUMBER_ID']}/messages"

    try:
        response = requests.post(
            url, data=data, headers=headers, timeout=10
        )  # 10 seconds timeout as an example
        response.raise_for_status()  # Raises an HTTPError if the HTTP request returned an unsuccessful status code
    except requests.Timeout:
        logging.error("Timeout occurred while sending message")
        return jsonify({"status": "error", "message": "Request timed out"}), 408
    except (
        requests.RequestException
    ) as e:  # This will catch any general request exception
        logging.error(f"Request failed due to: {e}")
        return jsonify({"status": "error", "message": "Failed to send message"}), 500
    else:
        # Process the response as normal
        log_http_response(response)
        return response


def process_text_for_whatsapp(text):
    # Remove brackets
    pattern = r"\【.*?\】"
    # Substitute the pattern with an empty string
    text = re.sub(pattern, "", text).strip()

    # Pattern to find double asterisks including the word(s) in between
    pattern = r"\*\*(.*?)\*\*"

    # Replacement pattern with single asterisks
    replacement = r"*\1*"

    # Substitute occurrences of the pattern with the replacement
    whatsapp_style_text = re.sub(pattern, replacement, text)

    return whatsapp_style_text

def get_user_profile(wa_id, name):
    """Récupère ou crée le profil utilisateur"""
    try:
        with shelve.open("users_db") as users_shelf:
            user_data = users_shelf.get(wa_id, None)
            
            if user_data is None:
                # Nouvel utilisateur
                from datetime import datetime
                user_data = {
                    "wa_id": wa_id,
                    "name": name,
                    "created_at": datetime.now().isoformat(),
                    "last_activity": datetime.now().isoformat(),
                    "message_count": 0,
                    "preferences": {},
                    "business_info": {}
                }
                users_shelf[wa_id] = user_data
                print(f"👤 Nouvel utilisateur enregistré: {name} ({wa_id})")
            else:
                # Utilisateur existant - mise à jour
                from datetime import datetime
                user_data["last_activity"] = datetime.now().isoformat()
                user_data["message_count"] += 1
                user_data["name"] = name  # Mise à jour du nom si changé
                users_shelf[wa_id] = user_data
                
            return user_data
    except Exception as e:
        print(f"Erreur profil utilisateur: {e}")
        return {"wa_id": wa_id, "name": name}

def process_whatsapp_message(body):
    """Version multi-utilisateurs améliorée"""
    try:
        wa_id = body["entry"][0]["changes"][0]["value"]["contacts"][0]["wa_id"]
        name = body["entry"][0]["changes"][0]["value"]["contacts"][0]["profile"]["name"]
        message = body["entry"][0]["changes"][0]["value"]["messages"][0]
        
        # Récupérer/créer le profil utilisateur
        user_profile = get_user_profile(wa_id, name)
        
        # Traitement du message (texte ou vocal)
        if message.get("type") == "audio":
            media_id = message["audio"]["id"]
            print(f"🎵 Message vocal de {name} ({wa_id})")
            
            audio_file = download_whatsapp_audio(media_id)
            if audio_file:
                message_body = transcribe_audio(audio_file)
                if message_body:
                    message_body = f"[Message vocal transcrit] {message_body}"
                else:
                    message_body = "Désolé, je n'ai pas pu comprendre votre message vocal."
            else:
                message_body = "Erreur lors de la réception du message vocal."
                
        elif message.get("type") == "text":
            message_body = message["text"]["body"]
        else:
            message_body = "Je ne peux traiter que les messages texte et vocaux."
        
        print(f"📱 Message de {name}: {message_body[:50]}...")
        
        # Générer réponse personnalisée avec contexte utilisateur
        response = generate_response(message_body, wa_id, name)
        response = process_text_for_whatsapp(response)
        
        # IMPORTANT: Envoyer à l'utilisateur spécifique (pas un numéro fixe)
        data = get_text_message_input(wa_id, response)
        send_message(data)
        
    except Exception as e:
        print(f"Erreur traitement message: {e}")
        # Envoyer message d'erreur à l'utilisateur spécifique
        error_message = "Désolé, j'ai rencontré un problème technique. Réessayez dans quelques instants."
        try:
            data = get_text_message_input(wa_id, error_message)
            send_message(data)
        except:
            print("Impossible d'envoyer le message d'erreur")

def get_user_stats():
    """Statistiques des utilisateurs pour monitoring"""
    try:
        with shelve.open("users_db") as users_shelf:
            stats = {
                "total_users": len(users_shelf),
                "users": []
            }
            
            for wa_id, user_data in users_shelf.items():
                stats["users"].append({
                    "name": user_data.get("name", "Unknown"),
                    "wa_id": wa_id,
                    "message_count": user_data.get("message_count", 0),
                    "last_activity": user_data.get("last_activity", "Unknown")
                })
            
            return stats
    except Exception as e:
        print(f"Erreur stats: {e}")
        return {"error": str(e)}

def is_valid_whatsapp_message(body):
    """
    Check if the incoming webhook event has a valid WhatsApp message structure.
    """
    return (
        body.get("object")
        and body.get("entry")
        and body["entry"][0].get("changes")
        and body["entry"][0]["changes"][0].get("value")
        and body["entry"][0]["changes"][0]["value"].get("messages")
        and body["entry"][0]["changes"][0]["value"]["messages"][0]
    )

def download_whatsapp_audio(media_id):
    """Télécharge le fichier audio depuis WhatsApp"""
    try:
        # Récupérer l'URL du média
        headers = {
            "Authorization": f"Bearer {current_app.config['ACCESS_TOKEN']}",
        }
        
        media_url = f"https://graph.facebook.com/{current_app.config['VERSION']}/{media_id}"
        media_response = requests.get(media_url, headers=headers)
        media_data = media_response.json()
        
        # Télécharger le fichier audio
        audio_url = media_data['url']
        audio_response = requests.get(audio_url, headers=headers)
        
        # Sauvegarder temporairement
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.ogg')
        temp_file.write(audio_response.content)
        temp_file.close()
        
        return temp_file.name
        
    except Exception as e:
        print(f"Erreur téléchargement audio: {e}")
        return None

def transcribe_audio(audio_file_path):
    """Transcrit l'audio en texte avec OpenAI Whisper"""
    try:
        client = OpenAI(api_key=current_app.config.get('OPENAI_API_KEY'))
        
        with open(audio_file_path, 'rb') as audio_file:
            transcript = client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file,
                language="fr"  # ou "auto" pour détecter automatiquement
            )
        
        # Supprimer le fichier temporaire
        os.unlink(audio_file_path)
        
        return transcript.text
        
    except Exception as e:
        print(f"Erreur transcription: {e}")
        if os.path.exists(audio_file_path):
            os.unlink(audio_file_path)
        return None