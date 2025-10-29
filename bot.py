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

class TwitterFollowingTracker:
    def __init__(self, twitter_credentials, telegram_bot_token):
        # Try using API keys first, fallback to bearer token
        if all(k in twitter_credentials for k in ['api_key', 'api_secret', 'access_token', 'access_secret']):
            self.twitter_client = tweepy.Client(
                consumer_key=twitter_credentials['api_key'],
                consumer_secret=twitter_credentials['api_secret'],
                access_token=twitter_credentials['access_token'],
                access_token_secret=twitter_credentials['access_secret']
            )
            logger.info("Using OAuth 1.0a authentication")
        else:
            self.twitter_client = tweepy.Client(bearer_token=twitter_credentials['bearer_token'])
            logger.info("Using Bearer Token authentication")
        
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
║  👥 FOLLOWING TRACKER BOT  ║
╚═══════════════════════╝

🎯 <b>Track Following Real-Time:</b>
━━━━━━━━━━━━━━━━━━━━━━
👥 Siapa yang baru di-follow
📊 Detail profil target
⏰ Notifikasi instant

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

⚡ <b>Optimized untuk Twitter Free API</b>
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
➡️ {user.data.public_metrics['following_count']:,} following

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
            # Initialize following list
            init_msg = await query.edit_message_text("⏳ Memuat following list awal...")
            
            following = self.twitter_client.get_users_following(
                id=user_data.id,
                max_results=1000,
                user_fields=['name', 'username', 'public_metrics']
            )
            
            following_set = set()
            if following.data:
                following_set = {user.id for user in following.data}
            
            self.tracked_accounts[username] = {
                'id': user_data.id,
                'name': user_data.name,
                'chain': chain_code,
                'followers': user_data.public_metrics['followers_count'],
                'following_count': user_data.public_metrics['following_count'],
                'following_list': following_set,
                'last_check': datetime.now()
            }
            
            chain_info = CHAINS[chain_code]
            msg = f"""
✅ <b>Berhasil Ditambahkan</b>

👤 @{username}
📝 {self.escape_html(user_data.name)}
⛓️ {chain_info['emoji']} {chain_info['name']}
➡️ Tracking {len(following_set)} following

Ketik /start_monitoring untuk mulai!
            """
            await init_msg.edit_text(msg, parse_mode='HTML')
            
            del self.pending_adds[chat_id]
            logger.info(f"Ditambahkan: @{username} ({chain_code}) - {len(following_set)} following")
            
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
                following_count = len(data['following_list'])
                msg += f"  • @{username} - {self.escape_html(data['name'])}\n"
                msg += f"    ➡️ {following_count} following\n"
        
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
    
    async def check_following(self):
        """Cek following baru untuk semua tracked accounts"""
        for username, data in self.tracked_accounts.items():
            try:
                logger.info(f"Checking @{username}...")
                
                # Get current following list
                following = self.twitter_client.get_users_following(
                    id=data['id'],
                    max_results=1000,
                    user_fields=['name', 'username', 'public_metrics', 'description', 'created_at']
                )
                
                if following.data:
                    current_following = {user.id for user in following.data}
                    
                    # Detect new follows
                    if data['following_list']:
                        new_follows = current_following - data['following_list']
                        
                        if new_follows:
                            logger.info(f"Found {len(new_follows)} new follows for @{username}")
                            new_users = [user for user in following.data if user.id in new_follows]
                            
                            for new_user in new_users:
                                await self.notify_new_follow(username, new_user, data['name'], data['chain'])
                                await asyncio.sleep(1)  # Delay between notifications
                    
                    # Update following list
                    data['following_list'] = current_following
                    data['following_count'] = len(current_following)
                    data['last_check'] = datetime.now()
                
                # Delay between accounts to avoid rate limit
                await asyncio.sleep(60)  # 1 menit per akun
                
            except tweepy.errors.TooManyRequests as e:
                logger.warning(f"⚠️ Rate limit hit! Menunggu 15 menit...")
                await self.send_to_all("⚠️ <b>Rate Limit Twitter API</b>\n\nBot pause 15 menit untuk avoid ban")
                await asyncio.sleep(900)  # Wait 15 minutes
            except tweepy.errors.Forbidden as e:
                logger.error(f"❌ Forbidden: {e}")
                await self.send_to_all(f"❌ <b>Twitter API Error</b>\n\nCek Bearer Token atau akses API")
                break
            except Exception as e:
                logger.error(f"Error cek @{username}: {e}")
                await asyncio.sleep(10)
    
    async def notify_new_follow(self, username, new_user, display_name, chain):
        """Notifikasi following baru"""
        chain_info = CHAINS[chain]
        
        # Get account age
        account_age = ""
        if hasattr(new_user, 'created_at') and new_user.created_at:
            created = new_user.created_at
            age_days = (datetime.now(created.tzinfo) - created).days
            if age_days < 30:
                account_age = f"\n⚠️ Akun baru ({age_days} hari)"
            elif age_days < 365:
                account_age = f"\n📅 Akun {age_days // 30} bulan"
            else:
                account_age = f"\n📅 Akun {age_days // 365} tahun"
        
        # Get bio
        bio = ""
        if hasattr(new_user, 'description') and new_user.description:
            bio_text = self.escape_html(new_user.description[:150])
            bio = f"\n📝 {bio_text}{'...' if len(new_user.description) > 150 else ''}"
        
        msg = f"""
👥 <b>FOLLOWING BARU!</b>

🎯 <b>@{username}</b> ({self.escape_html(display_name)})
⛓️ {chain_info['emoji']} {chain_info['name']}

━━━━━━━━━━━━━━━━━━━━
🆕 <b>Baru Follow:</b>

👤 <a href="https://twitter.com/{new_user.username}">@{new_user.username}</a>
📝 {self.escape_html(new_user.name)}
👥 {new_user.public_metrics['followers_count']:,} followers
💬 {new_user.public_metrics['tweet_count']:,} tweets{bio}{account_age}

⏰ {datetime.now().strftime('%d/%m/%Y %H:%M WIB')}
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
                    disable_web_page_preview=False
                )
            except Exception as e:
                logger.error(f"Error kirim ke {chat_id}: {e}")
    
    async def monitoring_loop(self, context: ContextTypes.DEFAULT_TYPE):
        """Loop monitoring"""
        logger.info("Monitoring dimulai")
        while self.monitoring:
            if self.tracked_accounts:
                await self.check_following()
            else:
                await asyncio.sleep(30)
    
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
        total_following = 0
        for data in self.tracked_accounts.values():
            chain = data['chain']
            chain_counts[chain] = chain_counts.get(chain, 0) + 1
            total_following += len(data['following_list'])
        
        chains_text = "\n".join([
            f"  {CHAINS[c]['emoji']} {CHAINS[c]['name']}: {count} akun"
            for c, count in sorted(chain_counts.items(), key=lambda x: x[1], reverse=True)
        ])
        
        # Calculate check interval
        accounts_count = len(self.tracked_accounts)
        cycle_time = accounts_count * 1  # 1 menit per akun
        
        msg = f"""
