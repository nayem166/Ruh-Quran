import requests
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, BotCommand, BotCommandScopeChat
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, ChatMemberHandler, CallbackQueryHandler, filters
from datetime import datetime, time, timedelta
import asyncio
import pytz

BANGLADESH_TIMEZONE = pytz.timezone('Asia/Dhaka')

# Set up logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Bot token and username
BOT_TOKEN = "7404345569:AAFGYtBMXfV_yOiMG8BGc-Z4lfzn4rvmkJM"
BOT_USERNAME = "Ruh_Quran_bot"
DEFAULT_QARI = "mishary"

# New global dictionary to store message IDs for deletion.
# Key: user_id, Value: list of dictionaries, each with command_message_id and surah_message_id
user_surah_messages = {}

# Command lists for private and group chats
private_commands = [
    BotCommand("start", "বট শুরু করুন এবং গ্রুপে যোগ করুন"),
    BotCommand("help", "সাহায্য পান এবং কমাণ্ড তালিকা দেখুন"),
    BotCommand("prayer", "নামাজের সময় দেখুন"),
    BotCommand("surah", "সূরার অডিও পান"),
    BotCommand("qari_list", "ক্বারীদের তালিকা দেখুন"),
    BotCommand("surah_list", "সূরার তালিকা দেখুন")
]

group_commands = [
    BotCommand("help", "সাহায্য পান এবং কমাণ্ড তালিকা দেখুন"),
    BotCommand("prayer", "নামাজের সময় দেখুন"),
    BotCommand("surah", "সূরার অডিও পান"),
    BotCommand("qari_list", "ক্বারীদের তালিকা দেখুন"),
    BotCommand("surah_list", "সূরার তালিকা দেখুন"),
    BotCommand("delete_surah", "আপনার দেওয়া সূরাটি এবং কমান্ড মেসেজটি মুছে দিন।"), # New command added
    BotCommand("salat_reminder_fajr", "ফজরের সালাতের জন্য স্মরণ করিয়ে দিন"),
    BotCommand("salat_reminder_dhuhr", "যোহরের সালাতের জন্য স্মরণ করিয়ে দিন"),
    BotCommand("salat_reminder_jumuah", "জুম'আর সালাতের জন্য স্মরণ করিয়ে দিন"),
    BotCommand("salat_reminder_asr", "আসরের সালাতের জন্য স্মরণ করিয়ে দিন"),
    BotCommand("salat_reminder_maghrib", "মাগরিবের সালাতের জন্য স্মরণ করিয়ে দিন"),
    BotCommand("salat_reminder_isha", "ইশার সালাতের জন্য স্মরণ করিয়ে দিন"),
    BotCommand("sehri_reminder", "সেহরির সময় স্মরণ করিয়ে দিন"),
    BotCommand("iftar_reminder", "ইফতারের সময় স্মরণ করিয়ে দিন")
]

# List of Surahs longer than 25 minutes
LONG_SURAHS = {2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 16, 17, 18, 20, 21, 22, 24, 26, 37, 39, 40}

# Reciter (Qari) data
QARI_DATA = {
    "mishary": {
        "name": "Mishary Rashid Al-Afasy",
        "name_bn": "মিশারী রাশিদ আল-আফাসী",
        "bio": "Mishary bin Rashid Alafasy is a Kuwaiti reciter, imam, and vocalist. He is one of the most popular reciters in the Islamic world.",
        "bio_bn": "তিনি একজন কুয়েতি ক্বারী, ইমাম এবং মুনশিদ। তিনি মুসলিম বিশ্বের অন্যতম জনপ্রিয় ক্বারী।",
        "short_name": "mishary",
        "fatiha_link": "https://download.quranicaudio.com/quran/mishaari_raashid_al_3afaasee/001.mp3",
        "base_url": "https://download.quranicaudio.com/quran/mishaari_raashid_al_3afaasee/"
    },
    "yasser": {
        "name": "Yasser bin Rashid Al-Dosari",
        "name_bn": "ইয়াসির বিন রাশিদ আল-দুসারি",
        "bio": "Yasser Al Dossari is a well-known Saudi reciter and imam of the Grand Mosque in Makkah.",
        "bio_bn": "তিনি একজন সুপরিচিত সৌদি ক্বারী এবং মক্কার গ্র্যান্ড মসজিদের ইমাম।",
        "short_name": "yasser",
        "fatiha_link": "https://podcasts.qurancentral.com/yasser-al-dossari/yasser-al-dossari-001.mp3",
        "base_url": "https://podcasts.qurancentral.com/yasser-al-dossari/yasser-al-dossari-"
    },
    "sudais": {
        "name": "Abdur-Rahman As-Sudais",
        "name_bn": "আব্দুর-রাহমান আস-সুদাইস",
        "bio": "Abdurrahman as Sudais is a famous reciter and the Chief Imam of the Grand Mosque in Makkah.",
        "bio_bn": "তিনি একজন বিখ্যাত ক্বারী এবং মক্কার গ্র্যান্ড মসজিদের প্রধান ইমাম।",
        "short_name": "sudais",
        "fatiha_link": "https://download.quranicaudio.com/quran/abdurrahmaan_as-sudays/001.mp3",
        "base_url": "https://download.quranicaudio.com/quran/abdurrahmaan_as-sudays/"
    },
    "abdulbasit": {
        "name": "Abdul Basit ‘Abd us-Samad",
        "name_bn": "আব্দুল বাসিত 'আব্দুস সামাদ",
        "bio": "Abdul Basit Abdul Samad was an Egyptian reciter, widely regarded as one of the best in the world.",
        "bio_bn": "তিনি একজন মিশরীয় ক্বারী ছিলেন, যাকে বিশ্বজুড়ে অন্যতম সেরা ক্বারী হিসেবে গণ্য করা হয়।",
        "short_name": "abdulbasit",
        "fatiha_link": "https://download.quranicaudio.com/quran/abdulbaset_mujawwad/001.mp3",
        "base_url": "https://download.quranicaudio.com/quran/abdulbaset_mujawwad/"
    }
}

# Surah data
def get_surah_link(qari_key, surah_id):
    if qari_key in QARI_DATA:
        if surah_id == 1:
            return QARI_DATA[qari_key]["fatiha_link"]
        return QARI_DATA[qari_key]["base_url"] + f"{surah_id:03d}.mp3"
    logger.error(f"Invalid qari_key: {qari_key}")
    return None

# All 114 Surah names
SURAH_NAMES = [
    "Al-Fatiha", "Al-Baqarah", "Aal-E-Imran", "An-Nisa", "Al-Ma'ida", "Al-An'am",
    "Al-A'raf", "Al-Anfal", "At-Tawba", "Yunus", "Hud", "Yusuf", "Ar-Ra'd",
    "Ibrahim", "Al-Hijr", "An-Nahl", "Al-Isra", "Al-Kahf", "Maryam", "Ta-Ha",
    "Al-Anbiya", "Al-Hajj", "Al-Mu'minun", "An-Nur", "Al-Furqan", "Ash-Shu'ara",
    "An-Naml", "Al-Qasas", "Al-Ankabut", "Ar-Rum", "Luqman", "As-Sajda", "Al-Ahzab",
    "Saba", "Fatir", "Ya-Sin", "As-Saffat", "Sad", "Az-Zumar", "Ghafir", "Fussilat",
    "Ash-Shura", "Az-Zukhruf", "Ad-Dukhan", "Al-Jathiya", "Al-Ahqaf", "Muhammad",
    "Al-Fath", "Al-Hujurat", "Qaf", "Adh-Dhariyat", "At-Tur", "An-Najm", "Al-Qamar",
    "Ar-Rahman", "Al-Waqi'a", "Al-Hadid", "Al-Mujadila", "Al-Hashr", "Al-Mumtahina",
    "As-Saff", "Al-Jumu'a", "Al-Munafiqun", "At-Taghabun", "At-Talaq", "At-Tahrim",
    "Al-Mulk", "Al-Qalam", "Al-Haqqah", "Al-Ma'arij", "Nuh", "Al-Jinn", "Al-Muzzammil",
    "Al-Muddaththir", "Al-Qiyama", "Al-Insan", "Al-Mursalat", "An-Naba", "An-Nazi'at",
    "Abasa", "At-Takwir", "Al-Infitar", "Al-Mutaffifin", "Al-Inshiqaq", "Al-Buruj",
    "At-Tariq", "Al-A'la", "Al-Ghashiya", "Al-Fajr", "Al-Balad", "Ash-Shams",
    "Al-Layl", "Ad-Duha", "Ash-Sharh", "At-Tin", "Al-Alaq", "Al-Qadr", "Al-Bayyina",
    "Az-Zalzala", "Al-Adiyat", "Al-Qari'a", "At-Takathur", "Al-Asr", "Al-Humaza",
    "Al-Fil", "Quraysh", "Al-Ma'un", "Al-Kawthar", "Al-Kafirun", "An-Nasr",
    "Al-Masad", "Al-Ikhlas", "Al-Falaq", "An-Nas"
]

# Surah mapping for flexible input handling
SURAH_MAPPING = {
    name.lower().replace(" ", "").replace("-", "").replace("'", ""): i + 1
    for i, name in enumerate(SURAH_NAMES)
}
SURAH_MAPPING.update({
    "fatiha": 1, "baqarah": 2, "imran": 3, "nisa": 4, "maida": 5, "anam": 6,
    "araf": 7, "anfal": 8, "tawba": 9, "yunus": 10, "hud": 11, "yusuf": 12,
    "rad": 13, "ibrahim": 14, "hijr": 15, "nahl": 16, "isra": 17, "kahf": 18,
    "maryam": 19, "taha": 20, "anbiya": 21, "hajj": 22, "muminun": 23, "nur": 24,
    "furqan": 25, "shuara": 26, "naml": 27, "qasas": 28, "ankabut": 29, "rum": 30,
    "luqman": 31, "sajda": 32, "ahzab": 33, "saba": 34, "fatir": 35, "yasin": 36,
    "saffat": 37, "sad": 38, "zumar": 39, "ghafir": 40, "fussilat": 41, "shura": 42,
    "zukhruf": 43, "dukhan": 44, "jathiya": 45, "ahqaf": 46, "muhammad": 47,
    "fath": 48, "hujurat": 49, "qaf": 50, "dhariyat": 51, "tur": 52, "najm": 53,
    "qamar": 54, "rahman": 55, "waqiah": 56, "hadid": 57, "mujadila": 58, "hashr": 59,
    "mumtahina": 60, "saff": 61, "jumua": 62, "munafiqun": 63, "taghabun": 64,
    "talaq": 65, "tahrim": 66, "mulk": 67, "qalam": 68, "haqqah": 69, "maarij": 70,
    "nuh": 71, "jinn": 72, "muzzammil": 73, "muddaththir": 74, "qiyama": 75,
    "insan": 76, "mursalat": 77, "naba": 78, "naziat": 79, "abasa": 80, "takwir": 81,
    "infitar": 82, "mutaffifin": 83, "inshiqaq": 84, "buruj": 85, "tariq": 86,
    "ala": 87, "ghashiya": 88, "fajr": 89, "balad": 90, "shams": 91, "layl": 92,
    "duha": 93, "sharh": 94, "tin": 95, "alaq": 96, "qadr": 97, "bayyina": 98,
    "zalzala": 99, "adiyat": 100, "qaria": 101, "takathur": 102, "asr": 103,
    "humaza": 104, "fil": 105, "quraysh": 106, "maun": 107, "kawthar": 108,
    "kafirun": 109, "nasr": 110, "masad": 111, "ikhlas": 112, "falaq": 113, "nas": 114,
    "yaseen": 36, "waqiah": 56,
})

# Add reciter short names to surah mapping
for qari in QARI_DATA.values():
    SURAH_MAPPING[qari["short_name"]] = None
    SURAH_MAPPING[qari["name"].lower().replace(" ", "").replace("-", "")] = None
    SURAH_MAPPING[qari["name"].lower().replace(" ", "_").replace("-", "_")] = None

