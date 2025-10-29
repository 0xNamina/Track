import tweepy
import telegram
from telegram.ext import Application, CommandHandler, ContextTypes, CallbackQueryHandler
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
import asyncio
import os
from datetime import datetime
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Chain configurations - Untuk label aja
CHAINS = {
    'ETH': {'name': 'Ethereum', 'emoji': '⛓️'},
    'BSC': {'name': 'BNB Chain', 'emoji': '🟡'},
    'SOL': {'name': 'Solana', 'emoji': '🟣'},
    'ARB': {'name': 'Arbitrum', 'emoji': '🔷'},
    'OP': {'name': 'Optimism', 'emoji': '🔴'},
    'BASE': {'name': 'Base', 'emoji': '🔵'},
    'AVAX': {'name': 'Avalanche', 'emoji': '🔺'},
    'MATIC': {'name': 'Polygon', 'emoji': '🟣'},
    'FTM': {'name': 'Fantom', 'emoji': '👻'},
    'CELO': {'name': 'Celo', 'emoji': '💚'},
    'AURORA': {'name': 'Aurora', 'emoji': '🌈'},
    'CRONOS': {'name': 'Cronos', 'emoji': '💎'},
    'KAVA': {'name': 'Kava', 'emoji': '🟢'},
    'CANTO': {'name': 'Canto', 'emoji': '🎵'},
    'SUI': {'name': 'Sui', 'emoji': '🌊'},
    'APT': {'name': 'Aptos', 'emoji': '🎯'},
    'SEI': {'name': 'Sei', 'emoji': '⚡'},
    'INJ': {'name': 'Injective', 'emoji': '💉'},
    'TON': {'name': 'TON', 'emoji': '💠'},
    'LINEA': {'name': 'Linea', 'emoji': '📏'},
    'ZKSYNC': {'name': 'zkSync Era', 'emoji': '⚙️'},
    'SCROLL': {'name': 'Scroll', 'emoji': '📜'},
    'MANTA': {'name': 'Manta Pacific', 'emoji': '🦈'},
    'BLAST': {'name': 'Blast', 'emoji': '💥'},
    'METIS': {'name': 'Metis', 'emoji': '🌟'},
    'MULTI': {'name': 'Multi-Chain', 'emoji': '🌐'}
}

class TwitterTelegramTracker:
    def __init__(self, twitter_bearer_token, telegram_bot_token):
        self.twitter_client = tweepy.Client(bearer_token=twitter_bearer_token)
        self.telegram_app = Application.builder().token(telegram_bot_token).build()
        
        self.tracked_accounts = {}
        self.chat_ids = set()
        self.monitoring = False
        self.pending_adds = {}
        
        logger.info("Bot berhasil diinisialisasi")
    
    def escape_html(self, text):
        """Escape HTML characters"""
        return text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handler untuk /start command"""
        chat_id = update.effective_chat.id
        self.chat_ids.add(chat_id)
        
        welcome_msg = """
╔═══════════════════════╗
║  🔍 TWITTER ACTIVITY BOT  ║
╚═══════════════════════╝

🎯 <b>Track Aktivitas Real-Time:</b>
━━━━━━━━━━━━━━━━━━━━━━
📝 Tweet Baru
🔁 Retweet
💬 Reply/Komentar
👥 Following Baru

📋 <b>Perintah:</b>
━━━━━━━━━━━━━━━━━━━━━━
/add @username - Tambah tracking
/list - Lihat daftar
/remove @username - Hapus tracking
/start_monitoring - Mulai track
/stop_monitoring - Stop track
/status - Cek status