✅ <b>Monitoring Aktif!</b>

📊 Tracking:
{chains_text}

➡️ Total: {total_following} following dipantau
⏱️ Check interval: ~{cycle_time} menit per cycle
⚠️ Twitter Free API: 15 req/15min limit
📢 Notifikasi: Real-time

<i>Rekomendasi: Track maksimal 5 akun untuk hasil optimal</i>
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
        total_following = 0
        for data in self.tracked_accounts.values():
            chain = data['chain']
            chain_counts[chain] = chain_counts.get(chain, 0) + 1
            total_following += len(data['following_list'])
        
        chains_list = "\n".join([
            f"  {CHAINS[c]['emoji']} {CHAINS[c]['name']}: {count}"
            for c, count in sorted(chain_counts.items(), key=lambda x: x[1], reverse=True)
        ]) if chain_counts else "  Belum ada"
        
        # Last check info
        last_check = ""
        if self.tracked_accounts:
            latest = max(self.tracked_accounts.values(), key=lambda x: x['last_check'])
            last_check = f"\n🕐 Last check: {latest['last_check'].strftime('%H:%M:%S')}"
        
        msg = f"""
📊 <b>Status Bot</b>

{status_icon} {status_text}

👥 Total: {len(self.tracked_accounts)} akun
➡️ Monitoring: {total_following} following
📢 Subscribers: {len(self.chat_ids)}{last_check}

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
        # Use polling with drop_pending_updates to avoid conflicts
        self.telegram_app.run_polling(
            allowed_updates=Update.ALL_TYPES,
            drop_pending_updates=True,  # Skip old updates
            close_loop=False
        )


# ==================== MAIN ====================
if __name__ == "__main__":
    TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
    
    # Try to get OAuth credentials first
    twitter_credentials = {}
    
    if os.getenv("TWITTER_API_KEY") and os.getenv("TWITTER_API_SECRET"):
        twitter_credentials = {
            'api_key': os.getenv("TWITTER_API_KEY"),
            'api_secret': os.getenv("TWITTER_API_SECRET"),
            'access_token': os.getenv("TWITTER_ACCESS_TOKEN"),
            'access_secret': os.getenv("TWITTER_ACCESS_SECRET")
        }
        logger.info("Found OAuth credentials")
    elif os.getenv("TWITTER_BEARER_TOKEN"):
        twitter_credentials = {
            'bearer_token': os.getenv("TWITTER_BEARER_TOKEN")
        }
        logger.info("Found Bearer Token")
    else:
        logger.error("❌ No Twitter credentials found!")
        logger.error("Set either:")
        logger.error("  1. TWITTER_API_KEY, TWITTER_API_SECRET, TWITTER_ACCESS_TOKEN, TWITTER_ACCESS_SECRET")
        logger.error("  2. TWITTER_BEARER_TOKEN")
        exit(1)
    
    if not TELEGRAM_BOT_TOKEN:
        logger.error("❌ TELEGRAM_BOT_TOKEN tidak ditemukan!")
        exit(1)
    
    try:
        bot = TwitterFollowingTracker(twitter_credentials, TELEGRAM_BOT_TOKEN)
        bot.run()
    except Exception as e:
        logger.error(f"Bot crash: {e}")
        raise