# Fallback prayer times (Dhaka)
FALLBACK_PRAYER_TIMES = {
    "dhaka": {
        "ফজর": "4:26",
        "যোহর": "12:03",
        "আসর": "15:30",
        "মাগরিব": "18:34",
        "ইশা": "19:40",
        "সেহরি": "4:16",
        "ইফতার": "18:34"
    }
}
locations = {

# Update with all 64 districts
    # Provided districts (36, with corrections)
    "barguna": {
        "coords": {"lat": 22.1577, "lon": 90.1256},
        "sub_districts": {
            "barguna_sadar": {"lat": 22.1577, "lon": 90.1256},
            "amtali": {"lat": 22.1333, "lon": 90.2333},
            "bamna": {"lat": 22.0667, "lon": 90.1000},
            "betagi": {"lat": 22.4167, "lon": 90.1667},
            "patharghata": {"lat": 22.0167, "lon": 90.0667},
            "taltali": {"lat": 22.0000, "lon": 90.2000}
        }
    },
    "bhola": {
        "coords": {"lat": 22.6900, "lon": 90.6440},
        "sub_districts": {
            "bhola_sadar": {"lat": 22.6900, "lon": 90.6440},
            "burhanuddin": {"lat": 22.5000, "lon": 90.7167},
            "char_fasson": {"lat": 22.1833, "lon": 90.7500},
            "daulatkhan": {"lat": 22.6167, "lon": 90.7333},
            "lalmohan": {"lat": 22.3167, "lon": 90.7333},
            "manpura": {"lat": 22.1833, "lon": 90.9667},
            "tazumuddin": {"lat": 22.4167, "lon": 90.8333}
        }
    },
    "bandarban": {
        "coords": {"lat": 22.1953, "lon": 92.2195},
        "sub_districts": {
            "bandarban_sadar": {"lat": 22.1953, "lon": 92.2195},
            "alikhong": {"lat": 22.3167, "lon": 92.3000},
            "lama": {"lat": 21.7667, "lon": 92.2000},
            "naikhongchhari": {"lat": 21.4167, "lon": 92.1833},
            "rowangchhari": {"lat": 22.1667, "lon": 92.3333},
            "ruma": {"lat": 22.0500, "lon": 92.4167},
            "thanchi": {"lat": 21.7833, "lon": 92.4333}
        }
    },
    "brahmanbaria": {
        "coords": {"lat": 23.9575, "lon": 91.1117},
        "sub_districts": {
            "brahmanbaria_sadar": {"lat": 23.9575, "lon": 91.1117},
            "akhaura": {"lat": 24.0333, "lon": 91.2167},
            "ashuganj": {"lat": 24.0333, "lon": 91.0000},
            "bancharampur": {"lat": 23.7667, "lon": 90.8333},
            "bijoynagar": {"lat": 24.0000, "lon": 91.1167},
            "kasba": {"lat": 23.7333, "lon": 91.1667},
            "nabinagar": {"lat": 23.8833, "lon": 90.9667},
            "nasirnagar": {"lat": 24.2000, "lon": 91.1667},
            "saraill": {"lat": 24.1167, "lon": 91.1333}
        }
    },
    "coxs_bazar": {
        "coords": {"lat": 21.4397, "lon": 92.0096},
        "sub_districts": {
            "coxs_bazar_sadar": {"lat": 21.4397, "lon": 92.0096},
            "chakaria": {"lat": 21.7833, "lon": 92.0833},
            "kutubdia": {"lat": 21.8167, "lon": 91.8667},
            "maheshkhali": {"lat": 21.5167, "lon": 91.9667},
            "ramu": {"lat": 21.4333, "lon": 92.1000},
            "teknaf": {"lat": 20.8667, "lon": 92.3000},
            "ukhia": {"lat": 21.2167, "lon": 92.1667},
            "pekua": {"lat": 21.8333, "lon": 92.0667}
        }
    },
    "khagrachhari": {
        "coords": {"lat": 23.1079, "lon": 91.9701},
        "sub_districts": {
            "khagrachhari_sadar": {"lat": 23.1079, "lon": 91.9701},
            "dighinala": {"lat": 23.2500, "lon": 92.0667},
            "guimara": {"lat": 22.9833, "lon": 91.9333},
            "lakshmichhari": {"lat": 22.7833, "lon": 91.9000},
            "mahalchhari": {"lat": 22.9167, "lon": 92.0333},
            "manikchhari": {"lat": 22.8333, "lon": 91.8333},
            "matiranga": {"lat": 23.0333, "lon": 91.8667},
            "panchhari": {"lat": 23.2667, "lon": 91.9000},
            "ramgarh": {"lat": 22.9667, "lon": 91.6833}
        }
    },
    "rangamati": {
        "coords": {"lat": 22.6484, "lon": 92.1678},
        "sub_districts": {
            "rangamati_sadar": {"lat": 22.6484, "lon": 92.1678},
            "baghaichhari": {"lat": 23.1167, "lon": 92.1833},
            "barkal": {"lat": 22.7333, "lon": 92.3667},
            "belaichhari": {"lat": 22.4667, "lon": 92.3833},
            "juraichhari": {"lat": 22.6667, "lon": 92.3833},
            "kaptai": {"lat": 22.5000, "lon": 92.2167},
            "kawkhali": {"lat": 22.5667, "lon": 92.0167},
            "langadu": {"lat": 22.7167, "lon": 92.1500},
            "naniarchar": {"lat": 22.8667, "lon": 92.1167},
            "rajasthali": {"lat": 22.3833, "lon": 92.2333}
        }
    },
    "faridpur": {
        "coords": {"lat": 23.6061, "lon": 89.8406},
        "sub_districts": {
            "faridpur_sadar": {"lat": 23.6061, "lon": 89.8406},
            "alfadanga": {"lat": 23.3167, "lon": 89.7167},
            "bhanga": {"lat": 23.3833, "lon": 89.9833},
            "boalmari": {"lat": 23.3833, "lon": 89.6833},
            "charbhadrasan": {"lat": 23.6167, "lon": 90.0167},
            "madhukhali": {"lat": 23.5333, "lon": 89.5833},
            "nagarkanda": {"lat": 23.4167, "lon": 89.8833},
            "sadarpur": {"lat": 23.4667, "lon": 90.0333},
            "saltha": {"lat": 23.3167, "lon": 89.7833}
        }
    },
    "gazipur": {
        "coords": {"lat": 23.9989, "lon": 90.4203},
        "sub_districts": {
            "gazipur_sadar": {"lat": 23.9989, "lon": 90.4203},
            "kaliganj": {"lat": 23.9167, "lon": 90.5667},
            "kaliakair": {"lat": 24.0667, "lon": 90.2167},
            "kapasia": {"lat": 24.1000, "lon": 90.5667},
            "sreepur": {"lat": 24.2000, "lon": 90.4667}
        }
    },
    "gopalganj": {
        "coords": {"lat": 23.0051, "lon": 89.8266},
        "sub_districts": {
            "gopalganj_sadar": {"lat": 23.0051, "lon": 89.8266},
            "kashiani": {"lat": 23.2167, "lon": 89.6833},
            "kotalipara": {"lat": 22.9833, "lon": 89.9833},
            "muksudpur": {"lat": 23.3167, "lon": 89.8667},
            "tungipara": {"lat": 22.9000, "lon": 89.8833}
        }
    },
    "kishoreganj": {
        "coords": {"lat": 24.4394, "lon": 90.7829},
        "sub_districts": {
            "kishoreganj_sadar": {"lat": 24.4394, "lon": 90.7829},
            "austagram": {"lat": 24.2667, "lon": 91.1167},
            "bajitpur": {"lat": 24.2167, "lon": 90.9500},
            "bhairab": {"lat": 24.0500, "lon": 90.9833},
            "hossainpur": {"lat": 24.4167, "lon": 90.6500},
            "itna": {"lat": 24.5333, "lon": 91.0833},
            "karimganj": {"lat": 24.4667, "lon": 90.8833},
            "katiadi": {"lat": 24.2500, "lon": 90.7833},
            "kuliarchar": {"lat": 24.1500, "lon": 90.9000},
            "mithamain": {"lat": 24.4333, "lon": 91.0500},
            "nikli": {"lat": 24.3167, "lon": 90.7167},
            "pakundia": {"lat": 24.3167, "lon": 90.6833},
            "tarail": {"lat": 24.5333, "lon": 90.8833}
        }
    },
    "madaripur": {
        "coords": {"lat": 23.1710, "lon": 90.2094},
        "sub_districts": {
            "madaripur_sadar": {"lat": 23.1710, "lon": 90.2094},
            "kalkini": {"lat": 23.0667, "lon": 90.2333},
            "rajair": {"lat": 23.2000, "lon": 90.0667},
            "shibchar": {"lat": 23.3500, "lon": 90.1667}
        }
    },
    "manikganj": {
        "coords": {"lat": 23.8617, "lon": 90.0044},
        "sub_districts": {
            "manikganj_sadar": {"lat": 23.8617, "lon": 90.0044},
            "daulatpur": {"lat": 23.9333, "lon": 89.8333},
            "ghior": {"lat": 23.8667, "lon": 89.8333},
            "harirampur": {"lat": 23.7333, "lon": 90.0333},
            "saturia": {"lat": 23.9667, "lon": 90.0333},
            "shivalaya": {"lat": 23.8667, "lon": 89.9167},
            "singair": {"lat": 23.8167, "lon": 90.1500}
        }
    },
    "munshiganj": {
        "coords": {"lat": 23.5533, "lon": 90.5308},
        "sub_districts": {
            "munshiganj_sadar": {"lat": 23.5533, "lon": 90.5308},
            "gazaria": {"lat": 23.5333, "lon": 90.6167},
            "lohajang": {"lat": 23.4667, "lon": 90.3167},
            "serajdikhan": {"lat": 23.5333, "lon": 90.3833},
            "sreenagar": {"lat": 23.5333, "lon": 90.2833},
            "tongibari": {"lat": 23.5000, "lon": 90.4667}
        }
    },
    "narayanganj": {
        "coords": {"lat": 23.6238, "lon": 90.5000},
        "sub_districts": {
            "narayanganj_sadar": {"lat": 23.6238, "lon": 90.5000},
            "araihazar": {"lat": 23.7833, "lon": 90.6500},
            "bandar": {"lat": 23.6000, "lon": 90.5167},
            "rupganj": {"lat": 23.7333, "lon": 90.5167},
            "sonargaon": {"lat": 23.6500, "lon": 90.6167}
        }
    },
    "narsingdi": {
        "coords": {"lat": 23.9230, "lon": 90.7177},
        "sub_districts": {
            "narsingdi_sadar": {"lat": 23.9230, "lon": 90.7177},
            "belabo": {"lat": 24.0833, "lon": 90.8333},
            "monohardi": {"lat": 24.1167, "lon": 90.7000},
            "palash": {"lat": 23.9167, "lon": 90.6167},
            "raipura": {"lat": 24.0167, "lon": 90.8667},
            "shibpur": {"lat": 24.0333, "lon": 90.7333}
        }
    },
    "rajbari": {
        "coords": {"lat": 23.7574, "lon": 89.6440},
        "sub_districts": {
            "rajbari_sadar": {"lat": 23.7574, "lon": 89.6440},
            "baliakandi": {"lat": 23.6167, "lon": 89.5500},
            "goalandaghat": {"lat": 23.7333, "lon": 89.7667},
            "kalukhali": {"lat": 23.6833, "lon": 89.6667},
            "pangsha": {"lat": 23.7833, "lon": 89.4167}
        }
    },
    "shariatpur": {
        "coords": {"lat": 23.2137, "lon": 90.3471},
        "sub_districts": {
            "shariatpur_sadar": {"lat": 23.2137, "lon": 90.3471},
            "bhedarganj": {"lat": 23.2167, "lon": 90.4333},
            "damudya": {"lat": 23.1333, "lon": 90.4333},
            "gosairhat": {"lat": 23.0833, "lon": 90.4167},
            "naria": {"lat": 23.3167, "lon": 90.4000},
            "zajira": {"lat": 23.3667, "lon": 90.3167}
        }
    },
    "tangail": {
        "coords": {"lat": 24.2498, "lon": 89.9167},
        "sub_districts": {
            "tangail_sadar": {"lat": 24.2498, "lon": 89.9167},
            "basail": {"lat": 24.2167, "lon": 90.0667},
            "bhuapur": {"lat": 24.4667, "lon": 89.8667},
            "delduar": {"lat": 24.1333, "lon": 89.9667},
            "dhanbari": {"lat": 24.6167, "lon": 89.9667},
            "ghatail": {"lat": 24.4833, "lon": 90.0167},
            "gopalpur": {"lat": 24.5667, "lon": 89.9167},
            "kalihati": {"lat": 24.3833, "lon": 90.0167},
            "madhupur": {"lat": 24.6167, "lon": 90.0333},
            "mirzapur": {"lat": 24.1000, "lon": 90.1000},
            "nagarpur": {"lat": 24.0500, "lon": 89.8667},
            "sakhipur": {"lat": 24.3167, "lon": 90.1667}
        }
    },
    "chuadanga": {
        "coords": {"lat": 23.6410, "lon": 88.8514},
        "sub_districts": {
            "chuadanga_sadar": {"lat": 23.6410, "lon": 88.8514},
            "alamdanga": {"lat": 23.7500, "lon": 88.9333},
            "damurhuda": {"lat": 23.6167, "lon": 88.7667},
            "jibannagar": {"lat": 23.4167, "lon": 88.8167}
        }
    },
    "jhenaidah": {
        "coords": {"lat": 23.5417, "lon": 89.1772},
        "sub_districts": {
            "jhenaidah_sadar": {"lat": 23.5417, "lon": 89.1772},
            "harinakunda": {"lat": 23.6500, "lon": 89.0333},
            "kaliganj": {"lat": 23.4167, "lon": 89.1333},
            "kotchandpur": {"lat": 23.4000, "lon": 89.0167},
            "maheshpur": {"lat": 23.3500, "lon": 88.9833},
            "shailkupa": {"lat": 23.6833, "lon": 89.2500}
        }
    },
    "magura": {
        "coords": {"lat": 23.4871, "lon": 89.4197},
        "sub_districts": {
            "magura_sadar": {"lat": 23.4871, "lon": 89.4197},
            "mohammadpur": {"lat": 23.4000, "lon": 89.5667},
            "shalikha": {"lat": 23.3167, "lon": 89.3833},
            "sreepur": {"lat": 23.6000, "lon": 89.3833}
        }
    },
    "meherpur": {
        "coords": {"lat": 23.7710, "lon": 88.6317},
        "sub_districts": {
            "meherpur_sadar": {"lat": 23.7710, "lon": 88.6317},
            "gangni": {"lat": 23.8167, "lon": 88.6667},
            "mujibnagar": {"lat": 23.6500, "lon": 88.6000}
        }
    },
    "narail": {
        "coords": {"lat": 23.1720, "lon": 89.5124},
        "sub_districts": {
            "narail_sadar": {"lat": 23.1720, "lon": 89.5124},
            "kalia": {"lat": 23.0333, "lon": 89.6333},
            "lohapara": {"lat": 23.1833, "lon": 89.3667}
        }
    },
    "satkhira": {
        "coords": {"lat": 22.7082, "lon": 89.0751},
        "sub_districts": {
            "satkhira_sadar": {"lat": 22.7082, "lon": 89.0751},
            "assasuni": {"lat": 22.5500, "lon": 89.1667},
            "debhata": {"lat": 22.5667, "lon": 88.9667},
            "kalaroa": {"lat": 22.8667, "lon": 89.0333},
            "kaliganj": {"lat": 22.4500, "lon": 89.0333},
            "shyamnagar": {"lat": 22.3167, "lon": 89.1000},  # Corrected
            "tala": {"lat": 22.7500, "lon": 89.2500}
        }
    },
    "jamalpur": {
        "coords": {"lat": 24.9196, "lon": 89.9481},
        "sub_districts": {
            "jamalpur_sadar": {"lat": 24.9196, "lon": 89.9481},
            "baksiganj": {"lat": 25.2167, "lon": 89.8833},
            "dewanganj": {"lat": 25.1333, "lon": 89.7667},
            "isaranganj": {"lat": 25.1333, "lon": 89.8667},
            "madarganj": {"lat": 24.8833, "lon": 90.0000},
            "melandaha": {"lat": 24.9667, "lon": 89.8333},
            "sarishabari": {"lat": 24.7333, "lon": 89.8333}
        }
    },
    "chapainawabganj": {
        "coords": {"lat": 24.5903, "lon": 88.2712},
        "sub_districts": {
            "chapainawabganj_sadar": {"lat": 24.5903, "lon": 88.2712},
            "bholahat": {"lat": 24.8167, "lon": 88.1500},
            "gomastapur": {"lat": 24.7833, "lon": 88.2833},
            "nachole": {"lat": 24.7333, "lon": 88.3167},
            "shibganj": {"lat": 24.6833, "lon": 88.1667}
        }
    },
    "joypurhat": {
        "coords": {"lat": 25.1014, "lon": 89.0227},
        "sub_districts": {
            "joypurhat_sadar": {"lat": 25.1014, "lon": 89.0227},
            "akkelpur": {"lat": 24.9667, "lon": 89.0333},
            "kalai": {"lat": 25.0667, "lon": 89.1833},
            "khetlal": {"lat": 25.0333, "lon": 89.1333},
            "panchbibi": {"lat": 25.1833, "lon": 89.0167}
        }
    },
    "gaibandha": {
        "coords": {"lat": 25.3293, "lon": 89.5439},
        "sub_districts": {  # Corrected from "subseven"
            "gaibandha_sadar": {"lat": 25.3293, "lon": 89.5439},
            "fulchhari": {"lat": 25.2667, "lon": 89.6333},
            "gobindaganj": {"lat": 25.1333, "lon": 89.3833},
            "palashbari": {"lat": 25.2833, "lon": 89.3500},
            "sadullapur": {"lat": 25.3833, "lon": 89.4667},
            "saghata": {"lat": 25.1000, "lon": 89.5833},
            "sundarganj": {"lat": 25.5667, "lon": 89.5167}
        }
    },
    "kurigram": {
        "coords": {"lat": 25.8072, "lon": 89.6292},
        "sub_districts": {
            "kurigram_sadar": {"lat": 25.8072, "lon": 89.6292},
            "bhuranbari": {"lat": 25.9667, "lon": 89.6667},
            "char_rajibpur": {"lat": 25.4167, "lon": 89.7000},
            "chilmari": {"lat": 25.5667, "lon": 89.6833},
            "fulbari": {"lat": 25.9333, "lon": 89.4333},
            "nageshwari": {"lat": 25.9667, "lon": 89.7167},
            "rajarhat": {"lat": 25.8000, "lon": 89.5333},
            "raumari": {"lat": 25.5667, "lon": 89.8500},
            "ulipur": {"lat": 25.6667, "lon": 89.6167}
        }
    },
    "lalmonirhat": {
        "coords": {"lat": 25.9124, "lon": 89.4460},
        "sub_districts": {
            "lalmonirhat_sadar": {"lat": 25.9124, "lon": 89.4460},
            "aditmari": {"lat": 25.9167, "lon": 89.3500},
            "hatibandha": {"lat": 26.1167, "lon": 89.1333},
            "kaliganj": {"lat": 25.9667, "lon": 89.2167},
            "patgram": {"lat": 26.3500, "lon": 89.0167}
        }
    },
    "nilphamari": {
        "coords": {"lat": 25.9417, "lon": 88.8443},
        "sub_districts": {
            "nilphamari_sadar": {"lat": 25.9417, "lon": 88.8443},
            "dimla": {"lat": 26.1333, "lon": 88.9167},
            "domar": {"lat": 26.1000, "lon": 88.8333},
            "jaldhaka": {"lat": 26.0167, "lon": 89.0333},
            "kishoreganj": {"lat": 25.9167, "lon": 89.0167},
            "saidpur": {"lat": 25.7833, "lon": 88.9000}
        }
    },
    "panchagarh": {
        "coords": {"lat": 26.3350, "lon": 88.5577},
        "sub_districts": {
            "panchagarh_sadar": {"lat": 26.3350, "lon": 88.5577},
            "atwari": {"lat": 26.3167, "lon": 88.4667},
            "boda": {"lat": 26.2167, "lon": 88.5667},
            "debiganj": {"lat": 26.1167, "lon": 88.7667},
            "tetulia": {"lat": 26.4833, "lon": 88.4667}
        }
    },
    "thakurgaon": {
        "coords": {"lat": 26.0310, "lon": 88.4699},
        "sub_districts": {
            "thakurgaon_sadar": {"lat": 26.0310, "lon": 88.4699},
            "baliadangi": {"lat": 26.1000, "lon": 88.3333},
            "haripur": {"lat": 26.0333, "lon": 88.2333},
            "pirganj": {"lat": 25.8667, "lon": 88.3667},
            "ranisankail": {"lat": 25.8833, "lon": 88.2667}
        }
    },
    # Additional 28 districts
    "barishal": {
        "coords": {"lat": 22.7010, "lon": 90.3535},
        "sub_districts": {
            "barishal_sadar": {"lat": 22.7010, "lon": 90.3535},
            "agailjhara": {"lat": 22.9667, "lon": 90.1667},
            "babuganj": {"lat": 22.8333, "lon": 90.3333},
            "bakerganj": {"lat": 22.5500, "lon": 90.3333},
            "banaripara": {"lat": 22.7833, "lon": 90.1667},
            "gaurnadi": {"lat": 22.9667, "lon": 90.2333},
            "hizla": {"lat": 22.9167, "lon": 90.5000},
            "mehendiganj": {"lat": 22.6833, "lon": 90.5333},
            "muladi": {"lat": 22.9167, "lon": 90.4167},
            "wazirpur": {"lat": 22.8167, "lon": 90.2500}
        }
    },
    "patuakhali": {
        "coords": {"lat": 22.3596, "lon": 90.3181},
        "sub_districts": {
            "patuakhali_sadar": {"lat": 22.3596, "lon": 90.3181},
            "bauphal": {"lat": 22.4167, "lon": 90.4167},
            "dashmina": {"lat": 22.2833, "lon": 90.5667},
            "dumki": {"lat": 22.4333, "lon": 90.3833},
            "galachipa": {"lat": 22.1667, "lon": 90.4333},
            "kalapara": {"lat": 21.9833, "lon": 90.2333},
            "mirzaganj": {"lat": 22.3667, "lon": 90.2333},
            "rangabali": {"lat": 22.0833, "lon": 90.3333}
        }
    },
    "pirojpur": {
        "coords": {"lat": 22.5797, "lon": 89.9752},
        "sub_districts": {
            "pirojpur_sadar": {"lat": 22.5797, "lon": 89.9752},
            "bhandaria": {"lat": 22.4833, "lon": 90.0667},
            "kaukhali": {"lat": 22.6333, "lon": 90.0667},
            "mathbaria": {"lat": 22.2833, "lon": 89.9667},
            "nazirpur": {"lat": 22.7167, "lon": 90.0333},
            "nesarabad": {"lat": 22.7667, "lon": 90.1167},
            "zianagar": {"lat": 22.4333, "lon": 90.0000}
        }
    },
    "jhalokati": {
        "coords": {"lat": 22.6406, "lon": 90.1987},
        "sub_districts": {
            "jhalokati_sadar": {"lat": 22.6406, "lon": 90.1987},
            "kanthalia": {"lat": 22.6667, "lon": 90.1667},
            "nalchity": {"lat": 22.6167, "lon": 90.2667},
            "rajapur": {"lat": 22.5667, "lon": 90.1333}
        }
    },
    "chattogram": {
        "coords": {"lat": 22.3569, "lon": 91.7832},
        "sub_districts": {
            "chattogram_sadar": {"lat": 22.3569, "lon": 91.7832},
            "anwara": {"lat": 22.2167, "lon": 91.8667},
            "banshkhali": {"lat": 22.0333, "lon": 91.9333},
            "boalkhali": {"lat": 22.3667, "lon": 91.9167},
            "chandanaish": {"lat": 22.2167, "lon": 92.0167},
            "fatikchhari": {"lat": 22.6833, "lon": 91.7833},
            "hathazari": {"lat": 22.5000, "lon": 91.8167},
            "lohagara": {"lat": 22.1500, "lon": 92.0333},
            "mirsharai": {"lat": 22.7667, "lon": 91.5833},
            "patiya": {"lat": 22.3000, "lon": 91.9833},
            "rangunia": {"lat": 22.4667, "lon": 92.0833},
            "raozan": {"lat": 22.5333, "lon": 91.9333},
            "sandwip": {"lat": 22.4833, "lon": 91.4167},
            "satkania": {"lat": 22.0833, "lon": 92.0500},
            "sitakunda": {"lat": 22.5833, "lon": 91.6667}
        }
    },
    "cumilla": {
        "coords": {"lat": 23.4610, "lon": 91.1850},
        "sub_districts": {
            "cumilla_sadar": {"lat": 23.4610, "lon": 91.1850},
            "barura": {"lat": 23.3667, "lon": 91.0667},
            "brahmanpara": {"lat": 23.6167, "lon": 91.1167},
            "burichang": {"lat": 23.5500, "lon": 91.1333},
            "chandina": {"lat": 23.4833, "lon": 90.9833},
            "chauddagram": {"lat": 23.2167, "lon": 91.3167},
            "daudkandi": {"lat": 23.5333, "lon": 90.7167},
            "debidwar": {"lat": 23.6000, "lon": 90.9833},
            "homna": {"lat": 23.6833, "lon": 90.8000},
            "laksam": {"lat": 23.2500, "lon": 91.1333},
            "muradnagar": {"lat": 23.6833, "lon": 90.9333},
            "nangalkot": {"lat": 23.1667, "lon": 91.2000},
            "meghna": {"lat": 23.6167, "lon": 90.6833},
            "titas": {"lat": 23.5667, "lon": 90.8000},
            "monohorgonj": {"lat": 23.1667, "lon": 90.9833},
            "cumilla_sadar_dakshin": {"lat": 23.4167, "lon": 91.2167}
        }
    },
    "noakhali": {
        "coords": {"lat": 22.8340, "lon": 91.0973},
        "sub_districts": {
            "noakhali_sadar": {"lat": 22.8340, "lon": 91.0973},
            "begumganj": {"lat": 22.9333, "lon": 91.1000},
            "chatkhil": {"lat": 23.0333, "lon": 90.9667},
            "companiganj": {"lat": 22.8667, "lon": 91.2833},
            "hatiya": {"lat": 22.3667, "lon": 91.1333},
            "senbagh": {"lat": 22.9833, "lon": 91.2333},
            "sonaimuri": {"lat": 23.0333, "lon": 91.1167},
            "subarnachar": {"lat": 22.6833, "lon": 91.0833},
            "kabirhat": {"lat": 22.8833, "lon": 91.1667}
        }
    },
    "feni": {
        "coords": {"lat": 23.0159, "lon": 91.3976},
        "sub_districts": {
            "feni_sadar": {"lat": 23.0159, "lon": 91.3976},
            "chhagalnaiya": {"lat": 23.0333, "lon": 91.5167},
            "daganbhuiyan": {"lat": 22.9333, "lon": 91.3167},
            "fulgazi": {"lat": 23.1333, "lon": 91.4333},
            "parshuram": {"lat": 23.2167, "lon": 91.4167},
            "sonagazi": {"lat": 22.8500, "lon": 91.3833}
        }
    },
    "lakshmipur": {
        "coords": {"lat": 22.9443, "lon": 90.8282},
        "sub_districts": {
            "lakshmipur_sadar": {"lat": 22.9443, "lon": 90.8282},
            "raipur": {"lat": 23.0333, "lon": 90.7667},
            "ramganj": {"lat": 23.1000, "lon": 90.8667},
            "ramgati": {"lat": 22.6167, "lon": 90.6667},
            "kamalnagar": {"lat": 22.7333, "lon": 90.8833}
        }
    },
    "chandpur": {
        "coords": {"lat": 23.2500, "lon": 90.6500},
        "sub_districts": {
            "chandpur_sadar": {"lat": 23.2500, "lon": 90.6500},
            "faridganj": {"lat": 23.1333, "lon": 90.7333},
            "hajiganj": {"lat": 23.2500, "lon": 90.8500},
            "kachua": {"lat": 23.3167, "lon": 90.9000},
            "matlab_dakshin": {"lat": 23.1833, "lon": 90.7167},
            "matlab_uttar": {"lat": 23.3500, "lon": 90.7000},
            "shahrasti": {"lat": 23.2167, "lon": 90.9667}
        }
    },
    "dhaka": {
        "coords": {"lat": 23.8103, "lon": 90.4125},
        "sub_districts": {
            "dhamrai": {"lat": 23.9167, "lon": 90.2167},
            "dohar": {"lat": 23.5833, "lon": 90.1333},
            "keraniganj": {"lat": 23.6833, "lon": 90.3167},
            "nawabganj": {"lat": 23.6667, "lon": 90.1667},
            "savar": {"lat": 23.8333, "lon": 90.2500}
        }
    },
    "jashore": {
        "coords": {"lat": 23.1697, "lon": 89.2137},
        "sub_districts": {
            "jashore_sadar": {"lat": 23.1697, "lon": 89.2137},
            "abhaynagar": {"lat": 23.0167, "lon": 89.4333},
            "bagherpara": {"lat": 23.2167, "lon": 89.3500},
            "chaugachha": {"lat": 23.2667, "lon": 89.0833},
            "jhikargachha": {"lat": 23.1000, "lon": 89.1000},
            "keshabpur": {"lat": 22.9167, "lon": 89.2167},
            "manirampur": {"lat": 23.0167, "lon": 89.2333},
            "sharsha": {"lat": 23.0667, "lon": 88.8667}
        }
    },
    "khulna": {
        "coords": {"lat": 22.8456, "lon": 89.5403},
        "sub_districts": {
            "khulna_sadar": {"lat": 22.8456, "lon": 89.5403},
            "batiaghata": {"lat": 22.7167, "lon": 89.5167},
            "dacope": {"lat": 22.5667, "lon": 89.5167},
            "dumuria": {"lat": 22.8167, "lon": 89.4167},
            "dighalia": {"lat": 22.9000, "lon": 89.5333},
            "koyra": {"lat": 22.3500, "lon": 89.2833},
            "paikgachha": {"lat": 22.5833, "lon": 89.3333},
            "phultala": {"lat": 22.9833, "lon": 89.4167},
            "rupsha": {"lat": 22.8333, "lon": 89.6667},
            "terokhada": {"lat": 22.9333, "lon": 89.6667}
        }
    },
    "kushtia": {
        "coords": {"lat": 23.9013, "lon": 89.1201},
        "sub_districts": {
            "kushtia_sadar": {"lat": 23.9013, "lon": 89.1201},
            "bheramara": {"lat": 24.0333, "lon": 88.9833},
            "daulatpur": {"lat": 24.0167, "lon": 88.8333},
            "khoksa": {"lat": 23.7833, "lon": 89.2833},
            "kumarkhali": {"lat": 23.8667, "lon": 89.2333},
            "mirpur": {"lat": 24.1000, "lon": 89.0000}
        }
    },
    "bagerhat": {
        "coords": {"lat": 22.6576, "lon": 89.7895},
        "sub_districts": {
            "bagerhat_sadar": {"lat": 22.6576, "lon": 89.7895},
            "chitalmari": {"lat": 22.6833, "lon": 89.6667},
            "fakirhat": {"lat": 22.7833, "lon": 89.7167},
            "kachua": {"lat": 22.6500, "lon": 89.8833},
            "mollahat": {"lat": 22.9333, "lon": 89.7000},
            "mongla": {"lat": 22.4833, "lon": 89.6000},
            "morrelganj": {"lat": 22.4333, "lon": 89.8667},
            "rampal": {"lat": 22.5833, "lon": 89.6667},
            "sarankhola": {"lat": 22.3167, "lon": 89.8333}
        }
    },
    "mymensingh": {
        "coords": {"lat": 24.7471, "lon": 90.4203},
        "sub_districts": {
            "mymensingh_sadar": {"lat": 24.7471, "lon": 90.4203},
            "bhaluka": {"lat": 24.4167, "lon": 90.3833},
            "dhobaura": {"lat": 25.0833, "lon": 90.5167},
            "fulbaria": {"lat": 24.6333, "lon": 90.2667},
            "gaffargaon": {"lat": 24.4333, "lon": 90.5500},
            "gauripur": {"lat": 24.7667, "lon": 90.5833},
            "haluaghat": {"lat": 25.1333, "lon": 90.3500},
            "ishwarganj": {"lat": 24.6833, "lon": 90.6000},
            "muktangacha": {"lat": 24.7667, "lon": 90.2667},
            "nandail": {"lat": 24.5667, "lon": 90.6833},
            "phulpur": {"lat": 24.9500, "lon": 90.3500},
            "trishal": {"lat": 24.5833, "lon": 90.3833}
        }
    },
    "netrokona": {
        "coords": {"lat": 24.8702, "lon": 90.7290},
        "sub_districts": {
            "netrokona_sadar": {"lat": 24.8702, "lon": 90.7290},
            "atpara": {"lat": 24.8167, "lon": 90.8667},
            "barhatta": {"lat": 24.8833, "lon": 90.8833},
            "durgapur": {"lat": 25.1333, "lon": 90.6833},
            "kalmakanda": {"lat": 25.0833, "lon": 90.8833},
            "kendua": {"lat": 24.6500, "lon": 90.8333},
            "khaliajuri": {"lat": 24.7000, "lon": 90.9667},
            "madhupur": {"lat": 24.6833, "lon": 90.7333},
            "mohanganj": {"lat": 24.8667, "lon": 90.9667},
            "purbadhala": {"lat": 24.9333, "lon": 90.6000}
        }
    },
    "sherpur": {
        "coords": {"lat": 25.0204, "lon": 90.0151},
        "sub_districts": {
            "sherpur_sadar": {"lat": 25.0204, "lon": 90.0151},
            "jhenaigati": {"lat": 25.1833, "lon": 90.0667},
            "nakla": {"lat": 24.9833, "lon": 90.1833},
            "nalitabari": {"lat": 25.0833, "lon": 90.2000},
            "sreebardi": {"lat": 25.2667, "lon": 90.1667}
        }
    },
    "bogura": {
        "coords": {"lat": 24.8465, "lon": 89.3773},
        "sub_districts": {
            "bogura_sadar": {"lat": 24.8465, "lon": 89.3773},
            "adamdighi": {"lat": 24.8167, "lon": 89.0333},
            "dhunat": {"lat": 24.6833, "lon": 89.5333},
            "dhupchanchia": {"lat": 24.8667, "lon": 89.1667},
            "gabtali": {"lat": 24.8833, "lon": 89.4500},
            "kahaloo": {"lat": 24.8333, "lon": 89.2667},
            "nandigram": {"lat": 24.7167, "lon": 89.2500},
            "sariakandi": {"lat": 24.8833, "lon": 89.5667},
            "shajahanpur": {"lat": 24.7667, "lon": 89.4167},
            "sherpur": {"lat": 24.6667, "lon": 89.4167},
            "shibganj": {"lat": 24.9500, "lon": 89.3167},
            "sonatola": {"lat": 24.6667, "lon": 89.5333}
        }
    },
    "naogaon": {
        "coords": {"lat": 24.7936, "lon": 88.9318},
        "sub_districts": {
            "naogaon_sadar": {"lat": 24.7936, "lon": 88.9318},
            "atrai": {"lat": 24.6167, "lon": 88.9667},
            "badalgachhi": {"lat": 24.9667, "lon": 88.9167},
            "dhamoirhat": {"lat": 24.9167, "lon": 88.8333},
            "manda": {"lat": 24.7667, "lon": 88.6667},
            "mahisontosh": {"lat": 24.8333, "lon": 88.7167},
            "niamatpur": {"lat": 24.8333, "lon": 88.5667},
            "patnitala": {"lat": 24.9333, "lon": 88.7333},
            "porsha": {"lat": 25.0333, "lon": 88.4833},
            "raninagar": {"lat": 24.7333, "lon": 88.9667},
            "sapahar": {"lat": 25.0333, "lon": 88.5833}
        }
    },
    "natore": {
        "coords": {"lat": 24.4206, "lon": 89.0003},
        "sub_districts": {
            "natore_sadar": {"lat": 24.4206, "lon": 89.0003},
            "bagatipara": {"lat": 24.3167, "lon": 89.0333},
            "baraigram": {"lat": 24.3167, "lon": 88.9333},
            "gurudaspur": {"lat": 24.3833, "lon": 89.2500},
            "lalpur": {"lat": 24.1833, "lon": 88.9667},
            "singra": {"lat": 24.5000, "lon": 89.1333}
        }
    },
    "pabna": {
        "coords": {"lat": 24.0063, "lon": 89.2372},
        "sub_districts": {
            "pabna_sadar": {"lat": 24.0063, "lon": 89.2372},
            "atgharia": {"lat": 24.1167, "lon": 89.2167},
            "ber": {"lat": 24.0667, "lon": 89.6167},
            "bhangura": {"lat": 24.2167, "lon": 89.3833},
            "chatmohar": {"lat": 24.2167, "lon": 89.2833},
            "faridpur": {"lat": 24.1667, "lon": 89.4333},
            "ishwardi": {"lat": 24.1333, "lon": 89.0667},
            "santhia": {"lat": 24.0667, "lon": 89.5333},
            "sujanagar": {"lat": 23.9167, "lon": 89.4333}
        }
    },
    "rajshahi": {
        "coords": {"lat": 24.3745, "lon": 88.6042},
        "sub_districts": {
            "rajshahi_sadar": {"lat": 24.3745, "lon": 88.6042},
            "bagha": {"lat": 24.3167, "lon": 88.8333},
            "bagmara": {"lat": 24.5667, "lon": 88.8167},
            "charghat": {"lat": 24.2833, "lon": 88.7667},
            "durgapur": {"lat": 24.4667, "lon": 88.7667},
            "godagari": {"lat": 24.4667, "lon": 88.3333},
            "mohanpur": {"lat": 24.5667, "lon": 88.6500},
            "paba": {"lat": 24.4333, "lon": 88.6167},
            "puthia": {"lat": 24.3667, "lon": 88.8333},
            "tanore": {"lat": 24.5833, "lon": 88.5667}
        }
    },
    "sirajganj": {
        "coords": {"lat": 24.4539, "lon": 89.7007},
        "sub_districts": {
            "sirajganj_sadar": {"lat": 24.4539, "lon": 89.7007},
            "belkuchi": {"lat": 24.3167, "lon": 89.7000},
            "chauhali": {"lat": 24.1167, "lon": 89.6667},
            "kamarkhanda": {"lat": 24.3667, "lon": 89.7000},
            "kazipur": {"lat": 24.6333, "lon": 89.6500},
            "raiganj": {"lat": 24.4833, "lon": 89.5333},
            "shahjadpur": {"lat": 24.1667, "lon": 89.5833},
            "tarash": {"lat": 24.4333, "lon": 89.3667},
            "ullapara": {"lat": 24.3167, "lon": 89.5667}
        }
    },
    "dinajpur": {
        "coords": {"lat": 25.6279, "lon": 88.6378},
        "sub_districts": {
            "dinajpur_sadar": {"lat": 25.6279, "lon": 88.6378},
            "birampur": {"lat": 25.3833, "lon": 88.9833},
            "birganj": {"lat": 25.8833, "lon": 88.6500},
            "biral": {"lat": 25.6333, "lon": 88.5333},
            "bochaganj": {"lat": 25.8000, "lon": 88.4667},
            "chirirbandar": {"lat": 25.6667, "lon": 88.3167},
            "fulbari": {"lat": 25.5167, "lon": 88.9333},
            "ghoraghat": {"lat": 25.2500, "lon": 89.2167},
            "hakimpur": {"lat": 25.2833, "lon": 89.0167},
            "kaharole": {"lat": 25.7833, "lon": 88.6000},
            "khansama": {"lat": 25.9333, "lon": 88.7333},
            "nawabganj": {"lat": 25.4167, "lon": 88.3167},
            "parbatipur": {"lat": 25.6667, "lon": 88.9167}
        }
    },
    "rangpur": {
        "coords": {"lat": 25.7439, "lon": 89.2752},
        "sub_districts": {
            "rangpur_sadar": {"lat": 25.7439, "lon": 89.2752},
            "badarganj": {"lat": 25.6667, "lon": 89.0500},
            "gangachhara": {"lat": 25.8500, "lon": 89.2167},
            "kaunia": {"lat": 25.7667, "lon": 89.4167},
            "mithapukur": {"lat": 25.5667, "lon": 89.2833},
            "pirgachha": {"lat": 25.6667, "lon": 89.3833},
            "pirganj": {"lat": 25.4167, "lon": 89.3167},
            "taraganj": {"lat": 25.8167, "lon": 89.0167}
        }
    },
    "sylhet": {
        "coords": {"lat": 24.8949, "lon": 91.8687},
        "sub_districts": {
            "sylhet_sadar": {"lat": 24.8949, "lon": 91.8687},
            "balaganj": {"lat": 24.6667, "lon": 91.8333},
            "beanibazar": {"lat": 24.8167, "lon": 92.1667},
            "bishwanath": {"lat": 24.7833, "lon": 91.7333},
            "companiganj": {"lat": 25.0833, "lon": 91.7833},
            "fenchuganj": {"lat": 24.7167, "lon": 91.9167},
            "golapganj": {"lat": 24.8667, "lon": 92.0167},
            "gowainghat": {"lat": 25.1000, "lon": 91.7333},
            "jaintiapur": {"lat": 25.1333, "lon": 92.1167},
            "kanaighat": {"lat": 25.0167, "lon": 92.2500},
            "zakiganj": {"lat": 24.8833, "lon": 92.3667},
            "south_surma": {"lat": 24.8333, "lon": 91.8333}
        }
    },
    "habiganj": {
        "coords": {"lat": 24.3740, "lon": 91.4155},
        "sub_districts": {
            "habiganj_sadar": {"lat": 24.3740, "lon": 91.4155},
            "ajmiriganj": {"lat": 24.5500, "lon": 91.2500},
            "baniachong": {"lat": 24.5167, "lon": 91.3333},
            "bahubal": {"lat": 24.3167, "lon": 91.5167},
            "chunarughat": {"lat": 24.2167, "lon": 91.5167},
            "lakhai": {"lat": 24.3167, "lon": 91.2167},
            "madhabpur": {"lat": 24.1000, "lon": 91.3167},
            "nabiganj": {"lat": 24.5667, "lon": 91.5167}
        }
    },
    "moulvibazar": {
        "coords": {"lat": 24.4829, "lon": 91.7770},
        "sub_districts": {
            "moulvibazar_sadar": {"lat": 24.4829, "lon": 91.7770},
            "barlekha": {"lat": 24.7167, "lon": 92.2000},
            "juri": {"lat": 24.6000, "lon": 92.1167},
            "kamalganj": {"lat": 24.3333, "lon": 91.9333},
            "kulaura": {"lat": 24.5167, "lon": 92.0333},
            "rajnagar": {"lat": 24.5000, "lon": 91.8667},
            "sreemangal": {"lat": 24.3167, "lon": 91.7333}
        }
    },
    "sunamganj": {
        "coords": {"lat": 25.0658, "lon": 91.3960},
        "sub_districts": {
            "sunamganj_sadar": {"lat": 25.0658, "lon": 91.3960},
            "bishwambarpur": {"lat": 24.9167, "lon": 91.3167},
            "chhatak": {"lat": 25.0333, "lon": 91.6667},
            "dakshin_sunamganj": {"lat": 24.8833, "lon": 91.4167},
            "derai": {"lat": 24.7833, "lon": 91.3667},
            "dharampasha": {"lat": 24.9167, "lon": 91.0167},
            "dowarabazar": {"lat": 25.0833, "lon": 91.5667},
            "jagannathpur": {"lat": 24.7667, "lon": 91.5333},
            "jamalganj": {"lat": 24.9333, "lon": 91.2667},
            "sullah": {"lat": 24.7167, "lon": 91.3167},
            "tahsil": {"lat": 25.0167, "lon": 91.3167}
        }
    }
}
# Verify total districts
print(f"Total districts: {len(locations)}")  # Outputs: 64

