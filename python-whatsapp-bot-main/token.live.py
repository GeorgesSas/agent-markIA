# token-live.py
# Script pour générer un token WhatsApp longue durée (60 jours)

import requests
import os
from dotenv import load_dotenv, set_key

def get_credentials_from_user():
    """Demande les credentials à l'utilisateur si pas dans .env"""
    print("🔧 Configuration du token longue durée WhatsApp")
    print("=" * 50)
    
    # Charger le .env existant
    load_dotenv()
    
    app_id = os.getenv("WHATSAPP_APP_ID")
    app_secret = os.getenv("WHATSAPP_APP_SECRET")
    current_token = os.getenv("ACCESS_TOKEN")
    
    # Demander les infos manquantes
    if not app_id:
        app_id = input("📱 Entrez votre WHATSAPP_APP_ID: ").strip()
        set_key('.env', 'WHATSAPP_APP_ID', app_id)
        print("✅ WHATSAPP_APP_ID sauvé dans .env")
    
    if not app_secret:
        app_secret = input("🔐 Entrez votre WHATSAPP_APP_SECRET: ").strip()
        set_key('.env', 'WHATSAPP_APP_SECRET', app_secret)
        print("✅ WHATSAPP_APP_SECRET sauvé dans .env")
    
    if not current_token:
        print("❌ ACCESS_TOKEN manquant dans .env")
        return None, None, None
    
    return app_id, app_secret, current_token

def generate_long_lived_token():
    """Génère un token WhatsApp longue durée (60 jours)"""
    
    print("\n🚀 Génération du token longue durée...")
    
    # Récupérer les credentials
    app_id, app_secret, current_token = get_credentials_from_user()
    
    if not all([app_id, app_secret, current_token]):
        print("❌ Credentials manquants. Vérifiez votre .env")
        return False
    
    # URL pour échanger le token
    url = "https://graph.facebook.com/v18.0/oauth/access_token"
    
    params = {
        'grant_type': 'fb_exchange_token',
        'client_id': app_id,
        'client_secret': app_secret,
        'fb_exchange_token': current_token
    }
    
    try:
        print("📡 Envoi de la requête à Facebook...")
        response = requests.get(url, params=params)
        data = response.json()
        
        if 'access_token' in data:
            new_token = data['access_token']
            expires_in = data.get('expires_in', 'inconnu')
            
            # Calculer les jours d'expiration
            if expires_in != 'inconnu':
                days = int(expires_in) // 86400  # secondes -> jours
                print(f"📅 Le nouveau token expire dans: {days} jours")
            
            # Sauvegarder le nouveau token
            set_key('.env', 'ACCESS_TOKEN', new_token)
            
            print("\n" + "=" * 50)
            print("✅ TOKEN LONGUE DURÉE GÉNÉRÉ AVEC SUCCÈS !")
            print("=" * 50)
            print(f"📱 Nouveau token: {new_token[:20]}...")
            print(f"💾 Sauvé automatiquement dans .env")
            print(f"⏰ Valide pendant ~{days if expires_in != 'inconnu' else '60'} jours")
            print("\n🎉 Votre bot n'aura plus de problème de token pendant 2 mois !")
            
            return True
            
        else:
            print("\n❌ ERREUR lors de la génération:")
            print(f"📄 Réponse Facebook: {data}")
            
            # Messages d'erreur courants
            if 'error' in data:
                error = data['error']
                if 'Invalid' in error.get('message', ''):
                    print("\n💡 Solutions possibles:")
                    print("1. Vérifiez votre APP_ID et APP_SECRET")
                    print("2. Votre token actuel est peut-être expiré")
                    print("3. Générez un nouveau token depuis Meta Business Manager")
            
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Erreur de connexion: {e}")
        print("💡 Vérifiez votre connexion internet")
        return False
    
    except Exception as e:
        print(f"❌ Erreur inattendue: {e}")
        return False

def verify_token_works():
    """Vérifie que le nouveau token fonctionne"""
    print("\n🔍 Vérification du token...")
    
    load_dotenv()
    token = os.getenv("ACCESS_TOKEN")
    
    if not token:
        print("❌ Aucun token trouvé")
        return False
    
    try:
        # Test simple avec l'API WhatsApp
        url = f"https://graph.facebook.com/v18.0/me?access_token={token}"
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            print("✅ Token vérifié : FONCTIONNE !")
            return True
        else:
            print(f"❌ Token invalide (Code: {response.status_code})")
            return False
            
    except Exception as e:
        print(f"❌ Erreur vérification: {e}")
        return False

def show_help():
    """Affiche l'aide pour trouver les credentials"""
    print("\n" + "=" * 60)
    print("📚 AIDE : Comment trouver vos credentials WhatsApp")
    print("=" * 60)
    print("""
📍 Pour trouver WHATSAPP_APP_ID et WHATSAPP_APP_SECRET :

1. 🌐 Allez sur: https://business.facebook.com
2. 👤 Connectez-vous à votre compte Meta Business
3. 📱 Cliquez sur votre app WhatsApp Business
4. ⚙️  Menu "Paramètres" > "Informations de base"
5. 📋 Copiez :
   • ID de l'app = WHATSAPP_APP_ID
   • Clé secrète de l'app = WHATSAPP_APP_SECRET

📝 Note: Ces infos sont différentes de votre token d'accès !
    """)

if __name__ == "__main__":
    print("🤖 Mark.AI - Générateur de Token Longue Durée")
    print("=" * 50)
    
    while True:
        print("\nQue voulez-vous faire ?")
        print("1. 🔄 Générer un token longue durée")
        print("2. 🔍 Vérifier le token actuel")
        print("3. 📚 Aide pour trouver les credentials")
        print("4. 🚪 Quitter")
        
        choice = input("\nVotre choix (1-4): ").strip()
        
        if choice == "1":
            success = generate_long_lived_token()
            if success:
                verify_token_works()
        
        elif choice == "2":
            verify_token_works()
        
        elif choice == "3":
            show_help()
        
        elif choice == "4":
            print("\n👋 À bientôt !")
            break
        
        else:
            print("❌ Choix invalide. Utilisez 1, 2, 3 ou 4.")
        
        input("\nAppuyez sur Entrée pour continuer...")