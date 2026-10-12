import telebot
import pymupdf as fitz
import os
from supabase import create_client, Client
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

BOT_TOKEN = "8876009144:AAH2txX37Vzwp1Tu6O_YnSemAG1imamx4L4"
SUPABASE_URL = "https://imylliwshodkqytjnlqs.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImlteWxsaXdzaG9ka3F5dGpubHFzIiwicm9sZSI6ImFub24iLCJpYXQiOjE3OTE3MzIxMzUsImV4cCI6MjEwNzMwODEzNX0.nIJ2XSFry_ZEkL1KjO10DhNM4cBFVkw-4rGA4tNblvU"

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
bot = telebot.TeleBot(BOT_TOKEN)

# អនុគមន៍កាត់យករូបក្របជា File រូបភាព (.png)
def extract_cover_image(pdf_path, output_image_path):
    try:
        doc = fitz.open(pdf_path)
        page = doc.load_page(0)
        pix = page.get_pixmap(matrix=fitz.Matrix(0.3, 0.3))
        pix.save(output_image_path)
        return True
    except:
        return False

def save_to_supabase(file_name, file_id, cover_photo_id):
    try:
        supabase.table("cloud_books").upsert({
            "file_name": file_name,
            "file_id": file_id,
            "cover_base64": cover_photo_id  
        }, on_conflict="file_name").execute()
        return True
    except Exception as e:
        print("Error Supabase:", e)
        return False

@bot.channel_post_handler(content_types=['document'])
def handle_channel_docs(message):
    process_document(message)

@bot.message_handler(content_types=['document'])
def handle_group_docs(message):
    process_document(message)

def process_document(message):
    file_id = message.document.file_id
    file_name = message.document.file_name
    chat_id = message.chat.id
    
    if file_name.lower().endswith('.pdf'):
        msg = bot.reply_to(message, "⏳ កំពុងបង្កើត និងផ្ទុករូបក្របឡើង Telegram...")
        
        try:
            # ១. ទាញយក PDF មកកាត់យករូបក្រប
            file_info = bot.get_file(file_id)
            downloaded_file = bot.download_file(file_info.file_path)
            
            temp_pdf = f"temp_{message.message_id}.pdf"
            temp_img = f"temp_{message.message_id}.png"
            
            with open(temp_pdf, 'wb') as f:
                f.write(downloaded_file)
                
            if extract_cover_image(temp_pdf, temp_img):
                # ២. ផ្ញើរូបក្របនោះចូល Telegram Channel/Group វិញ ដើម្បីយក photo_id
                with open(temp_img, 'rb') as photo:
                    sent_photo_msg = bot.send_photo(chat_id, photo, caption=f"📚 ក្របសៀវភៅ: {file_name}")
                    cover_photo_id = sent_photo_msg.photo[-1].file_id # យក ID រូបភាពធំល្មម
                
                # ៣. យករูป ID ទៅ Save ក្នុង Supabase
                success = save_to_supabase(file_name, file_id, cover_photo_id)
                
                # ៤. លុបឯកសារបណ្តោះអាសន្នចោល
                if os.path.exists(temp_pdf): os.remove(temp_pdf)
                if os.path.exists(temp_img): os.remove(temp_img)
                
                if success:
                    bot.edit_message_text(f"✅ បានបញ្ចូលសៀវភៅ <b>{file_name}</b> ជោគជ័យ!", chat_id=chat_id, message_id=msg.message_id, parse_mode="HTML")
                else:
                    bot.edit_message_text("❌ រក្សាទុកក្នុង Supabase មិនបានសម្រេច។", chat_id=chat_id, message_id=msg.message_id)
            else:
                bot.edit_message_text("❌ មិនអាចកាត់យករូបក្របពី PDF នេះបានទេ។", chat_id=chat_id, message_id=msg.message_id)
        except Exception as e:
            bot.edit_message_text(f"❌ Error: {e}", chat_id=chat_id, message_id=msg.message_id)
    else:
        bot.reply_to(message, "⚠️ សូមផ្ញើតែឯកសារ .pdf ប៉ុណ្ណោះ។")

# =======================================================
# ផ្នែកខាងក្រោមនេះគឺជា Web Server សម្រាប់បញ្ឆោត Render កុំឱ្យបិទ Bot
# =======================================================
class DummyHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is running successfully!")

def keep_alive():
    port = int(os.environ.get('PORT', 8080))
    server = HTTPServer(('0.0.0.0', port), DummyHandler)
    server.serve_forever()

if __name__ == "__main__":
    print("🤖 Bot កំពុងដំណើរការ...")
    
    # ចាប់ផ្តើម Web Server នៅក្នុង Background
    threading.Thread(target=keep_alive).start()
    
    # ចាប់ផ្តើម Bot ឱ្យរង់ចាំទទួលឯកសារ
    bot.polling(none_stop=True)