# Check if it's Ramadan (March 1–30, 2025)
def is_ramadan():
    today = datetime.now(BANGLADESH_TIMEZONE)
    ramadan_start = BANGLADESH_TIMEZONE.localize(datetime(today.year, 3, 1))
    ramadan_end = BANGLADESH_TIMEZONE.localize(datetime(today.year, 3, 30))
    return ramadan_start <= today <= ramadan_end

# Convert 24-hour format to 12-hour AM/PM
def convert_to_12_hour(time_str):
    try:
        t = datetime.strptime(time_str, "%H:%M")
        return t.strftime("%I:%M %p").lstrip("0")
    except:
        return time_str

# Fetch prayer times from Aladhan API
def get_prayer_times(lat, lon):
    try:
        date = datetime.now(BANGLADESH_TIMEZONE).strftime("%d-%m-%Y")
        url = f"http://api.aladhan.com/v1/timings/{date}?latitude={lat}&longitude={lon}&method=4"
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        data = response.json()
        if data["code"] == 200 and "data" in data and "timings" in data["data"]:
            timings = data["data"]["timings"]
            return {
                "ফজর": timings.get("Fajr", "N/A"),
                "যোহর": timings.get("Dhuhr", "N/A"),
                "আসর": timings.get("Asr", "N/A"),
                "মাগরিব": timings.get("Maghrib", "N/A"),
                "ইশা": timings.get("Isha", "N/A"),
                "সেহরি": timings.get("Imsak", "N/A"),
                "ইফতার": timings.get("Maghrib", "N/A")
            }
        return None
    except Exception as e:
        logger.error(f"Error fetching prayer times: {e}")
        return None

