from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler,
    filters, CallbackContext, ConversationHandler
)
from dotenv import load_dotenv
import os
from utils.check_token import get_token_info
from utils.build_tx import send_proxy_swap_tx
from config.settings import BOT_TOKEN, DEFAULT_SLIPPAGE

load_dotenv()

# Conversation states
TOKEN_ADDR, BUY_AMOUNT, SLIPPAGE, CONFIRM_BUY = range(4)

async def start(update: Update, context: CallbackContext) -> None:
    keyboard = [
        [
            InlineKeyboardButton("🚀 Snipe Token", callback_data="snipe_token"),
            InlineKeyboardButton("🛒 Manual Buy", callback_data="manual_buy"),
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("🔥 Welcome to your Binance Sniper Bot 🔫\n\nChoose an option:", reply_markup=reply_markup)

async def button_callback(update: Update, context: CallbackContext) -> int:
    query = update.callback_query
    await query.answer()

    if query.data == "manual_buy":
        await query.message.reply_text("📥 Send the **token contract address** you want to manually buy 👇")
        return TOKEN_ADDR

async def manual_get_token_address(update: Update, context: CallbackContext) -> int:
    contract = update.message.text.strip()
    context.user_data['token_address'] = contract

    token_info = get_token_info(contract)
    if not token_info:
        await update.message.reply_text("❌ Couldn’t fetch token info.")
        return ConversationHandler.END

    text = (
        f"📊 Token Info:\n"
        f"Name: {token_info['name']}\n"
        f"Symbol: {token_info['symbol']}\n"
        f"Liquidity: {token_info['liquidity']} BNB"
    )

    buy_buttons = [
        [InlineKeyboardButton("0.005 BNB", callback_data="buy_0.005"),
         InlineKeyboardButton("0.01 BNB", callback_data="buy_0.01")],
        [InlineKeyboardButton("0.05 BNB", callback_data="buy_0.05"),
         InlineKeyboardButton("0.1 BNB", callback_data="buy_0.1")]
    ]
    reply_markup = InlineKeyboardMarkup(buy_buttons)
    await update.message.reply_text(text, reply_markup=reply_markup)
    return BUY_AMOUNT

async def buy_amount_callback(update: Update, context: CallbackContext) -> int:
    query = update.callback_query
    await query.answer()

    amount = float(query.data.replace("buy_", ""))
    context.user_data['buy_amount'] = amount

    slippage_buttons = [
        [InlineKeyboardButton("0.5%", callback_data="slip_0.5"),
         InlineKeyboardButton("1%", callback_data="slip_1")],
        [InlineKeyboardButton("3%", callback_data="slip_3"),
         InlineKeyboardButton("5%", callback_data="slip_5")]
    ]
    reply_markup = InlineKeyboardMarkup(slippage_buttons)
    await query.message.reply_text("⚙️ Choose slippage:", reply_markup=reply_markup)
    return SLIPPAGE

async def slippage_callback(update: Update, context: CallbackContext) -> int:
    query = update.callback_query
    await query.answer()

    slippage = float(query.data.replace("slip_", ""))
    context.user_data['slippage'] = slippage

    confirm_button = [
        [InlineKeyboardButton("✅ Confirm Buy", callback_data="confirm_buy")]
    ]
    reply_markup = InlineKeyboardMarkup(confirm_button)

    await query.message.reply_text(
        f"✅ Ready to buy {context.user_data['buy_amount']} BNB of token `{context.user_data['token_address']}` with {slippage}% slippage.",
        reply_markup=reply_markup
    )
    return CONFIRM_BUY

async def confirm_buy_callback(update: Update, context: CallbackContext) -> int:
    query = update.callback_query
    await query.answer()

    token_address = context.user_data['token_address']
    buy_amount = context.user_data['buy_amount']
    slippage = context.user_data.get('slippage', DEFAULT_SLIPPAGE)

    await query.message.reply_text("🚀 Sending transaction... please wait.")

    tx_hash = send_proxy_swap_tx(token_address, buy_amount, slippage)
    if tx_hash:
        await query.message.reply_text(f"✅ Swap sent!\n📦 Tx Hash: `{tx_hash}`", parse_mode='Markdown')
    else:
        await query.message.reply_text("❌ Failed to send transaction.")

    return ConversationHandler.END

async def cancel(update: Update, context: CallbackContext) -> int:
    await update.message.reply_text("❌ Operation cancelled.")
    return ConversationHandler.END

def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    manual_buy_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(button_callback, pattern="^manual_buy$")],
        states={
            TOKEN_ADDR: [MessageHandler(filters.TEXT & ~filters.COMMAND, manual_get_token_address)],
            BUY_AMOUNT: [CallbackQueryHandler(buy_amount_callback, pattern="^buy_")],
            SLIPPAGE: [CallbackQueryHandler(slippage_callback, pattern="^slip_")],
            CONFIRM_BUY: [CallbackQueryHandler(confirm_buy_callback, pattern="^confirm_buy$")]
        },
        fallbacks=[CommandHandler('cancel', cancel)]
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(manual_buy_handler)

    print("[✓] Telegram bot running...")
    app.run_polling()

if __name__ == '__main__':
    main()
