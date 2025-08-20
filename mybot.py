from groq import Groq
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, MessageHandler, filters, ContextTypes, CommandHandler, CallbackQueryHandler
import asyncio
import os
from dotenv import load_dotenv

# Clés API
load_dotenv()
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")


# Vérifier que la clé est bien chargée
if not GROQ_API_KEY:
    raise ValueError("La variable GROQ_API_KEY n'est pas définie !")
client = Groq(api_key=GROQ_API_KEY)

# Historique et langue des utilisateurs
user_histories = {}
user_languages = {}

# Fonction pour envoyer “typing” en continu
async def send_typing_continuous(context, chat_id):
    while True:
        await context.bot.send_chat_action(chat_id=chat_id, action="typing")
        await asyncio.sleep(2)  # plus rapide que 3 sec

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
                "👋 Salut ! Je suis ton assistant IA. Je peux t’aider surtout avec le développement web, les applications et les technologies." \
                "ça dependra de ton objectif "
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
    user_languages[user_id] = query.data  # 'fr' ou 'en'
    
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

# Fonction principale pour gérer les messages
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    user_message = update.message.text

    if not user_message:
        await update.message.reply_text("⚠️ Message vide.")
        return

    if user_id not in user_histories:
        user_histories[user_id] = []

    # Détecter la langue et créer l'instruction système
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

    # Ajouter instruction système + message utilisateur
    user_histories[user_id].append(system_instruction)
    user_histories[user_id].append({"role": "user", "content": user_message})

    try:
        chat_id = update.effective_chat.id
        typing_task = asyncio.create_task(send_typing_continuous(context, chat_id))

        # Générer la réponse avec Groq
        response = client.chat.completions.create(
            model="llama3-8b-8192",
            messages=user_histories[user_id]
        )

        bot_reply = response.choices[0].message.content
        user_histories[user_id].append({"role": "assistant", "content": bot_reply})

        typing_task.cancel()
        await asyncio.sleep(0.05)  # petite pause avant l'affichage

        # Envoyer le message progressivement par blocs de 3 mots
        sent_message = await update.message.reply_text("...")
        text_to_send = ""
        words = bot_reply.split()
        i = 0
        while i < len(words):
            block = " ".join(words[i:i+3])
            text_to_send += block + " "
            await sent_message.edit_text(text_to_send)
            await asyncio.sleep(0.02)  # ultra-rapide
            i += 3

    except Exception as e:
        await update.message.reply_text("⚠️ Une erreur est survenue.")
        print(e)

# Lancer le bot
def main():
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("clear", clear))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(CallbackQueryHandler(set_language))
    print("Bot lancé ✅")
    app.run_polling()

if __name__ == "__main__":
    main()