# Format prayer times message
def format_prayer_times(location, times):
    message = f"🕌 {location} এর আজকের নামাজের সময়সূচি\n━━━━━━━━━━━━━━━━━━━━━━\n"
    message += f"🌅 ফজর     ⟶  {convert_to_12_hour(times['ফজর'])}\n"

    # Check if today is Friday to display Jummah time instead of Dhuhr
    today = datetime.now(BANGLADESH_TIMEZONE).weekday()
    if today == 4: # Friday
        message += f"☀️ জুম'আ    ⟶  {convert_to_12_hour(times['যোহর'])}\n"
    else:
        message += f"☀️ যোহর     ⟶  {convert_to_12_hour(times['যোহর'])}\n"

    message += f"🌤 আসর      ⟶  {convert_to_12_hour(times['আসর'])}\n"
    message += f"🌇 মাগরিব   ⟶  {convert_to_12_hour(times['মাগরিব'])}\n"
    message += f"🌌 ইশা      ⟶  {convert_to_12_hour(times['ইশা'])}\n"
    if is_ramadan():
        message += f"🌙 সেহরি    ⟶  {convert_to_12_hour(times['সেহরি'])}\n"
        message += f"🍽️ ইফতার   ⟶  {convert_to_12_hour(times['ইফতার'])}\n"
    message += "━━━━━━━━━━━━━━━━━━━━━━"
    return message

