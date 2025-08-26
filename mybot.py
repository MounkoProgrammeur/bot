from fastapi import FastAPI, Request
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler
import os
import logging
from groq import Groq
import asyncio
from dotenv import load_dotenv

# Configuration des logs
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialisation de FastAPI
app = FastAPI()

# Clés API
load_dotenv()
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")

# Vérifier les clés
if not TELEGRAM_TOKEN or not GROQ_API_KEY:
    raise ValueError("TELEGRAM_TOKEN ou GROQ_API_KEY non défini !")

client = Groq(api_key=GROQ_API_KEY)

# Historique et langue des utilisateurs
user_histories = {}
user_languages = {}

# Initialisation de l'application Telegram
application = Application.builder().token(TELEGRAM_TOKEN).build()

# Commande /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    if user_id not in user_languages:
        keyboard = [
            [InlineKeyboardButton("Français 🇫🇷", callback_data='fr')],
            [InlineKeyboardButton("English 🇬🇧", callback_data='en')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            "👋 Salut ! Bienvenue sur ton assistant IA spécialisé en informatique et développement developpé par mon maitre JIMMY MOUNKO.\n"
            "Choisis ta langue pour commencer / Choose your language:",
            reply_markup=reply_markup
        )
    else:
        language = user_languages[user_id]
        if language == 'fr':
            await update.message.reply_text(
                "👋 Salut ! Je suis ton assistant IA. Je peux t’aider surtout avec le développement web, les applications et les technologies.\n"
                "Pose-moi une question et je te répondrai !\n\n"
                "Commandes utiles :\n"
                "/clear - Effacer l’historique de la conversation\n"
                "/help - Aide"
            )
        else:
            await update.message.reply_text(
                "👋 Hello! I’m your AI assistant. I mainly help with web development, apps, and technology questions. "
                "Ask me anything and I’ll answer!\n\n"
                "Useful commands:\n"
                "/clear - Clear the conversation history\n"
                "/help - Help"
            )

# Gestion de la sélection de langue
async def set_language(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    user_languages[user_id] = query.data
    if query.data == 'fr':
        await query.edit_message_text("🇫🇷 Langue sélectionnée : Français ! Pose-moi une question.")
    else:
        await query.edit_message_text("🇬🇧 Language selected: English! Ask me a question.")

# Commande /help
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    language = user_languages.get(user_id, 'fr')
    if language == 'fr':
        await update.message.reply_text(
            "ℹ️ Voici ce que je peux faire :\n"
            "- Répondre aux questions sur l’informatique et le développement\n"
        )
    else:
        await update.message.reply_text(
            "ℹ️ Here’s what I can do:\n"
            "- Answer questions about IT and development\n"
        )

# Commande /clear
async def clear(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    if user_id in user_histories:
        user_histories[user_id] = []
    language = user_languages.get(user_id, 'fr')
    if language == 'fr':
        await update.message.reply_text("🧹 Historique effacé. La conversation recommence à zéro.")
    else:
        await update.message.reply_text("🧹 History cleared. The conversation starts over.")

# Fonction pour gérer les messages
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    user_message = update.message.text
    logger.info(f"Message reçu de {user_id}: {user_message}")

    if not user_message:
        await update.message.reply_text("⚠️ Message vide.")
        return

    if user_id not in user_histories:
        user_histories[user_id] = []

    language = user_languages.get(user_id, 'fr')
    system_instruction = {
        "role": "system",
        "content": (
           
             "Agis comme un expert senior dans le domaine concerné par ma demande. Ton objectif est de m’apporter une réponse complète, précise, et optimisée pour un usage réel. "
            "Voici comment je veux que tu fonctionnes :"
           " 1. Structure ton raisonnement avec des titres, des points clés, et une logique claire (comme un consultant McKinsey ou un professeur de haut niveau)."
            "2. Corrige mes imprécisions. Si ma demande est floue ou mal formulée, reformule-la ou pose-moi une question pour clarifier avant de répondre."
            "3. Ne te limite pas à l’évidence. Pousse l’analyse plus loin, propose des alternatives, explore les conséquences."
            "4. Sois exigeant : ne me dis pas ce que j’ai envie d’entendre, mais ce que j’ai besoin d’entendre pour progresser."
           " 5. Donne toujours un exemple concret ou un cas d’usage pour illustrer ta réponse."
            "6. Sois critique et analytique. Si une idée est mauvaise ou à risque, dis-le clairement, explique pourquoi."
            "7. Fais court, mais dense. pas de blabla. Va droit au but."
            "8. Ajoute toujours une question ou une piste pour que je continue à creuser. Tu es là pour m’élever."
            "Précision importante : je préfère une réponse honnête, nuancée et utile, même si elle est brutale, plutôt qu'une réponse flatteuse ou simpliste."
            "Si tu as compris, commence ta réponse par : Compris. Voici une réponse calibrée comme demandé."
            "Si l’utilisateur pose une question sur un autre sujet, répond poliment et brièvement. "
            "Répond toujours de manière courte et concise (1-3 phrases), mais pas toujours obligé. "
            "Lis le message de l’utilisateur et répond dans la même langue que lui. "
            "Ajoute des emojis appropriés selon le ton et le contexte. "
            "Reste poli, amical et compréhensible."
            
        )
    }

    user_histories[user_id].append(system_instruction)
    user_histories[user_id].append({"role": "user", "content": user_message})

    try:
        # Envoi de l'action "typing" pendant le traitement
        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
        
        # Appel à l'API Groq
        response = client.chat.completions.create(
            model="llama3-8b-8192",
            messages=user_histories[user_id]
        )
        bot_reply = response.choices[0].message.content
        user_histories[user_id].append({"role": "assistant", "content": bot_reply})

        # Envoi progressif du message (par blocs de 3 mots)
        sent_message = await update.message.reply_text("...")
        text_to_send = ""
        words = bot_reply.split()
        i = 0
        while i < len(words):
            block = " ".join(words[i:i+3])
            text_to_send += block + " "
            await sent_message.edit_text(text_to_send)
            await asyncio.sleep(0.02)  # Pause rapide pour effet visuel
            i += 3
        
        logger.info(f"Réponse envoyée : {bot_reply}")
    except Exception as e:
        await update.message.reply_text("⚠️ Une erreur est survenue.")
        logger.error(f"Erreur dans handle_message : {e}", exc_info=True)

# Endpoint webhook
@app.post("/webhook")
async def webhook(request: Request):
    try:
        data = await request.json()
        logger.info(f"Requête webhook reçue : {data}")
        update = Update.de_json(data, application.bot)
        logger.info(f"Update traité : {update}")
        await application.process_update(update)
        logger.info("Mise à jour traitée avec succès")
        return {"status": "ok"}
    except Exception as e:
        logger.error(f"Erreur dans le webhook : {e}", exc_info=True)
        return {"status": "error"}

# Route santé
@app.get("/health")
async def health():
    return {"status": "running"}

# Route racine pour éviter "Non trouvé"
@app.get("/")
async def root():
    return {"message": "Bot Telegram en ligne"}

# Initialisation et configuration du webhook au démarrage
@app.on_event("startup")
async def on_startup():
    await application.initialize()  # Initialisation explicite
    webhook_url = os.environ.get("WEBHOOK_URL", "https://bot-1xw3.onrender.com/webhook")
    await application.bot.set_webhook(url=webhook_url)
    logger.info(f"Webhook configuré sur {webhook_url}")

# Ajout des handlers
application.add_handler(CommandHandler("start", start))
application.add_handler(CommandHandler("help", help_command))
application.add_handler(CommandHandler("clear", clear))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
application.add_handler(CallbackQueryHandler(set_language))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))