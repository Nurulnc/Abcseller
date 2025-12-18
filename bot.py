import logging
from uuid import uuid4
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ConversationHandler,
    filters,
    ContextTypes,
)

# --- Configuration ---
TOKEN = "YOUR_BOT_TOKEN_HERE"
ADMIN_ID = 1651695602
BINANCE_ID = "38017799"

# Product Data (Only USD/USDT Pricing)
PRODUCTS = {
    "proxy_1gb":  {"name": "🚀 AbcProxy 1GB",  "usd": 2.20},
    "proxy_2gb":  {"name": "🚀 AbcProxy 2GB",  "usd": 4.10},
    "proxy_3gb":  {"name": "🚀 AbcProxy 3GB",  "usd": 6.00},
    "proxy_5gb":  {"name": "🚀 AbcProxy 5GB",  "usd": 9.80},
    "proxy_10gb": {"name": "🚀 AbcProxy 10GB", "usd": 18.50},
}

# States
SELECT_PLAN, CONFIRM_ORDER, UPLOAD_PROOF, SUBMIT_TXID = range(4)
orders = {}

# --- Handlers ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "🌟 *Welcome to AbcProxy Official Store*\n"
        "━━━━━━━━━━━━━━━━━━\n"
        "Get high-speed residential proxies with instant delivery.\n\n"
        "🛒 *Select your preferred plan to order:*"
    )
    
    buttons = [[InlineKeyboardButton(info["name"], callback_data=f"plan_{key}")] for key, info in PRODUCTS.items()]
    reply_markup = InlineKeyboardMarkup(buttons)
    
    if update.message:
        await update.message.reply_text(text, parse_mode="Markdown", reply_markup=reply_markup)
    else:
        await update.callback_query.edit_message_text(text, parse_mode="Markdown", reply_markup=reply_markup)
    return SELECT_PLAN

async def plan_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    plan_key = query.data.replace("plan_", "")
    product = PRODUCTS[plan_key]
    context.user_data.update({
        "plan_key": plan_key, 
        "plan_name": product["name"],
        "total": product["usd"],
        "curr": "USDT"
    })
    
    instruction = (
        f"💎 *Plan:* {product['name']}\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"⚠️ *Payment Instructions (Binance)*\n"
        f"Please send exact `{product['usd']} USDT` to:\n\n"
        f"📍 Binance Pay ID: `{BINANCE_ID}`\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"✅ Once payment is done, click the button below."
    )
    
    kb = [
        [InlineKeyboardButton("✅ I Have Paid", callback_data="paid_confirm")],
        [InlineKeyboardButton("🔙 Back to Plans", callback_data="back_start")]
    ]
    await query.edit_message_text(instruction, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(kb))
    return CONFIRM_ORDER

async def confirm_order(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data == "back_start":
        return await start(update, context)
        
    oid = str(uuid4())[:8].upper()
    context.user_data["oid"] = oid
    
    await query.edit_message_text(f"📸 *Order ID:* `{oid}`\n\nPlease upload the **Payment Screenshot**.")
    return UPLOAD_PROOF

async def get_proof(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.photo:
        await update.message.reply_text("⚠️ Please send a screenshot image.")
        return UPLOAD_PROOF
    
    context.user_data["photo"] = update.message.photo[-1].file_id
    await update.message.reply_text("🔢 Type your **Binance TXID** or **Reference Code**:")
    return SUBMIT_TXID

async def get_txid_final(update: Update, context: ContextTypes.DEFAULT_TYPE):
    txid = update.message.text.strip()
    oid = context.user_data["oid"]
    
    orders[oid] = {**context.user_data, "uid": update.effective_user.id, "user": update.effective_user.username}
    
    admin_msg = (
        f"🔔 *New Proxy Order (Binance Only)*\n"
        f"ID: `{oid}`\n"
        f"User: @{orders[oid]['user']}\n"
        f"Plan: {context.user_data['plan_name']}\n"
        f"Total: ${context.user_data['total']} USDT\n"
        f"TrxID: `{txid}`\n\n"
        f"Approve: `/approve {oid} CD_KEY_HERE`"
    )
    await context.bot.send_photo(ADMIN_ID, context.user_data["photo"], caption=admin_msg, parse_mode="Markdown")
    
    await update.message.reply_text("✅ *Order Submitted!*\n\nOur admin is verifying your Binance payment. Your CD-Key will be sent here shortly.")
    return ConversationHandler.END

async def approve_proxy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return
    try:
        oid = context.args[0].upper()
        cd_key = context.args[1]
        order = orders.get(oid)
        
        if not order:
            await update.message.reply_text("❌ Order not found.")
            return

        delivery_text = (
            f"🎉 *Order Approved!*\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"📦 Product: {order['plan_name']}\n"
            f"🆔 Order ID: `{oid}`\n\n"
            f"🔑 *Your CD-Key:* `{cd_key}`\n\n"
            f"Thank you for choosing us!"
        )
        
        await context.bot.send_message(chat_id=order["uid"], text=delivery_text, parse_mode="Markdown")
        await update.message.reply_text(f"✅ Success! Key delivered for order {oid}")
        del orders[oid]
    except IndexError:
        await update.message.reply_text("❌ Use: `/approve ORDER_ID CD_KEY`")

def main():
    app = ApplicationBuilder().token(TOKEN).build()
    logging.basicConfig(level=logging.INFO)

    conv = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            SELECT_PLAN:   [CallbackQueryHandler(plan_selected, pattern="^plan_")],
            CONFIRM_ORDER: [CallbackQueryHandler(confirm_order, pattern="paid_confirm"), CallbackQueryHandler(start, pattern="back_start")],
            UPLOAD_PROOF:  [MessageHandler(filters.PHOTO, get_proof)],
            SUBMIT_TXID:   [MessageHandler(filters.TEXT & ~filters.COMMAND, get_txid_final)],
        },
        fallbacks=[CommandHandler("start", start)],
    )

    app.add_handler(conv)
    app.add_handler(CommandHandler("approve", approve_proxy))

    print("AbcProxy Binance-Only Bot Online...")
    app.run_polling()

if __name__ == "__main__":
    main()