💡 <b>Label chain untuk identifikasi CT
mana yang aktif di chain apa</b>
        """
        await update.message.reply_text(welcome_msg, parse_mode='HTML')
        logger.info(f"User baru: {chat_id}")
    
    async def add_account(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handler untuk /add command"""
        if not context.args:
            await update.message.reply_text(
                "❌ Gunakan: /add @username\n"
                "Contoh: /add @lookonchain",
                parse_mode='HTML'
            )
            return
        
        username = context.args[0].replace('@', '')
        chat_id = update.effective_chat.id
        
        loading_msg = await update.message.reply_text(f"⏳ Mengecek @{username}...")
        
        try:
            user = self.twitter_client.get_user(
                username=username,
                user_fields=['public_metrics']
            )
            
            if user.data:
                self.pending_adds[chat_id] = {
                    'username': username,
                    'user_data': user.data
                }
                
                # Create keyboard 4 kolom
                keyboard = []
                row = []
                for idx, (chain_code, chain_info) in enumerate(CHAINS.items()):
                    button = InlineKeyboardButton(
                        f"{chain_info['emoji']} {chain_code}",
                        callback_data=f"chain_{chain_code}"
                    )
                    row.append(button)
                    
                    if len(row) == 4 or idx == len(CHAINS) - 1:
                        keyboard.append(row)
                        row = []
                
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                msg = f"""
✅ <b>Akun Ditemukan</b>

👤 @{username}
📝 {self.escape_html(user.data.name)}
👥 {user.data.public_metrics['followers_count']:,} followers

⛓️ <b>Pilih Chain:</b>
Label untuk identifikasi CT ini aktif di chain mana
                """
                
                await loading_msg.edit_text(msg, parse_mode='HTML', reply_markup=reply_markup)
                
        except Exception as e:
            await loading_msg.edit_text(f"❌ Error: {str(e)}")
    
    async def chain_selection_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handler untuk chain selection"""
        query = update.callback_query
        await query.answer()
        
        chat_id = query.message.chat_id
        chain_code = query.data.replace('chain_', '')
        
        if chat_id not in self.pending_adds:
            await query.edit_message_text("❌ Session expired, /add lagi")
            return
        
        pending = self.pending_adds[chat_id]
        username = pending['username']
        user_data = pending['user_data']
        
        try:
            self.tracked_accounts[username] = {
                'id': user_data.id,
                'name': user_data.name,
                'chain': chain_code,
                'followers': user_data.public_metrics['followers_count'],
                'following': user_data.public_metrics['following_count'],
                'last_tweet_id': None,
                'last_check': datetime.now(),
                'following_list': set()
            }
            
            chain_info = CHAINS[chain_code]
            msg = f"""
✅ <b>Berhasil Ditambahkan</b>

👤 @{username}
📝 {self.escape_html(user_data.name)}
⛓️ {chain_info['emoji']} {chain_info['name']}

