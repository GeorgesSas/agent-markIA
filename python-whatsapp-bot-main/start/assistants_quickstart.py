import openai
import shelve
from dotenv import load_dotenv
import os
import time
import traceback

# Charger la clé API depuis .env
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

if not OPENAI_API_KEY:
    raise ValueError("⚠️ OPEN_AI_API_KEY manquant dans .env")

openai.api_key = OPENAI_API_KEY

# Ton assistant existant (créé une seule fois dans l’interface OpenAI ou avec un autre script)
ASSISTANT_ID = "asst_QJuRk8I4LaZwcXh2FHVMnsTF"


# --------------------------------------------------------------
# Gestion des threads utilisateurs
# --------------------------------------------------------------
def check_if_thread_exists(wa_id):
    with shelve.open("threads_db") as threads_shelf:
        return threads_shelf.get(wa_id, None)

def store_thread(wa_id, thread_id):
    with shelve.open("threads_db", writeback=True) as threads_shelf:
        threads_shelf[wa_id] = thread_id


# --------------------------------------------------------------
# Générer une réponse
# --------------------------------------------------------------
def generate_response(message_body, wa_id, name):
    try:
        # Vérifier si un thread existe déjà
        thread_id = check_if_thread_exists(wa_id)

        if thread_id is None:
            print(f"🆕 Création d’un nouveau thread pour {name} ({wa_id})")
            thread = openai.beta.threads.create()
            store_thread(wa_id, thread.id)
            thread_id = thread.id
        else:
            print(f"📂 Récupération du thread existant pour {name} ({wa_id})")
            thread = openai.beta.threads.retrieve(thread_id)

        # Ajouter le message utilisateur
        openai.beta.threads.messages.create(
            thread_id=thread_id,
            role="user",
            content=message_body,
        )

        # Exécuter l’assistant
        return run_assistant(thread)

    except Exception as e:
        print("💥 Erreur dans generate_response :", e)
        traceback.print_exc()
        return "Désolé, je rencontre un problème technique."


# --------------------------------------------------------------
# Lancer l’assistant
# --------------------------------------------------------------
def run_assistant(thread):
    try:
        run = openai.beta.threads.runs.create(
            thread_id=thread.id,
            assistant_id=ASSISTANT_ID,
        )

        # Attendre la fin du traitement
        while run.status != "completed":
            time.sleep(0.5)
            run = openai.beta.threads.runs.retrieve(thread_id=thread.id, run_id=run.id)

        # Récupérer la dernière réponse
        messages = openai.beta.threads.messages.list(thread_id=thread.id)
        return messages.data[0].content[0].text.value

    except Exception as e:
        print("💥 Erreur dans run_assistant :", e)
        traceback.print_exc()
        return "Je n'ai pas pu traiter la demande."


# --------------------------------------------------------------
# Test hors webhook
# --------------------------------------------------------------
if __name__ == "__main__":
    print(generate_response("What's the check in time?", "123", "John"))
    print(generate_response("What's the pin for the lockbox?", "456", "Sarah"))
    print(generate_response("What was my previous question?", "123", "John"))