# Set bot commands for private or group chats
async def set_bot_commands(context: ContextTypes.DEFAULT_TYPE, chat_id: int, chat_type: str):
    try:
        if chat_type == "private":
            await context.bot.set_my_commands(commands=private_commands, scope=BotCommandScopeChat(chat_id=chat_id))
            logger.info(f"Set private commands for chat_id: {chat_id}")
        elif chat_type in ["group", "supergroup"]:
            commands = group_commands if is_ramadan() else [cmd for cmd in group_commands if cmd.command not in ["sehri_reminder", "iftar_reminder"]]
            await context.bot.set_my_commands(commands=commands, scope=BotCommandScopeChat(chat_id=chat_id))
            logger.info(f"Set group commands for chat_id: {chat_id}")
    except Exception as e:
        logger.error(f"Error setting bot commands for chat_id {chat_id}: {e}")

# Help command
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await set_bot_commands(context, update.effective_chat.id, update.effective_chat.type)
    message = (
        "📖 আমার উপলব্ধ কমান্ডগুলো:\n\n"
        "**প্রাইভেট এবং গ্রুপ উভয় ক্ষেত্রেই কাজ করবে:**\n"
        "• /start - বট শুরু করুন এবং গ্রুপে যোগ করুন।\n"
        "• /help - সাহায্য পান এবং কমাণ্ড তালিকা দেখুন।\n"
        "• /prayer - নামাজের সময় দেখুন (যেমন: /prayer Dhaka বা /prayer Dhaka Savar)।\n"
        "• /surah - সূরার অডিও পান (উদাহরণ: /surah Al-Fatiha বা /surah 1)। সরাসরি যেকোনো সূরা পেতে ক্বারীর নাম যোগ করুন (যেমন: /surah Al-Fatiha Mishary).\n"
        "• /qari\\_list - ক্বারীদের তালিকা দেখুন।\n"
        "• /surah\\_list - সূরার তালিকা দেখুন।\n"
        "**শুধুমাত্র গ্রুপে কাজ করবে:**\n" # New help section
        "• /delete\\_surah - আপনার দেওয়া সূরাটি এবং কমান্ড মেসেজটি মুছে দিন।\n"
        "• /salat\\_reminder\\_fajr - ফজরের সালাতের জন্য স্মরণ করিয়ে দিন।\n"
        "• /salat\\_reminder\\_dhuhr - যোহরের সালাতের জন্য স্মরণ করিয়ে দিন।\n"
        "• /salat\\_reminder\\_jumuah - জুম'আর সালাতের জন্য স্মরণ করিয়ে দিন।\n"
        "• /salat\\_reminder\\_asr - আসরের সালাতের জন্য স্মরণ করিয়ে দিন।\n"
        "• /salat\\_reminder\\_maghrib - মাগরিবের সালাতের জন্য স্মরণ করিয়ে দিন।\n"
        "• /salat\\_reminder\\_isha - ইশার সালাতের জন্য স্মরণ করিয়ে দিন।\n"
    )
    if is_ramadan():
            message += "• /sehri_reminder - সেহরির সময় স্মরণ করিয়ে দিন।\n"
            message += "• /iftar_reminder - ইফতারের সময় স্মরণ করিয়ে দিন।\n"

    await update.message.reply_text(message, parse_mode='Markdown')

