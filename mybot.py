from fastapi import FastAPI, Request
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler
import os
import logging
from groq import Groq

# Configuration des logs
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialisation de FastAPI
app = FastAPI()

# Clés API
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
            "Tu es un expert en informatique et en développement : web, applications, logiciels, technologies et programmation. "
            "Ton objectif principal est de répondre aux questions liées à l’informatique et au développement. "
            "Si l’utilisateur pose une question sur un autre sujet, répond poliment et brièvement. "
            "Répond toujours de manière courte et concise (1-3 phrases). "
            "Lis le message de l’utilisateur et répond dans la même langue que lui. "
            "Ajoute des emojis appropriés selon le ton et le contexte. "
            "Reste poli, amical et compréhensible."
        )
    }

    user_histories[user_id].append(system_instruction)
    user_histories[user_id].append({"role": "user", "content": user_message})

    try:
        response = client.chat.completions.create(
            model="llama3-8b-8192",
            messages=user_histories[user_id]
        )
        bot_reply = response.choices[0].message.content
        user_histories[user_id].append({"role": "assistant", "content": bot_reply})
        await update.message.reply_text(bot_reply)
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