Ketik /start_monitoring untuk mulai!
            """
            await query.edit_message_text(msg, parse_mode='HTML')
            
            del self.pending_adds[chat_id]
            logger.info(f"Ditambahkan: @{username} ({chain_code})")
            
        except Exception as e:
            await query.edit_message_text(f"❌ Error: {str(e)}")
    
    async def list_accounts(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handler untuk /list command"""
        if not self.tracked_accounts:
            await update.message.reply_text(
                "🔭 Belum ada tracking\n\n"
                "Gunakan: /add @username"
            )
            return
        
        # Group by chain
        chains_groups = {}
        for username, data in self.tracked_accounts.items():
            chain = data['chain']
            if chain not in chains_groups:
                chains_groups[chain] = []
            chains_groups[chain].append((username, data))
        
        msg = "📋 <b>Daftar Tracking</b>\n\n"
        
        for chain_code in sorted(chains_groups.keys()):
            chain_info = CHAINS[chain_code]
            accounts = chains_groups[chain_code]
            
            msg += f"\n{chain_info['emoji']} <b>{chain_info['name']}</b>\n"
            for username, data in accounts:
                msg += f"  • @{username} - {self.escape_html(data['name'])}\n"
        
        msg += f"\n━━━━━━━━━━━━━━━━━━━━━━\n"
        msg += f"📊 Total: {len(self.tracked_accounts)} akun"
        
        await update.message.reply_text(msg, parse_mode='HTML')
    
    async def remove_account(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handler untuk /remove command"""
        if not context.args:
            await update.message.reply_text("❌ Gunakan: /remove @username")
            return
        
        username = context.args[0].replace('@', '')
        
        if username in self.tracked_accounts:
            del self.tracked_accounts[username]
            await update.message.reply_text(f"✅ @{username} dihapus")
            logger.info(f"Dihapus: @{username}")
        else:
            await update.message.reply_text(f"❌ @{username} tidak ditemukan")
    
    async def check_activities(self):
        """Cek semua aktivitas user"""
        for username, data in self.tracked_accounts.items():
            try:
                # CEK TWEETS & RETWEETS & REPLIES
                tweets = self.twitter_client.get_users_tweets(
                    id=data['id'],
                    max_results=10,
                    since_id=data['last_tweet_id'],
                    tweet_fields=['created_at', 'referenced_tweets'],
                    expansions=['referenced_tweets.id']
                )
                
                if tweets.data:
                    data['last_tweet_id'] = tweets.data[0].id
                    
                    for tweet in reversed(tweets.data):
                        is_retweet = False
                        is_reply = False
                        
                        if tweet.referenced_tweets:
                            for ref in tweet.referenced_tweets:
                                if ref.type == 'retweeted':
                                    is_retweet = True
                                elif ref.type == 'replied_to':
                                    is_reply = True
                        
                        if is_retweet:
                            await self.notify_retweet(username, tweet, data['name'], data['chain'])
                        elif is_reply:
                            await self.notify_reply(username, tweet, data['name'], data['chain'])
                        else:
                            await self.notify_tweet(username, tweet, data['name'], data['chain'])
                
                # CEK FOLLOWING BARU
                try:
                    following = self.twitter_client.get_users_following(
                        id=data['id'],
                        max_results=100,
                        user_fields=['name', 'username', 'public_metrics']
                    )
                    
                    if following.data:
                        current_following = {user.id for user in following.data}
                        
                        if data['following_list']:
                            new_follows = current_following - data['following_list']
                            if new_follows:
                                new_users = [user for user in following.data if user.id in new_follows]
                                for new_user in new_users[:5]:
                                    await self.notify_new_follow(username, new_user, data['name'], data['chain'])
                        
                        data['following_list'] = current_following
                except Exception as e:
                    logger.error(f"Error cek following @{username}: {e}")
                
            except tweepy.errors.TooManyRequests:
                logger.warning("Rate limit, menunggu...")
                await asyncio.sleep(900)
            except Exception as e:
                logger.error(f"Error cek @{username}: {e}")
            
            await asyncio.sleep(3)
    
    async def notify_tweet(self, username, tweet, display_name, chain):
        """Notifikasi tweet baru"""
        chain_info = CHAINS[chain]
        text = self.escape_html(tweet.text)
        
        msg = f"""
📝 <b>TWEET BARU</b>

👤 @{username} ({self.escape_html(display_name)})
⛓️ {chain_info['emoji']} {chain_info['name']}

{text[:400]}{'...' if len(tweet.text) > 400 else ''}

🔗 <a href="https://twitter.com/{username}/status/{tweet.id}">Lihat Tweet</a>
⏰ {tweet.created_at.strftime('%d/%m/%Y %H:%M')}
        """
        await self.send_to_all(msg)
    
    async def notify_retweet(self, username, tweet, display_name, chain):
        """Notifikasi retweet"""
        chain_info = CHAINS[chain]
        text = self.escape_html(tweet.text)
        
        msg = f"""
🔁 <b>RETWEET</b>

👤 @{username} ({self.escape_html(display_name)})
⛓️ {chain_info['emoji']} {chain_info['name']}

{text[:400]}{'...' if len(tweet.text) > 400 else ''}

🔗 <a href="https://twitter.com/{username}/status/{tweet.id}">Lihat Tweet</a>
⏰ {tweet.created_at.strftime('%d/%m/%Y %H:%M')}
        """
        await self.send_to_all(msg)
    
    async def notify_reply(self, username, tweet, display_name, chain):
        """Notifikasi reply/comment"""
        chain_info = CHAINS[chain]
        text = self.escape_html(tweet.text)
        
        msg = f"""
💬 <b>REPLY/KOMENTAR</b>

👤 @{username} ({self.escape_html(display_name)})
⛓️ {chain_info['emoji']} {chain_info['name']}

{text[:400]}{'...' if len(tweet.text) > 400 else ''}

🔗 <a href="https://twitter.com/{username}/status/{tweet.id}">Lihat Tweet</a>
⏰ {tweet.created_at.strftime('%d/%m/%Y %H:%M')}
        """
        await self.send_to_all(msg)
    
    async def notify_new_follow(self, username, new_user, display_name, chain):
        """Notifikasi following baru"""
        chain_info = CHAINS[chain]
        
        msg = f"""
👥 <b>FOLLOWING BARU</b>

👤 @{username} ({self.escape_html(display_name)})
⛓️ {chain_info['emoji']} {chain_info['name']}

🆕 Baru follow:
👤 @{new_user.username}
📝 {self.escape_html(new_user.name)}
👥 {new_user.public_metrics['followers_count']:,} followers

🔍 <a href="https://twitter.com/{new_user.username}">Cek Profil</a>
⏰ {datetime.now().strftime('%d/%m/%Y %H:%M')}
        """
        await self.send_to_all(msg)
    
    async def send_to_all(self, message):
        """Kirim ke semua subscriber"""
        for chat_id in self.chat_ids:
            try:
                await self.telegram_app.bot.send_message(
                    chat_id=chat_id,
                    text=message,
                    parse_mode='HTML',
                    disable_web_page_preview=True
                )
            except Exception as e:
                logger.error(f"Error kirim ke {chat_id}: {e}")
    
    async def monitoring_loop(self, context: ContextTypes.DEFAULT_TYPE):
        """Loop monitoring"""
        logger.info("Monitoring dimulai")
        while self.monitoring:
            if self.tracked_accounts:
                await self.check_activities()
            await asyncio.sleep(60)
    
    async def start_monitoring_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Start monitoring"""
        if not self.tracked_accounts:
            await update.message.reply_text(
                "❌ Belum ada tracking\n"
                "Gunakan: /add @username"
            )
            return
        
        if self.monitoring:
            await update.message.reply_text("⚠️ Monitoring sudah jalan")
            return
        
        self.monitoring = True
        context.application.create_task(self.monitoring_loop(context))
        
        chain_counts = {}
        for data in self.tracked_accounts.values():
            chain = data['chain']
            chain_counts[chain] = chain_counts.get(chain, 0) + 1
        
        chains_text = "\n".join([
            f"  {CHAINS[c]['emoji']} {CHAINS[c]['name']}: {count} akun"
            for c, count in sorted(chain_counts.items(), key=lambda x: x[1], reverse=True)
        ])
        
        msg = f"""
✅ <b>Monitoring Aktif!</b>

📊 Tracking:
{chains_text}

⏱️ Interval: 60 detik
📢 Notifikasi: Real-time
        """
        await update.message.reply_text(msg, parse_mode='HTML')
        logger.info("Monitoring dimulai")
    
    async def stop_monitoring_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Stop monitoring"""
        self.monitoring = False
        await update.message.reply_text("⏸️ Monitoring dihentikan")
        logger.info("Monitoring dihentikan")
    
    async def status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Cek status bot"""
        status_icon = "🟢" if self.monitoring else "🔴"
        status_text = "AKTIF" if self.monitoring else "TIDAK AKTIF"
        
        chain_counts = {}
        for data in self.tracked_accounts.values():
            chain = data['chain']
            chain_counts[chain] = chain_counts.get(chain, 0) + 1
        
        chains_list = "\n".join([
            f"  {CHAINS[c]['emoji']} {CHAINS[c]['name']}: {count}"
            for c, count in sorted(chain_counts.items(), key=lambda x: x[1], reverse=True)
        ]) if chain_counts else "  Belum ada"
        
        msg = f"""
📊 <b>Status Bot</b>

{status_icon} {status_text}

👥 Total: {len(self.tracked_accounts)} akun
📢 Subscribers: {len(self.chat_ids)}

⛓️ Per Chain:
{chains_list}
        """
        await update.message.reply_text(msg, parse_mode='HTML')
    
    def run(self):
        """Start bot"""
        self.telegram_app.add_handler(CommandHandler('start', self.start_command))
        self.telegram_app.add_handler(CommandHandler('add', self.add_account))
        self.telegram_app.add_handler(CommandHandler('list', self.list_accounts))
        self.telegram_app.add_handler(CommandHandler('remove', self.remove_account))
        self.telegram_app.add_handler(CommandHandler('start_monitoring', self.start_monitoring_command))
        self.telegram_app.add_handler(CommandHandler('stop_monitoring', self.stop_monitoring_command))
        self.telegram_app.add_handler(CommandHandler('status', self.status_command))
        self.telegram_app.add_handler(CallbackQueryHandler(self.chain_selection_callback, pattern='^chain_'))
        
        logger.info("🤖 Bot berjalan di Railway...")
        self.telegram_app.run_polling(allowed_updates=Update.ALL_TYPES)


# ==================== MAIN ====================
if __name__ == "__main__":
    TWITTER_BEARER_TOKEN = os.getenv("TWITTER_BEARER_TOKEN")
    TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
    
    if not TWITTER_BEARER_TOKEN or not TELEGRAM_BOT_TOKEN:
        logger.error("❌ Environment variables tidak ditemukan!")
        logger.error("Set TWITTER_BEARER_TOKEN dan TELEGRAM_BOT_TOKEN")
        exit(1)
    
    try:
        bot = TwitterTelegramTracker(TWITTER_BEARER_TOKEN, TELEGRAM_BOT_TOKEN)
        bot.run()
    except Exception as e:
        logger.error(f"Bot crash: {e}")
        raise