# /start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        chat_type = update.effective_chat.type
        chat_id = update.effective_chat.id
        logger.info(f"/start command received in chat type: {chat_type}")

        await set_bot_commands(context, chat_id, chat_type)

        if chat_type != "private":
            await update.message.reply_text("⚠️ এই কমান্ডটি শুধুমাত্র প্রাইভেট চ্যাটে কাজ করে")
            return

        message = (
            "আসসালামু আলাইকুম! আমি একটি ইসলামিক বট। আমাকে আপনার গ্রুপে যোগ করলে ইনশাআল্লাহ নির্দিষ্ট এলাকার নামাজের সময় জানাতে এবং কুরআন তেলাওয়াত শুনাতে সাহায্য করব। এছাড়া আপনি যদি আপনার গ্রুপ সদস্যদের চোখের হেফাজত নিশ্চিত করতে চান তাহলে অবশ্যই @Ruh\\_Eye\\_bot বটটি আপনার গ্রুপে যোগ করুন।\n\n"
            "নিচে আমার উপলব্ধ কমান্ডগুলো দেওয়া হলো:\n"
            "• /start - বট শুরু করুন এবং গ্রুপে যোগ করুন।\n"
            "• /help - সাহায্য পান এবং কমাণ্ড তালিকা দেখুন।\n"
            "• /prayer - নামাজের সময় দেখুন (যেমন: /prayer Dhaka বা /prayer Dhaka Savar)।\n"
            "• /surah - সূরার অডিও পান (উদাহরণ: /surah Al-Fatiha বা /surah 1)। সরাসরি যেকোনো সূরা পেতে ক্বারীর নাম যোগ করুন (যেমন: /surah Al-Fatiha Mishary).\n"
            "• /qari\\_list - ক্বারীদের তালিকা দেখুন।\n"
            "• /surah\\_list - সূরার তালিকা দেখুন।\n"
        )
        keyboard = [[InlineKeyboardButton("গ্রুপে যোগ দিন", url=f"https://t.me/{BOT_USERNAME}?startgroup=true")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(message, reply_markup=reply_markup, parse_mode='Markdown')
    except Exception as e:
        logger.error(f"Error in /start command: {e}")
        await update.message.reply_text("একটি ত্রুটি ঘটেছে। অনুগ্রহ করে আবার চেষ্টা করুন।")

# /prayer command
async def prayer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        await set_bot_commands(context, update.effective_chat.id, update.effective_chat.type)
        args = [arg.lower() for arg in context.args]
        if not args:
            await update.message.reply_text("অনুগ্রহ করে জেলার নাম দিন। যেমন: ⚠️ /prayer Dhaka বা /prayer Dhaka Savar")
            return

        district = args[0]
        sub_district = args[1] if len(args) > 1 else None

        if district not in locations:
            await update.message.reply_text("⚠️ এমন কোনো জেলা নেই।")
            return

        location_data = locations[district]
        location_name = district.capitalize()
        lat = location_data["coords"]["lat"]
        lon = location_data["coords"]["lon"]

        if sub_district:
            if sub_district not in location_data["sub_districts"]:
                sub_districts = ", ".join(location_data["sub_districts"].keys()).title()
                await update.message.reply_text(
                    f"⚠️ এই জেলায় এমন কোনো উপজেলা নেই।\n{location_name} জেলার উপজেলা: {sub_districts}"
                )
                return
            lat = location_data["sub_districts"][sub_district]["lat"]
            lon = location_data["sub_districts"][sub_district]["lon"]
            location_name = f"{location_name} {sub_district.capitalize()}"

        prayer_times = get_prayer_times(lat, lon)
        if not prayer_times:
            prayer_times = FALLBACK_PRAYER_TIMES.get(district, FALLBACK_PRAYER_TIMES["dhaka"])
            location_name += " (ফলব্যাক)"

        await update.message.reply_text(format_prayer_times(location_name, prayer_times))
    except Exception as e:
        logger.error(f"Error in /prayer command: {e}")
        await update.message.reply_text("একটি ত্রুটি ঘটেছে। অনুগ্রহ করে আবার চেষ্টা করুন।")

# Function to show short qari list if invalid qari
async def show_short_qari_list(update: Update, surah_id, surah_name):
    message = f"📖 সূরা: {surah_name}\nকোন ক্বারীর তেলাওয়াত শুনতে চান? সঠিক ক্বারী নির্বাচন করুন (যেমন: mishary, yasser, sudais, abdulbasit):"
    keyboard = [
        [InlineKeyboardButton(f"🎙️ {qari_data['short_name']}", callback_data=f"surah_{surah_id}_{key}")]
        for key, qari_data in QARI_DATA.items()
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    sent_message = await update.message.reply_text(message, reply_markup=reply_markup)
    return sent_message.message_id

# /surah command
async def surah(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        await set_bot_commands(context, update.effective_chat.id, update.effective_chat.type)
        user_id = update.effective_user.id
        chat_id = update.effective_chat.id

        # New code: Get the command message ID
        command_message_id = update.message.message_id

        if not context.args:
            await update.message.reply_text(
                "অনুগ্রহ করে সূরার নাম বা নম্বর দিন। যেমন: /surah Al-Fatiha, /surah 1 উদাহরণ: /surah Al-Fatiha বা /surah 1)। ক্বারী নির্বাচন করতে ক্বারীর নাম যোগ করুন (যেমন: /surah Al-Fatiha Mishary)."
            )
            return

        input_parts = [arg.lower() for arg in context.args]
        qari_key = None
        surah_input = ""

        # Check if the last argument is a valid qari
        if input_parts[-1] in QARI_DATA:
            qari_key = input_parts[-1]
            surah_input = "".join(input_parts[:-1])
        else:
            surah_input = "".join(input_parts)

        # Check for invalid qari name if multiple arguments were provided
        if len(input_parts) > 1 and qari_key is None:
            await update.message.reply_text("⚠️ ক্বারীর নাম এভাবে দিন (যেমন: mishary, yasser, sudais, abdulbasit)")
            # Auto-delete the command message
            try:
                if chat_id < 0:
                    await context.bot.delete_message(chat_id=chat_id, message_id=command_message_id)
            except Exception as e:
                logger.warning(f"Failed to auto-delete command message: {e}")
            return

        # Old qari finding logic (for multi-part names)
        if qari_key is None:
            for part in input_parts:
                found_qari = False
                for key, qari_data in QARI_DATA.items():
                    if part in (qari_data["short_name"], qari_data["name"].lower().replace(" ", "").replace("-", "")):
                        qari_key = key
                        surah_input = "".join([p for p in input_parts if p != part])
                        found_qari = True
                        break
                if found_qari:
                    break

        surah_id = None
        if surah_input.isdigit():
            num = int(surah_input)
            if 1 <= num <= 114:
                surah_id = num
        else:
            surah_id = SURAH_MAPPING.get(surah_input)

        if not surah_id:
            await update.message.reply_text(
                "এমন কোনো সূরা নেই। সঠিক নাম বা নম্বর দিন। যেমন: /surah Rahman বা /surah 55। /surah_list দিয়ে তালিকা দেখুন।"
            )
            # Auto-delete the command message
            try:
                if chat_id < 0:
                    await context.bot.delete_message(chat_id=chat_id, message_id=command_message_id)
            except Exception as e:
                logger.warning(f"Failed to auto-delete command message: {e}")
            return

        surah_name = SURAH_NAMES[surah_id - 1]

        if not qari_key:
            message = f"📖 সূরা: {surah_name}\nকোন ক্বারীর তেলাওয়াত শুনতে চান? নিচে থেকে নির্বাচন করুন:"
            keyboard = [
                [InlineKeyboardButton(f"🎙️ {qari_data['name']}", callback_data=f"surah_{surah_id}_{key}")]
                for key, qari_data in QARI_DATA.items()
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            sent_message = await update.message.reply_text(message, reply_markup=reply_markup)
            context.user_data["surah_selection_message_id"] = sent_message.message_id
            # Store the original command message ID in user_data
            context.user_data["original_command_message_id"] = command_message_id
            return

        # If both surah and valid qari provided
        surah_url = get_surah_link(qari_key, surah_id)
        if not surah_url:
            await update.message.reply_text(f"{QARI_DATA[qari_key]['name_bn']} ক্বারীর তেলাওয়াতে এই সূরার অডিও এখনো যোগ করা হয়নি।")
            return

        if surah_id in LONG_SURAHS:
            qari_name = QARI_DATA[qari_key]["name"]
            message_text = (
                f"✦━━━┈┈┈┈┈┈━━━✦\n"
                f"{surah_id}. 📖 Surah {surah_name}\n"
                f"✦━━━┈┈┈┈┈┈━━━✦\n"
                f"🎙️ {qari_name}\n\n"
                f"ফাইলটি বড় হওয়ায় সরাসরি শেয়ার করা যাচ্ছে না। নিচে ক্লিক করে শুনুন।"
            )
            keyboard = [[InlineKeyboardButton("এখানে ক্লিক করে শুনুন", url=surah_url)]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            sent_message = await update.message.reply_text(message_text, reply_markup=reply_markup)
        else:
            caption_text = (
                f"✦━━━┈┈┈┈┈┈━━━✦\n"
                f"{surah_id}. 📖 Surah {surah_name}\n"
                f"✦━━━┈┈┈┈┈┈━━━✦"
            )
            sent_message = await update.message.reply_document(
                document=surah_url,
                caption=caption_text,
                filename=f"{surah_id:03d}_{surah_name}.mp3"
            )

        # Store the sent message ID for deletion if in group
        if chat_id < 0:
            if user_id not in user_surah_messages:
                user_surah_messages[user_id] = []
            user_surah_messages[user_id].append({"command_id": command_message_id, "surah_id": sent_message.message_id})

            # New Code: Auto-delete the command message
            try:
                await context.bot.delete_message(chat_id=chat_id, message_id=command_message_id)
            except Exception as e:
                logger.warning(f"Failed to auto-delete command message {command_message_id}: {e}")

    except Exception as e:
        logger.error(f"Error in /surah command: {e}")
        await update.message.reply_text("একটি ত্রুটি ঘটেছে। অনুগ্রহ করে আবার চেষ্টা করুন।")

# New command handler for deleting surah messages
async def delete_surah_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    delete_command_id = update.message.message_id
    reply_to_message = update.message.reply_to_message

    if chat_id >= 0:  # Private chat
        await update.message.reply_text("⚠️ এই কমান্ডটি শুধুমাত্র গ্রুপে কাজ করে।")
        return

    if user_id not in user_surah_messages or not user_surah_messages[user_id]:
        try:
            await context.bot.delete_message(chat_id=chat_id, message_id=delete_command_id)
        except Exception as e:
            logger.warning(f"Failed to delete /delete_surah command message: {e}")
        await update.effective_chat.send_message("মুছে ফেলার জন্য কোনো সূরা খুঁজে পাওয়া যায়নি।")
        return

    deleted = False

    if reply_to_message:
        # Delete specific replied surah and its command
        target_surah_id = reply_to_message.message_id
        for idx, msg_data in enumerate(user_surah_messages[user_id]):
            if msg_data.get("surah_id") == target_surah_id:
                # Delete command message if exists
                if msg_data.get("command_id"):
                    try:
                        await context.bot.delete_message(chat_id=chat_id, message_id=msg_data["command_id"])
                    except Exception as e:
                        logger.warning(f"Failed to delete command message {msg_data['command_id']}: {e}")
                # Delete surah message
                try:
                    await context.bot.delete_message(chat_id=chat_id, message_id=target_surah_id)
                    deleted = True
                except Exception as e:
                    logger.warning(f"Failed to delete specific surah message {target_surah_id}: {e}")
                # Remove from list
                del user_surah_messages[user_id][idx]
                break
    else:
        # Delete all surah messages for the user
        for msg_data in user_surah_messages[user_id][:]:
            command_id = msg_data.get("command_id")
            surah_id = msg_data.get("surah_id")
            if command_id:
                try:
                    await context.bot.delete_message(chat_id=chat_id, message_id=command_id)
                except Exception as e:
                    logger.warning(f"Failed to delete command message {command_id}: {e}")
            if surah_id:
                try:
                    await context.bot.delete_message(chat_id=chat_id, message_id=surah_id)
                    deleted = True
                except Exception as e:
                    logger.warning(f"Failed to delete surah message {surah_id}: {e}")
        user_surah_messages[user_id] = []

    # Delete the /delete_surah command message
    try:
        await context.bot.delete_message(chat_id=chat_id, message_id=delete_command_id)
    except Exception as e:
        logger.warning(f"Failed to delete /delete_surah command message: {e}")

    if not deleted:
        await update.effective_chat.send_message("মুছে ফেলতে ব্যর্থ হয়েছে। সম্ভবত বটের যথেষ্ট অনুমতি নেই বা সূরা খুঁজে পাওয়া যায়নি।")

# /qari_list command
async def qari_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        await set_bot_commands(context, update.effective_chat.id, update.effective_chat.type)

        # New code: Get the command message ID if a message was sent (not a callback)
        command_message_id = None
        if update.message:
            command_message_id = update.message.message_id

        message = "🎙️ ক্বারীদের তালিকা:\n\n"
        keyboard = []

        for key, qari in QARI_DATA.items():
            message += f"• **{qari['name_bn']}**\n"
            message += f"  {qari['bio_bn']}\n\n"
            keyboard.append([InlineKeyboardButton(f"🎙️ {qari['name']}", callback_data=f"qari_{key}_page_1")])

        reply_markup = InlineKeyboardMarkup(keyboard)
        if update.callback_query:
            sent_message = await update.callback_query.edit_message_text(message, reply_markup=reply_markup, parse_mode='Markdown')
            context.user_data["qari_list_message_id"] = sent_message.message_id
        else:
            sent_message = await update.message.reply_text(message, reply_markup=reply_markup, parse_mode='Markdown')
            context.user_data["qari_list_message_id"] = sent_message.message_id

            # New Code: Auto-delete the command message if it's a group chat
            if update.effective_chat.type in ["group", "supergroup"] and command_message_id:
                try:
                    await context.bot.delete_message(chat_id=update.effective_chat.id, message_id=command_message_id)
                except Exception as e:
                    logger.warning(f"Failed to auto-delete qari_list command message {command_message_id}: {e}")
    except Exception as e:
        logger.error(f"Error in /qari_list command: {e}")
        await update.message.reply_text("একটি ত্রুটি ঘটেছে। অনুগ্রহ করে আবার চেষ্টা করুন।")

# /surah_list command
async def surah_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        await set_bot_commands(context, update.effective_chat.id, update.effective_chat.type)
        query = update.callback_query

        # New code: Get the command message ID if a message was sent (not a callback)
        command_message_id = None
        if update.message:
            command_message_id = update.message.message_id

        if query:
            data = query.data.split('_')
            qari_key = data[1]
            page = int(data[3])
        else:
            qari_key = context.user_data.get("selected_qari", DEFAULT_QARI)
            page = int(context.args[0]) if context.args and context.args[0].isdigit() else 1

        context.user_data["selected_qari"] = qari_key
        qari_name = QARI_DATA[qari_key]["name"]

        surahs_per_page = 20
        total_pages = (len(SURAH_NAMES) + surahs_per_page - 1) // surahs_per_page
        page = max(1, min(page, total_pages))

        start_idx = (page - 1) * surahs_per_page
        end_idx = min(start_idx + surahs_per_page, len(SURAH_NAMES))

        message = f"📜 সূরার লিস্ট\nক্বারীর নাম:**{qari['name_bn']}**| Page: {page}/{total_pages}\n\n"
        keyboard = []
        current_row = []

        for i in range(start_idx, end_idx):
            surah_number = i + 1
            surah_name = SURAH_NAMES[i]
            button_text = f"{surah_number}. {surah_name}"
            button_data = f"surah_{surah_number}_{qari_key}"
            current_row.append(InlineKeyboardButton(button_text, callback_data=button_data))
            if len(current_row) == 2:
                keyboard.append(current_row)
                current_row = []

        if current_row:
            keyboard.append(current_row)

        nav_buttons = []
        if page > 1:
            nav_buttons.append(InlineKeyboardButton("⬅️ পূর্ববর্তী", callback_data=f"list_{qari_key}_page_{page-1}"))
        if page < total_pages:
            nav_buttons.append(InlineKeyboardButton("পরবর্তী ➡️", callback_data=f"list_{qari_key}_page_{page+1}"))
        if nav_buttons:
            keyboard.append(nav_buttons)

        keyboard.append([InlineKeyboardButton("🔙 ক্বারী লিস্টে ফিরুন", callback_data="back_to_qari_list")])
        reply_markup = InlineKeyboardMarkup(keyboard)

        if query:
            sent_message = await query.message.edit_text(message, reply_markup=reply_markup)
            context.user_data["surah_list_message_id"] = sent_message.message_id
        else:
            sent_message = await update.message.reply_text(message, reply_markup=reply_markup)
            context.user_data["surah_list_message_id"] = sent_message.message_id

            # New Code: Auto-delete the command message if it's a group chat
            if update.effective_chat.type in ["group", "supergroup"] and command_message_id:
                try:
                    await context.bot.delete_message(chat_id=update.effective_chat.id, message_id=command_message_id)
                except Exception as e:
                    logger.warning(f"Failed to auto-delete surah_list command message {command_message_id}: {e}")

    except Exception as e:
        logger.error(f"Error in /surah_list command: {e}")
        await update.message.reply_text("একটি ত্রুটি ঘটেছে। অনুগ্রহ করে আবার চেষ্টা করুন।")

# Button callback handler
async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        query = update.callback_query
        await query.answer()
        data = query.data
        chat_id = query.message.chat_id
        message_id = query.message.message_id
        user_id = query.from_user.id

        await set_bot_commands(context, chat_id, query.message.chat.type)

        if data.startswith("qari_"):
            qari_key = data.split('_')[1]
            context.user_data["selected_qari"] = qari_key
            context.args = ["1"]
            await surah_list(update, context)
        elif data.startswith("list_"):
            parts = data.split('_')
            qari_key = parts[1]
            page = int(parts[3])
            context.args = [str(page)]
            context.user_data["selected_qari"] = qari_key
            await surah_list(update, context)
        elif data.startswith("surah_"):
            parts = data.split('_')
            surah_id = int(parts[1])
            qari_key = parts[2]
            surah_name = SURAH_NAMES[surah_id - 1]
            surah_url = get_surah_link(qari_key, surah_id)

            if not surah_url:
                await query.message.reply_text(f"{QARI_DATA[qari_key]['name_bn']} ক্বারীর তেলাওয়াতে এই সূরার অডিও এখনো যোগ করা হয়নি।")
                return

            await asyncio.sleep(1)

            try:
                if surah_id in LONG_SURAHS:
                    qari_name = QARI_DATA[qari_key]["name"]
                    message_text = (
                        f"✦━━━┈┈┈┈┈┈━━━✦\n"
                        f"{surah_id}. 📖 Surah {surah_name}\n"
                        f"✦━━━┈┈┈┈┈┈━━━✦\n"
                        f"🎙️ {qari_name}\n\n"
                        f"ফাইলটি বড় হওয়ায় সরাসরি শেয়ার করা যাচ্ছে না। নিচে ক্লিক করে শুনুন।"
                    )
                    keyboard = [[InlineKeyboardButton("এখানে ক্লিক করে শুনুন", url=surah_url)]]
                    reply_markup = InlineKeyboardMarkup(keyboard)
                    sent_message = await query.message.reply_text(message_text, reply_markup=reply_markup)
                else:
                    caption_text = (
                        f"✦━━━┈┈┈┈┈┈━━━✦\n"
                        f"{surah_id}. 📖 Surah {surah_name}\n"
                        f"✦━━━┈┈┈┈┈┈━━━✦"
                    )
                    sent_message = await query.message.reply_document(
                        document=surah_url,
                        caption=caption_text,
                        filename=f"{surah_id:03d}_{surah_name}.mp3"
                    )

                # Check for the original command ID in user_data and delete it
                original_command_id = context.user_data.get("original_command_message_id")
                if original_command_id:
                    try:
                        await context.bot.delete_message(chat_id=chat_id, message_id=original_command_id)
                        del context.user_data["original_command_message_id"]
                    except Exception as e:
                        logger.warning(f"Could not delete original command message {original_command_id}: {e}")

                # Store the sent message ID for deletion, if it's a group chat
                if chat_id < 0:
                    if user_id not in user_surah_messages:
                        user_surah_messages[user_id] = []
                    # Use a unique identifier to link command and surah messages.
                    user_surah_messages[user_id].append({"command_id": original_command_id, "surah_id": sent_message.message_id})

            except Exception as e:
                logger.error(f"Error sending Surah {surah_name} by {qari_key}: {e}")
                await query.message.reply_text("সূরা পাঠাতে ত্রুটি হয়েছে। দয়া করে আবার চেষ্টা করুন।")
                return

            for key in ["surah_selection_message_id", "surah_list_message_id", "qari_list_message_id"]:
                if key in context.user_data:
                    try:
                        await context.bot.delete_message(chat_id=chat_id, message_id=context.user_data[key])
                        del context.user_data[key]
                    except Exception as e:
                        logger.warning(f"Could not delete message {context.user_data[key]}: {e}")

            # The inline keyboard message is the one that triggered the callback, so we delete it.
            try:
                await context.bot.delete_message(chat_id=chat_id, message_id=message_id)
            except Exception as e:
                logger.warning(f"Could not delete message {message_id}: {e}")

        elif data == "back_to_qari_list":
            await qari_list(update, context)
    except Exception as e:
        logger.error(f"Error in button_callback: {e}")
        await query.message.reply_text("একটি ত্রুটি ঘটেছে। অনুগ্রহ করে আবার চেষ্টা করুন।")

# Prayer reminder messages
async def salat_reminder(update: Update, context: ContextTypes.DEFAULT_TYPE, prayer_name_bn, emoji):
    try:
        if prayer_name_bn == "ফজর":
            message = (
                f"🌿 আস্সালামু আলাইকুম! হে আমার মুসলিম ভাই ও বোনেরা,\n\n"
                f"**ফজর** সালাতের সময় হয়েছে। রাসূলুল্লাহ (সাঃ) বলেছেন, **\"যে ব্যক্তি ফজরের নামাজ পড়ল, সে আল্লাহর জিম্মায় থাকবে।\"** (মুসলিম)। এছাড়া ফজরের দুই রাকাত নামাজ দুনিয়া ও এর মধ্যে যা কিছু আছে তার চেয়েও উত্তম। জীবনের সব ব্যস্ততাকে এক পাশে রেখে এই মুহূর্তে সিজদায় লুটিয়ে পড়ুন। অন্তরকে প্রশান্ত করুন, কারণ সালাত মুমিনের জন্য শ্রেষ্ঠ নিরাময়।\n\n"
                f"“নিশ্চয় সালাত মুমিনদের ওপর নির্দিষ্ট সময়ে ফরয।” (সূরা আন-নিসা: ১০৩)\n\n"
                f"আল্লাহ আমাদের সবাইকে সঠিক সময়ে সালাত আদায় করার তৌফিক দিন। আমীন। {emoji}"
            )
        elif prayer_name_bn == "যোহর":
            message = (
                f"🌿 আস্সালামু আলাইকুম! হে আমার মুসলিম ভাই ও বোনেরা,\n\n"
                f"**যোহর** সালাতের সময় হয়েছে। রাসূলুল্লাহ (সাঃ) বলেছেন, **\"যে ব্যক্তি যোহরের ফরজের আগে চার রাকাত ও পরে দুই রাকাত সুন্নত আদায় করে, তার জন্য জান্নাতে একটি ঘর নির্মাণ করা হবে।\"** (তিরমিজি)। এই সালাত আদায়ের মাধ্যমে শয়তান থেকে রক্ষা পাওয়া যায় এবং রিজিক-এ বরকত আসে। জীবনের সব ব্যস্ততাকে এক পাশে রেখে এই মুহূর্তে সিজদায় লুটিয়ে পড়ুন। অন্তরকে প্রশান্ত করুন, কারণ সালাত মুমিনের জন্য শ্রেষ্ঠ নিরাময়।\n\n"
                f"“নিশ্চয় সালাত মুমিনদের ওপর নির্দিষ্ট সময়ে ফরয।” (সূরা আন-নিসা: ১০৩)\n\n"
                f"আল্লাহ আমাদের সবাইকে সঠিক সময়ে সালাত আদায় করার তৌফিক দিন। আমীন। {emoji}"
            )
        elif prayer_name_bn == "আসর":
            message = (
                f"🌿 আস্সালামু আলাইকুম! হে আমার মুসলিম ভাই ও বোনেরা,\n\n"
                f"**আসর** সালাতের সময় হয়েছে। আসরের সময় মানুষ সাধারণত কাজ-কর্মে ব্যস্ত থাকে, তাই এই সালাতের প্রতি বিশেষ গুরুত্ব দেওয়া হয়েছে। রাসূলুল্লাহ (সাঃ) বলেছেন, **\"যদি কোনো ব্যক্তির আসরের নামাজ ছুটে যায়, তাহলে যেন তার পরিবার-পরিজন ও মাল-সম্পদ সবকিছুই ধ্বংস হয়ে গেল।\"** (বুখারি)। অন্যদিকে, যারা আসরের নামাজ নিয়মিত আদায় করে তাদের জন্য জান্নাতে একটি বিশেষ ঘর রয়েছে। জীবনের সব ব্যস্ততাকে এক পাশে রেখে এই মুহূর্তে সিজদায় লুটিয়ে পড়ুন। অন্তরকে প্রশান্ত করুন, কারণ সালাত মুমিনের জন্য শ্রেষ্ঠ নিরাময়।\n\n"
                f"“নিশ্চয় সালাত মুমিনদের ওপর নির্দিষ্ট সময়ে ফরয।” (সূরা আন-নিসা: ১০৩)\n\n"
                f"আল্লাহ আমাদের সবাইকে সঠিক সময়ে সালাত আদায় করার তৌফিক দিন। আমীন। {emoji}"
            )
        elif prayer_name_bn == "মাগরিব":
            message = (
                f"🌿 আস্সালামু আলাইকুম! হে আমার মুসলিম ভাই ও বোনেরা,\n\n"
                f"**মাগরিব** সালাতের সময় হয়েছে। সূর্যাস্তের সাথে সাথে এই সালাত আদায় করা মুস্তাহাব। রাসূলুল্লাহ (সাঃ) বলেছেন, **\"যে ব্যক্তি মাগরিবের পর ছয় রাকা'আত নামাজ আদায় করবে, তার গুনাহ্ মাফ করে দেয়া হবে যদিও ওটা সমুদ্রের ফেনা রাশির সমান হয়।\"** (তাবরানী)। জীবনের সব ব্যস্ততাকে এক পাশে রেখে এই মুহূর্তে সিজদায় লুটিয়ে পড়ুন। অন্তরকে প্রশান্ত করুন, কারণ সালাত মুমিনের জন্য শ্রেষ্ঠ নিরাময়।\n\n"
                f"“নিশ্চয় সালাত মুমিনদের ওপর নির্দিষ্ট সময়ে ফরয।” (সূরা আন-নিসা: ১০৩)\n\n"
                f"আল্লাহ আমাদের সবাইকে সঠিক সময়ে সালাত আদায় করার তৌফিক দিন। আমীন। {emoji}"
            )
        elif prayer_name_bn == "ইশা":
            message = (
                f"🌿 আস্সালামু আলাইকুম! হে আমার মুসলিম ভাই ও বোনেরা,\n\n"
                f"**ইশা** সালাতের সময় হয়েছে। এই সালাতের ফজিলত অপরিসীম। রাসূলুল্লাহ (সাঃ) বলেছেন, **\"যে ব্যক্তি এশার নামাজ জামাতসহকারে পড়ল, সে যেন অর্ধরাত পর্যন্ত ইবাদত করল।\"** (মুসলিম)। দিনের ক্লান্তি এবং ঘুমের তাড়না সত্ত্বেও এই নামাজে উপস্থিত হওয়া অত্যন্ত পুণ্যের কাজ। জীবনের সব ব্যস্ততাকে এক পাশে রেখে এই মুহূর্তে সিজদায় লুটিয়ে পড়ুন। অন্তরকে প্রশান্ত করুন, কারণ সালাত মুমিনের জন্য শ্রেষ্ঠ নিরাময়।\n\n"
                f"“নিশ্চয় সালাত মুমিনদের ওপর নির্দিষ্ট সময়ে ফরয।” (সূরা আন-নিসা: ১০৩)\n\n"
                f"আল্লাহ আমাদের সবাইকে সঠিক সময়ে সালাত আদায় করার তৌফিক দিন। আমীন। {emoji}"
            )
        else:
            message = (
                f"🌿 আস্সালামু আলাইকুম! হে আমার মুসলিম ভাই ও বোনেরা,\n\n"
                f"{prayer_name_bn} সালাতের সময় হয়েছে। আল্লাহকে স্মরণ করার, তাঁর কাছে সাহায্য চাওয়ার এবং তাঁর রহমত লাভের এই সুযোগ হাতছাড়া করবেন না। জীবনের সব ব্যস্ততাকে এক পাশে রেখে এই মুহূর্তে সিজদায় লুটিয়ে পড়ুন। অন্তরকে প্রশান্ত করুন, কারণ সালাত মুমিনের জন্য শ্রেষ্ঠ নিরাময়।\n\n"
                f"“নিশ্চয় সালাত মুমিনদের ওপর নির্দিষ্ট সময়ে ফরয।” (সূরা আন-নিসা: ১০৩)\n\n"
                f"আল্লাহ আমাদের সবাইকে সঠিক সময়ে সালাত আদায় করার তৌফিক দিন। আমীন। {emoji}"
            )

        await update.message.reply_text(message, parse_mode='Markdown')
    except Exception as e:
        logger.error(f"Error in salat_reminder for {prayer_name_bn}: {e}")
        await update.message.reply_text("স্মরণ করিয়ে দিতে একটি ত্রুটি ঘটেছে।")

async def check_and_send_salat_reminder(update: Update, context: ContextTypes.DEFAULT_TYPE, prayer_name_bn, prayer_key, emoji):
    try:
        await set_bot_commands(context, update.effective_chat.id, update.effective_chat.type)
        current_time = datetime.now(BANGLADESH_TIMEZONE).time()

        dhaka_coords = {"lat": 23.8103, "lon": 90.4125}
        prayer_times_24h = get_prayer_times(dhaka_coords['lat'], dhaka_coords['lon'])

        if not prayer_times_24h:
            await update.message.reply_text("নামাজের সময়সূচী পেতে ব্যর্থ হয়েছে।")
            return

        prayer_times_obj = {k: datetime.strptime(v, '%H:%M').time() for k, v in prayer_times_24h.items()}

        prayers_list = [
            (prayer_times_obj["ফজর"], "ফজর"),
            (prayer_times_obj["যোহর"], "যোহর"),
            (prayer_times_obj["আসর"], "আসর"),
            (prayer_times_obj["মাগরিব"], "মাগরিব"),
            (prayer_times_obj["ইশা"], "ইশা")
        ]

        current_waqt = None

        if current_time < prayers_list[0][0]:
            current_waqt = "ইশা"
        else:
            for i in range(len(prayers_list)):
                if current_time >= prayers_list[i][0]:
                    current_waqt = prayers_list[i][1]

        if prayer_key == current_waqt:
            await salat_reminder(update, context, prayer_name_bn, emoji)
        else:
            await update.message.reply_text(f"⚠️ দুঃখিত! এখন {prayer_name_bn} সালাতের সময় হয়নি। এখন {current_waqt} সালাতের সময় চলছে।")

    except Exception as e:
        logger.error(f"Error in check_and_send_salat_reminder for {prayer_name_bn}: {e}")
        await update.message.reply_text("সময় পরীক্ষা করতে একটি ত্রুটি ঘটেছে।")

async def fajr_reminder(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await check_and_send_salat_reminder(update, context, "ফজর", "ফজর", "🌅")

async def dhuhr_reminder(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await check_and_send_salat_reminder(update, context, "যোহর", "যোহর", "☀️")

async def asr_reminder(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await check_and_send_salat_reminder(update, context, "আসর", "আসর", "🌤️")

async def maghrib_reminder(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await check_and_send_salat_reminder(update, context, "মাগরিব", "মাগরিব", "🌇")

async def isha_reminder(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await check_and_send_salat_reminder(update, context, "ইশা", "ইশা", "🌌")

async def jumuah_reminder(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        await set_bot_commands(context, update.effective_chat.id, update.effective_chat.type)
        today = datetime.now(BANGLADESH_TIMEZONE).weekday()
        if today != 4: # 4 is Friday
            await update.message.reply_text("⚠️ দুঃখিত, জুম'আর সালাত শুধুমাত্র শুক্রবারে হয়।")
            return

        current_time = datetime.now(BANGLADESH_TIMEZONE).time()
        dhaka_coords = {"lat": 23.8103, "lon": 90.4125}
        prayer_times_24h = get_prayer_times(dhaka_coords['lat'], dhaka_coords['lon'])

        if not prayer_times_24h:
            await update.message.reply_text("নামাজের সময়সূচী পেতে ব্যর্থ হয়েছে।")
            return

        jumuah_time_str = prayer_times_24h.get("যোহর")
        jumuah_time_obj = datetime.strptime(jumuah_time_str, '%H:%M').time()

        time_to_check = (datetime.combine(datetime.today(), jumuah_time_obj) - timedelta(minutes=10)).time()

        if current_time >= time_to_check:
            message = (
                "🌿 হে আমার মুসলিম ভাই ও বোনেরা,\n\n"
                "আজ **জুম'আতুল মুবারক**। জুম'আর সালাতের সময় হয়েছে। নিজেদের সব কাজ থেকে অবসর নিয়ে তাড়াতাড়ি মসজিদে চলে আসুন। আল্লাহ তা’আলা জুম'আর দিনকে আমাদের জন্য বিশেষভাবে বরকতময় করেছেন। এই দিনে দোয়া কবুল হয়।\n\n"
                "রাসূলুল্লাহ সাল্লাল্লাহু আলাইহি ওয়াসাল্লাম বলেছেন, **'যে ব্যক্তি জুম্মার দিন জানাবাত গোসলের ন্যায় গোসল করে এবং সালাত-এর জন্য প্রথমে আগমন করে সে যেন, একটি উট কুরবানী করল। যে ব্যক্তি দ্বিতীয় পর্যায়ে আগমন করে সে যেন, একটি গাভী কুরবানী করল।'** (সহিহ বুখারী) \n\n"
                "জুম'আর দিনে সূরা আল-কাহফ (১৮) পাঠ করা খুবই ফযীলতপূর্ণ।\n\n"
                "আল্লাহ আমাদের সবাইকে জুম'আর সালাত ও এর ফযিলতগুলো হাসিল করার তৌফিক দিন। আমীন। 🕌"
            )
            await update.message.reply_text(message, parse_mode='Markdown')
        else:
            await update.message.reply_text(f"⚠️ দুঃখিত! এখন জুম'আর সালাতের সময় হয়নি।")

    except Exception as e:
        logger.error(f"Error in jumuah_reminder: {e}")
        await update.message.reply_text("সময় পরীক্ষা করতে একটি ত্রুটি ঘটেছে।")

async def sehri_reminder(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        await set_bot_commands(context, update.effective_chat.id, update.effective_chat.type)
        if not is_ramadan():
            await update.message.reply_text("এখন রমজান মাস নয়। সেহরির সময় এখন প্রযোজ্য নয়।")
            return

        current_time = datetime.now(BANGLADESH_TIMEZONE).time()
        dhaka_coords = {"lat": 23.8103, "lon": 90.4125}
        prayer_times_24h = get_prayer_times(dhaka_coords['lat'], dhaka_coords['lon'])

        if not prayer_times_24h:
            await update.message.reply_text("সেহরির সময় পেতে ব্যর্থ হয়েছে।")
            return

        sehri_time_str = prayer_times_24h.get("সেহরি")
        if not sehri_time_str or sehri_time_str == "N/A":
            await update.message.reply_text("সেহরির সময় পাওয়া যায়নি।")
            return

        sehri_time_obj = datetime.strptime(sehri_time_str, '%H:%M').time()
        time_to_check = (datetime.combine(datetime.today(), sehri_time_obj) - timedelta(minutes=15)).time()

        if current_time >= time_to_check and current_time < sehri_time_obj:
            message = (
                "🌙 সেহরির শেষ সময় প্রায়! রোজার নিয়তে খাবার গ্রহণ করে নিন।\n\n"
                "রাসূল (সাঃ) বলেছেন, 'তোমরা সেহরি খাও, কারণ সেহরিতে বরকত রয়েছে।' (বুখারী ও মুসলিম)\n\n"
                "আল্লাহ আমাদের সিয়াম কবুল করুন। আমীন।🍽️"
            )
            await update.message.reply_text(message)
        else:
            await update.message.reply_text("⚠️ দুঃখিত! এখন সেহরির সময় চলছে না।")

    except Exception as e:
        logger.error(f"Error in sehri_reminder: {e}")
        await update.message.reply_text("সময় পরীক্ষা করতে একটি ত্রুটি ঘটেছে।")

async def iftar_reminder(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        await set_bot_commands(context, update.effective_chat.id, update.effective_chat.type)
        if not is_ramadan():
            await update.message.reply_text("এখন রমজান মাস নয়। ইফতারের সময় এখন প্রযোজ্য নয়।")
            return

        current_time = datetime.now(BANGLADESH_TIMEZONE).time()
        dhaka_coords = {"lat": 23.8103, "lon": 90.4125}
        prayer_times_24h = get_prayer_times(dhaka_coords['lat'], dhaka_coords['lon'])

        if not prayer_times_24h:
            await update.message.reply_text("ইফতারের সময় পেতে ব্যর্থ হয়েছে।")
            return

        iftar_time_str = prayer_times_24h.get("ইফতার")
        if not iftar_time_str or iftar_time_str == "N/A":
            await update.message.reply_text("ইফতারের সময় পাওয়া যায়নি।")
            return

        iftar_time_obj = datetime.strptime(iftar_time_str, '%H:%M').time()
        time_to_check = (datetime.combine(datetime.today(), iftar_time_obj) - timedelta(minutes=5)).time()

        if current_time >= time_to_check and current_time < iftar_time_obj:
            message = (
                "🌇 ইফতারের সময় হয়েছে! আল্লাহ আপনার সিয়াম কবুল করুন।\n\n"
                "ইফতারের পূর্ব মুহূর্তে দোয়া কবুল হয়। এই সময়টিকে নিজের ও উম্মাহর জন্য বেশি বেশি দোয়া করে কাজে লাগান।\n\n"
                "আল্লাহ আমাদের সবাইকে ইফতারের বরকত দান করুন। আমীন। 🍽️"
            )
            await update.message.reply_text(message)
        else:
            await update.message.reply_text("⚠️ দুঃখিত! এখন ইফতারের সময় হয়নি।")

    except Exception as e:
        logger.error(f"Error in iftar_reminder: {e}")
        await update.message.reply_text("সময় পরীক্ষা করতে একটি ত্রুটি ঘটেছে।")

# Check server time
async def check_time_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await set_bot_commands(context, update.effective_chat.id, update.effective_chat.type)
    current_server_time = datetime.now(BANGLADESH_TIMEZONE)
    message = f"বটের সার্ভারের বর্তমান সময়:\n{current_server_time.strftime('%I:%M:%S %p, %A, %B %d, %Y')}"
    await update.message.reply_text(message)

# Private chat warning message for group-only commands
async def private_warning(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await set_bot_commands(context, update.effective_chat.id, update.effective_chat.type)
    await update.message.reply_text("⚠️ এই কমান্ডটি শুধুমাত্র গ্রুপে কাজ করে।")

# Handle bot being added to a group
async def chat_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        chat_id = update.effective_chat.id
        chat_type = update.effective_chat.type
        if update.my_chat_member.new_chat_member.status in ["member", "administrator"]:
            await set_bot_commands(context, chat_id, chat_type)
            message = (
                "আসসালামু আলাইকুম! আমি গ্রুপে যোগ দিয়েছি। আমি আপনাদের নির্দিষ্ট এলাকার নামাজের সময় জানাতে এবং কুরআন তেলাওয়াত শুনাতে সাহায্য করব।\n\n"
                "আমার উপলব্ধ কমান্ডগুলো:\n"
                "• /prayer - নামাজের সময় দেখুন (যেমন: /prayer Dhaka বা /prayer Dhaka Savar)।\n"
                "• /surah - সূরার অডিও পান (উদাহরণ: /surah Al-Fatiha বা /surah 1)। সরাসরি সূরা পেতে ক্বারীর নাম যোগ করুন (যেমন: /surah Al-Fatiha Mishary).\n"
                "• /delete_surah - আপনার দেওয়া সূরাটি এবং কমান্ড মেসেজটি মুছে দিন।\n"
                "• /qari_list - ক্বারীদের তালিকা দেখুন।\n"
                "• /surah_list - সূরার তালিকা দেখুন।\n"
                "• /salat_reminder_fajr - ফজরের সালাতের জন্য স্মরণ করিয়ে দিন।\n"
                "• /salat_reminder_dhuhr - যোহরের সালাতের জন্য স্মরণ করিয়ে দিন।\n"
                "• /salat_reminder_jumuah - জুম'আর সালাতের জন্য স্মরণ করিয়ে দিন।\n"
                "• /salat_reminder_asr - আসরের সালাতের জন্য স্মরণ করিয়ে দিন।\n"
                "• /salat_reminder_maghrib - মাগরিবের সালাতের জন্য স্মরণ করিয়ে দিন।\n"
                "• /salat_reminder_isha - ইশার সালাতের জন্য স্মরণ করিয়ে দিন।\n"
            )
            if is_ramadan():
                message += "• /sehri_reminder - সেহরির সময় স্মরণ করিয়ে দিন।\n"
                message += "• /iftar_reminder - ইফতারের সময় স্মরণ করিয়ে দিন।\n"

            await update.effective_chat.send_message(message)
    except Exception as e:
        logger.error(f"Error in chat_member handler: {e}")

# Main function
def main():
    try:
        app = ApplicationBuilder().token(BOT_TOKEN).build()

        # Handlers for both private and group chats
        app.add_handler(CommandHandler("start", start))
        app.add_handler(CommandHandler("help", help_command))
        app.add_handler(CommandHandler("prayer", prayer))
        app.add_handler(CommandHandler("surah", surah))
        app.add_handler(CommandHandler("qari_list", qari_list))
        app.add_handler(CommandHandler("surah_list", surah_list))
        app.add_handler(CommandHandler("check_time", check_time_command))

        # Group-specific handlers
        group_handlers = [
            CommandHandler("delete_surah", delete_surah_command, filters=filters.ChatType.GROUPS),
            CommandHandler("salat_reminder_fajr", fajr_reminder, filters=filters.ChatType.GROUPS),
            CommandHandler("salat_reminder_dhuhr", dhuhr_reminder, filters=filters.ChatType.GROUPS),
            CommandHandler("salat_reminder_jumuah", jumuah_reminder, filters=filters.ChatType.GROUPS),
            CommandHandler("salat_reminder_asr", asr_reminder, filters=filters.ChatType.GROUPS),
            CommandHandler("salat_reminder_maghrib", maghrib_reminder, filters=filters.ChatType.GROUPS),
            CommandHandler("salat_reminder_isha", isha_reminder, filters=filters.ChatType.GROUPS),
            CommandHandler("sehri_reminder", sehri_reminder, filters=filters.ChatType.GROUPS),
            CommandHandler("iftar_reminder", iftar_reminder, filters=filters.ChatType.GROUPS),
        ]

        # Private chat handlers for group-only commands
        private_warning_handlers = [
            CommandHandler("delete_surah", private_warning, filters=filters.ChatType.PRIVATE),
            CommandHandler("salat_reminder_fajr", private_warning, filters=filters.ChatType.PRIVATE),
            CommandHandler("salat_reminder_dhuhr", private_warning, filters=filters.ChatType.PRIVATE),
            CommandHandler("salat_reminder_jumuah", private_warning, filters=filters.ChatType.PRIVATE),
            CommandHandler("salat_reminder_asr", private_warning, filters=filters.ChatType.PRIVATE),
            CommandHandler("salat_reminder_maghrib", private_warning, filters=filters.ChatType.PRIVATE),
            CommandHandler("salat_reminder_isha", private_warning, filters=filters.ChatType.PRIVATE),
            CommandHandler("sehri_reminder", private_warning, filters=filters.ChatType.PRIVATE),
            CommandHandler("iftar_reminder", private_warning, filters=filters.ChatType.PRIVATE),
        ]

        for handler in group_handlers:
            app.add_handler(handler)

        for handler in private_warning_handlers:
            app.add_handler(handler)

        app.add_handler(ChatMemberHandler(chat_member, ChatMemberHandler.MY_CHAT_MEMBER))
        app.add_handler(CallbackQueryHandler(button_callback))
        logger.info("Starting bot polling...")
        app.run_polling()
    except Exception as e:
        logger.error(f"Error starting bot: {e}")

if __name__ == "__main__":
    main()






