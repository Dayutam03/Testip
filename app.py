import os
import json
import re
import time
import asyncio
import zipfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass

import requests
from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup,
    LinkPreviewOptions, CopyTextButton, InputMediaPhoto,
    InputMediaVideo, InputMediaDocument
)
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, ContextTypes, JobQueue
)
from colorama import init, Fore, Style
from dotenv import load_dotenv
from telegram.constants import ParseMode
from telegram.error import BadRequest

init(autoreset=True)
load_dotenv()

print(f"{Fore.GREEN}[]════════[] STARTING BOT []════════[]{Style.RESET_ALL}")

@dataclass
class Config:
    APIKEY: str = os.getenv("APIKEY", "")
    BOT_TOKEN: str = os.getenv("BOT_TOKEN", "")
    OWNER_ID: int = int(os.getenv("OWNER_ID", "0"))
    CH_INFO: str = os.getenv("CH_INFO", "")
    OWNER_LINK: str = os.getenv("OWNER_LINK", "")
    SUPPORT: str = os.getenv("SUPPORT", "")
    OTPS_GROUP: str = os.getenv("OTPS_GROUP", "")
    NUM_GROUP_ID: str = os.getenv("NUM_GROUP_ID", "")
    
    def __post_init__(self):
        if not self.BOT_TOKEN:
            raise ValueError("BOT_TOKEN not found in .env")
        if not self.APIKEY:
            raise ValueError("APIKEY not found in .env")
        if self.OWNER_ID == 0:
            raise ValueError("OWNER_ID not found in .env")
    
    @staticmethod
    def save_env(key: str, value: str):
        env_vars = {}
        try:
            with open(".env", "r", encoding="utf-8") as f:
                for line in f:
                    if '=' in line:
                        k, v = line.strip().split('=', 1)
                        env_vars[k] = v
        except:
            pass
        
        env_vars[key] = value
        
        with open(".env", "w", encoding="utf-8") as f:
            for k, v in env_vars.items():
                f.write(f"{k}={v}\n")
        
        load_dotenv(override=True)

class Database:
    BASE_DIR = Path("database")
    
    @classmethod
    def init_db(cls):
        cls.BASE_DIR.mkdir(exist_ok=True)
        Path("numbers").mkdir(exist_ok=True)
        
        default_files = {
            "groups.json": {"groups": []},
            "users.json": {"not_verif": [], "Verified": []},
            "otps.json": {"otps": [], "statistics": {}, "last_cleanup": datetime.now(timezone.utc).isoformat()},
            "user_request.json": [],
            "country.json": {
                "62": {"name": "Indonesia", "flag": "🇮🇩", "shortName": "ID", "code": "62"},
                "1": {"name": "United States", "flag": "🇺🇸", "shortName": "US", "code": "1"},
                "44": {"name": "United Kingdom", "flag": "🇬🇧", "shortName": "UK", "code": "44"},
                "33": {"name": "France", "flag": "🇫🇷", "shortName": "FR", "code": "33"},
                "49": {"name": "Germany", "flag": "🇩🇪", "shortName": "DE", "code": "49"},
                "7": {"name": "Russia", "flag": "🇷🇺", "shortName": "RU", "code": "7"},
                "86": {"name": "China", "flag": "🇨🇳", "shortName": "CN", "code": "86"},
                "91": {"name": "India", "flag": "🇮🇳", "shortName": "IN", "code": "91"},
                "81": {"name": "Japan", "flag": "🇯🇵", "shortName": "JP", "code": "81"},
                "82": {"name": "South Korea", "flag": "🇰🇷", "shortName": "KR", "code": "82"},
                "234": {"name": "Nigeria", "flag": "🇳🇬", "shortName": "NG", "code": "234"},
                "228": {"name": "Togo", "flag": "🇹🇬", "shortName": "TG", "code": "228"},
                "58": {"name": "Venezuela", "flag": "🇻🇪", "shortName": "VE", "code": "58"},
                "55": {"name": "Brazil", "flag": "🇧🇷", "shortName": "BR", "code": "55"},
                "225": {"name": "Ivory Coast", "flag": "🇨🇮", "shortName": "CI", "code": "225"},
                "229": {"name": "Benin", "flag": "🇧🇯", "shortName": "BJ", "code": "229"}
            },
            "numbers.json": [],
            "verif.json": {},
            "sms_history.json": [],
            "autodel.json": {"enabled": False, "minutes": 0, "notif_message_ids": {}},
            "bot_messages.json": [],
            "daily_stats.json": {}
        }
        
        for file, content in default_files.items():
            path = cls.BASE_DIR / file
            if not path.exists():
                with open(path, "w", encoding="utf-8") as f:
                    json.dump(content, f, indent=4, ensure_ascii=False)
    
    @classmethod
    def load_db(cls, db_name: str) -> Any:
        path = cls.BASE_DIR / f"{db_name}.json"
        if path.exists():
            try:
                with open(path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except:
                return cls.get_default_structure(db_name)
        else:
            return cls.get_default_structure(db_name)
    
    @classmethod
    def get_default_structure(cls, db_name: str) -> Any:
        default_structures = {
            "groups": {"groups": []},
            "users": {"not_verif": [], "Verified": []},
            "otps": {"otps": [], "statistics": {}, "last_cleanup": datetime.now(timezone.utc).isoformat()},
            "user_request": [],
            "country": {},
            "numbers": [],
            "verif": {},
            "sms_history": [],
            "autodel": {"enabled": False, "minutes": 0, "notif_message_ids": {}},
            "bot_messages": [],
            "daily_stats": {}
        }
        return default_structures.get(db_name, {})
    
    @classmethod
    def save_db(cls, db_name: str, data: Any):
        path = cls.BASE_DIR / f"{db_name}.json"
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
    
    @classmethod
    def get_users(cls) -> Dict[str, List[int]]:
        data = cls.load_db("users")
        if isinstance(data, dict):
            return data
        else:
            return {"not_verif": [], "Verified": []}
    
    @classmethod
    def add_user(cls, user_id: int, verified: bool = False):
        data = cls.get_users()
        if verified:
            if user_id not in data["Verified"]:
                data["Verified"].append(user_id)
            if user_id in data["not_verif"]:
                data["not_verif"].remove(user_id)
        else:
            if user_id not in data["not_verif"] and user_id not in data["Verified"]:
                data["not_verif"].append(user_id)
        cls.save_db("users", data)
    
    @classmethod
    def verify_user(cls, user_id: int) -> bool:
        data = cls.get_users()
        if user_id in data["not_verif"]:
            data["not_verif"].remove(user_id)
            if user_id not in data["Verified"]:
                data["Verified"].append(user_id)
            cls.save_db("users", data)
            return True
        return False
    
    @classmethod
    def is_verified(cls, user_id: int) -> bool:
        data = cls.get_users()
        return user_id in data["Verified"]
    
    @classmethod
    def remove_from_verified(cls, user_id: int):
        data = cls.get_users()
        if user_id in data["Verified"]:
            data["Verified"].remove(user_id)
        if user_id not in data["not_verif"]:
            data["not_verif"].append(user_id)
        cls.save_db("users", data)
    
    @classmethod
    def get_groups(cls) -> List[str]:
        data = cls.load_db("groups")
        if isinstance(data, dict) and "groups" in data:
            return data["groups"]
        return []
    
    @classmethod
    def add_group(cls, group_id: str):
        data = cls.load_db("groups")
        if not isinstance(data, dict):
            data = {"groups": []}
        if "groups" not in data:
            data["groups"] = []
        if group_id not in data["groups"]:
            data["groups"].append(group_id)
            cls.save_db("groups", data)
    
    @classmethod
    def remove_group(cls, group_id: str) -> bool:
        data = cls.load_db("groups")
        if isinstance(data, dict) and "groups" in data and group_id in data["groups"]:
            data["groups"].remove(group_id)
            cls.save_db("groups", data)
            return True
        return False
    
    @classmethod
    def get_user_requests(cls) -> List[Dict]:
        data = cls.load_db("user_request")
        if isinstance(data, list):
            return data
        else:
            return []
    
    @classmethod
    def add_user_request(cls, user_id: int, numbers: List[str]):
        data = cls.get_user_requests()
        data = [r for r in data if r.get("user_id") != user_id]
        data.append({
            "user_id": user_id,
            "numbers": numbers,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
        cls.save_db("user_request", data)
    
    @classmethod
    def get_user_numbers(cls, user_id: int) -> Optional[List[str]]:
        data = cls.get_user_requests()
        for req in data:
            if req.get("user_id") == user_id:
                return req.get("numbers", [])
        return None
    
    @classmethod
    def remove_user_request(cls, user_id: int) -> bool:
        data = cls.get_user_requests()
        original_len = len(data)
        data = [r for r in data if r.get("user_id") != user_id]
        if len(data) != original_len:
            cls.save_db("user_request", data)
            return True
        return False
    
    @classmethod
    def get_countries(cls) -> Dict:
        data = cls.load_db("country")
        if isinstance(data, dict):
            return data
        else:
            return {}
    
    @classmethod
    def get_country_by_code(cls, phone: str) -> Optional[Dict]:
        countries = cls.get_countries()
        for code, info in countries.items():
            if phone.startswith(code):
                return info
        return None
    
    @classmethod
    def add_otp_record(cls, otp_data: Dict):
        try:
            data = cls.load_db("otps")
            
            if not isinstance(data, dict):
                data = {"otps": [], "statistics": {}, "last_cleanup": datetime.now(timezone.utc).isoformat()}
            
            if "otps" not in data:
                data["otps"] = []
            
            data["otps"].append(otp_data)
            
            cls.save_db("otps", data)
            
            cls.update_daily_stats(otp_data)
            
            cls.cleanup_otps()
            
        except Exception as e:
            print(f"Error in add_otp_record: {type(e).__name__}: {e}")
            cls.save_db("otps", {"otps": [], "statistics": {}, "last_cleanup": datetime.now(timezone.utc).isoformat()})
    
    @classmethod
    def update_daily_stats(cls, otp_data: Dict):
        try:
            stats = cls.load_db("daily_stats")
            if not isinstance(stats, dict):
                stats = {}
            
            date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            country = otp_data.get("country", "Unknown")
            service = otp_data.get("service", "Unknown").lower()
            
            if date_str not in stats:
                stats[date_str] = {
                    "total": 0,
                    "countries": {},
                    "services": {}
                }
            
            stats[date_str]["total"] += 1
            
            if country not in stats[date_str]["countries"]:
                stats[date_str]["countries"][country] = 0
            stats[date_str]["countries"][country] += 1
            
            if service not in stats[date_str]["services"]:
                stats[date_str]["services"][service] = 0
            stats[date_str]["services"][service] += 1
            
            cls.save_db("daily_stats", stats)
            
        except Exception as e:
            print(f"Error updating daily stats: {e}")
    
    @classmethod
    def cleanup_otps(cls):
        data = cls.load_db("otps")
        
        if not isinstance(data, dict):
            return
        
        otps = data.get("otps", [])
        if len(otps) > 0:
            now = datetime.now(timezone.utc)
            cutoff = now - timedelta(hours=24)
            
            filtered_otps = []
            for otp in otps:
                try:
                    timestamp = datetime.fromisoformat(otp.get("timestamp", ""))
                    if timestamp > cutoff:
                        filtered_otps.append(otp)
                except:
                    continue
            
            if len(filtered_otps) != len(otps):
                data["otps"] = filtered_otps
                cls.save_db("otps", data)
    
    @classmethod
    def cleanup_sms_history(cls):
        history = cls.load_db("sms_history")
        if isinstance(history, list) and len(history) > 1000:
            cls.save_db("sms_history", history[-1000:])
    
    @classmethod
    def get_statistics(cls) -> Dict:
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        stats = cls.load_db("daily_stats")
        
        today_stats = stats.get(today, {})
        today_total = today_stats.get("total", 0)
        today_countries = len(today_stats.get("countries", {}))
        
        users = cls.get_users()
        if not isinstance(users, dict):
            users = {"not_verif": [], "Verified": []}
        
        total_users = len(users.get("not_verif", [])) + len(users.get("Verified", []))
        verified_users = len(users.get("Verified", []))
        total_numbers = cls.get_total_numbers()
        
        return {
            "today_otps": today_total,
            "today_countries": today_countries,
            "total_numbers": total_numbers,
            "total_users": total_users,
            "verified_users": verified_users,
            "traffic": today_stats.get("countries", {})
        }
    
    @classmethod
    def get_today_traffic_by_service_and_country(cls) -> Dict:
        today = datetime.now(timezone.utc).date()
        otps_data = cls.load_db("otps")
        otps_list = otps_data.get("otps", []) if isinstance(otps_data, dict) else []
        
        result = {}
        
        for otp in otps_list:
            try:
                timestamp = datetime.fromisoformat(otp.get("timestamp", "")).date()
                if timestamp != today:
                    continue
                
                service = otp.get("service", "Unknown").capitalize()
                country = otp.get("country", "Unknown")
                
                if service not in result:
                    result[service] = {}
                
                if country not in result[service]:
                    result[service][country] = 0
                
                result[service][country] += 1
            except:
                continue
        
        return result
    
    @classmethod
    def get_traffic_for_days(cls, days: int) -> Dict:
        if days <= 0:
            return {}
        
        stats = cls.load_db("daily_stats")
        if not isinstance(stats, dict):
            return {}
        
        now = datetime.now(timezone.utc)
        result = {
            "total": 0,
            "countries": {},
            "services": {},
            "dates": []
        }
        
        for i in range(days):
            date = (now - timedelta(days=i)).strftime("%Y-%m-%d")
            if date in stats:
                day_stats = stats[date]
                result["total"] += day_stats.get("total", 0)
                result["dates"].append(date)
                
                for country, count in day_stats.get("countries", {}).items():
                    if country not in result["countries"]:
                        result["countries"][country] = 0
                    result["countries"][country] += count
                
                for service, count in day_stats.get("services", {}).items():
                    service_name = service.capitalize()
                    if service_name not in result["services"]:
                        result["services"][service_name] = 0
                    result["services"][service_name] += count
        
        return result
    
    @classmethod
    def get_all_time_stats(cls) -> Dict:
        stats = cls.load_db("daily_stats")
        if not isinstance(stats, dict):
            return {"total": 0, "countries": {}, "services": {}}
        
        total = 0
        countries = {}
        services = {}
        
        for date, day_stats in stats.items():
            total += day_stats.get("total", 0)
            for country, count in day_stats.get("countries", {}).items():
                if country not in countries:
                    countries[country] = 0
                countries[country] += count
            for service, count in day_stats.get("services", {}).items():
                service_name = service.capitalize()
                if service_name not in services:
                    services[service_name] = 0
                services[service_name] += count
        
        return {"total": total, "countries": countries, "services": services}
    
    @classmethod
    def get_total_numbers(cls) -> int:
        total = 0
        numbers_dir = Path("numbers")
        if numbers_dir.exists():
            for file in numbers_dir.glob("*.txt"):
                try:
                    with open(file, "r", encoding="utf-8") as f:
                        lines = f.readlines()
                        total += len([l for l in lines if l.strip()])
                except:
                    continue
        return total
    
    @classmethod
    def get_ranges(cls) -> List[Dict]:
        data = cls.load_db("numbers")
        if isinstance(data, list):
            return data
        else:
            return []
    
    @classmethod
    def add_range(cls, range_data: Dict):
        data = cls.get_ranges()
        data.append(range_data)
        cls.save_db("numbers", data)
    
    @classmethod
    def remove_range(cls, range_id: int) -> bool:
        data = cls.get_ranges()
        if 0 <= range_id < len(data):
            range_data = data[range_id]
            filename = range_data.get("filename", "")
            
            if filename:
                file_path = Path("numbers") / filename
                if file_path.exists():
                    file_path.unlink()
            
            data.pop(range_id)
            cls.save_db("numbers", data)
            
            for i in range(len(data)):
                data[i]["id"] = i + 1
            
            cls.save_db("numbers", data)
            return True
        return False
    
    @classmethod
    def get_range_file(cls, range_id: int) -> Optional[Path]:
        data = cls.get_ranges()
        if 0 <= range_id < len(data):
            range_data = data[range_id]
            filename = range_data.get("filename", "")
            if filename:
                file_path = Path("numbers") / filename
                return file_path if file_path.exists() else None
        return None
    
    @classmethod
    def load_verif(cls) -> Dict:
        return cls.load_db("verif")
    
    @classmethod
    def add_verification(cls, verif_id: str, link: str, group_id: str = ""):
        data = cls.load_verif()
        data[verif_id] = {"link": link, "id": group_id}
        cls.save_db("verif", data)
    
    @classmethod
    def remove_verification(cls, verif_id: str) -> bool:
        data = cls.load_verif()
        if verif_id in data:
            del data[verif_id]
            cls.save_db("verif", data)
            return True
        return False
    
    @classmethod
    def check_sms_history(cls, phone: str, datetime_str: str) -> bool:
        history = cls.load_db("sms_history")
        if not isinstance(history, list):
            history = []
        
        sms_id = f"{phone}_{datetime_str}"
        if sms_id in history:
            return True
        
        history.append(sms_id)
        cls.save_db("sms_history", history)
        cls.cleanup_sms_history()
        return False
    
    @classmethod
    def get_autodel_setting(cls) -> Dict:
        data = cls.load_db("autodel")
        if isinstance(data, dict):
            return data
        else:
            return {"enabled": False, "minutes": 0, "notif_message_ids": {}}
    
    @classmethod
    def set_autodel_setting(cls, minutes: int, notif_message_ids: Dict = None):
        if notif_message_ids is None:
            notif_message_ids = {}
        data = {"enabled": minutes > 0, "minutes": minutes, "notif_message_ids": notif_message_ids}
        cls.save_db("autodel", data)
    
    @classmethod
    def add_bot_message(cls, group_id: str, message_id: int):
        data = cls.load_db("bot_messages")
        if not isinstance(data, list):
            data = []
        
        data.append({
            "group_id": group_id,
            "message_id": message_id,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
        cls.save_db("bot_messages", data)
    
    @classmethod
    def get_old_bot_messages(cls, older_than_minutes: int) -> List[Dict]:
        data = cls.load_db("bot_messages")
        if not isinstance(data, list):
            return []
        
        now = datetime.now(timezone.utc)
        old_messages = []
        for msg in data:
            try:
                timestamp = datetime.fromisoformat(msg["timestamp"])
                if (now - timestamp).total_seconds() > older_than_minutes * 60:
                    old_messages.append(msg)
            except:
                pass
        
        return old_messages
    
    @classmethod
    def remove_bot_message(cls, group_id: str, message_id: int):
        data = cls.load_db("bot_messages")
        if not isinstance(data, list):
            return
        
        new_data = [m for m in data if not (m["group_id"] == group_id and m["message_id"] == message_id)]
        if len(new_data) != len(data):
            cls.save_db("bot_messages", new_data)

class Utils:
    @staticmethod
    def extract_otp(message: str) -> str:
        patterns = [
            re.compile(r'(?:kode|code|otp|pin|verification)[\s:]*([0-9]{3,8}(?:[- ][0-9]{3,8})?)', re.IGNORECASE),
            re.compile(r'(?:adalah|is|use|gunakan)[\s:]*([0-9]{3,8}(?:[- ][0-9]{3,8})?)', re.IGNORECASE),
            re.compile(r'(?::\s*|\/|\*)?([0-9]{3,8}(?:[- ][0-9]{3,8})?)(?:\.|,|$)'),
            re.compile(r'\b([0-9]{3,8}(?:[- ][0-9]{3,8})?)\b'),
            re.compile(r'#\s*([0-9]{3,8}(?:[- ][0-9]{3,8})?)')
        ]
        
        for pattern in patterns:
            match = pattern.search(message)
            if match and match[1]:
                return match[1].replace(' ', '-')
        
        dash_pattern = re.compile(r'\b(\d{3,8}[- ]\d{3,8})\b')
        dash_match = dash_pattern.search(message)
        if dash_match and dash_match[1]:
            return dash_match[1].replace(' ', '-')
        
        all_numbers = re.findall(r'\b\d{3,8}\b', message)
        if all_numbers and len(all_numbers) > 0:
            for i in range(len(all_numbers) - 1, -1, -1):
                num = all_numbers[i]
                if 3 <= len(num) <= 8:
                    return num
        
        return 'N/A'
    
    @staticmethod
    def mask_phone(phone: str) -> str:
        if len(phone) >= 8:
            return f"{phone[:4]}•DzD•{phone[-4:]}"
        return phone
    
    @staticmethod
    def escape_html(text: str) -> str:
        return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    
    @staticmethod
    def get_service_abbr(service: str) -> str:
        service_lower = service.lower()
        if "whatsapp" in service_lower or "wa" in service_lower:
            return "WS"
        elif "telegram" in service_lower or "tg" in service_lower:
            return "TG"
        elif "facebook" in service_lower or "fb" in service_lower:
            return "FB"
        elif "google" in service_lower or "gmail" in service_lower:
            return "GG"
        elif "instagram" in service_lower or "ig" in service_lower:
            return "IG"
        elif "twitter" in service_lower or "x" in service_lower:
            return "TW"
        else:
            return service[:2].upper() if len(service) >= 2 else "SV"
    
    @staticmethod
    def extract_numbers_from_file(file_content: str) -> List[str]:
        numbers = []
        for line in file_content.split('\n'):
            line = line.strip()
            if not line:
                continue
            
            phone_matches = re.findall(r'\b\d{10,15}\b', line)
            for phone in phone_matches:
                numbers.append(phone)
        
        return list(set(numbers))
    
    @staticmethod
    def extract_numbers_from_text(text: str) -> List[str]:
        numbers = re.findall(r'\b\d{10,15}\b', text)
        return list(set(numbers))

class OTPReceiver:
    def __init__(self, config: Config):
        self.config = config
        self.URL = "https://api.iprn-elite.com/v1.0/json"
        self.last_seen_id = None
    
    def get_sms(self):
        API_KEY = self.config.APIKEY
        
        headers = {
            "Content-Type": "application/json",
            "Api-Key": API_KEY
        }
        
        from datetime import timezone
        now = datetime.now(timezone.utc)
        start_time = (now - timedelta(hours=1)).strftime('%Y-%m-%dT%H:%M:%S.000Z')
        end_time = now.strftime('%Y-%m-%dT%H:%M:%S.000Z')
        
        payload = {
            "jsonrpc": "2.0",
            "method": "sms.mdr_full:get_list",
            "params": {
                "filter": {
                    "start_date": start_time,
                    "end_date": end_time
                },
                "page": 1,
                "per_page": 10
            },
            "id": 1
        }
        
        try:
            response = requests.post(self.URL, headers=headers, json=payload, timeout=30)
            
            if response.status_code == 200:
                return response.json()
            else:
                print(f"Server Error {response.status_code}: {response.text}")
                return None
        except Exception as e:
            print(f"Connection Error: {e}")
            return None
    
    async def process_sms(self, bot_app):
        os.system('cls' if os.name == 'nt' else 'clear')

        print(f"{Fore.CYAN}[]═════════════════════════════════[]{Style.RESET_ALL}")
        print(f"{Fore.GREEN}[]════════[] WAITING OTPS []════════[]{Style.RESET_ALL}")
        print(f"{Fore.CYAN}[]═════════════════════════════════[]{Style.RESET_ALL}")
        
        while True:
            try:
                data = self.get_sms()
                
                if data and "result" in data:
                    sms_list = data["result"].get("mdr_full_list", [])
                    if sms_list:
                        latest_sms = sms_list[0]
                        current_id = f"{latest_sms.get('phone')}_{latest_sms.get('datetime')}"
                        
                        if current_id != self.last_seen_id:
                            if Database.check_sms_history(latest_sms.get('phone', ''), latest_sms.get('datetime', '')):
                                print(f"{Fore.YELLOW}☐ [ SMS ALREADY PROCESSED ]{Style.RESET_ALL}")
                                self.last_seen_id = current_id
                                continue
                                
                            phone = latest_sms.get('phone', '')
                            message = latest_sms.get('message', '')
                            senderid = latest_sms.get('senderid', '')
                            
                            print(f"\n{Fore.GREEN}☐ [ NEW SMS RECIEVED ]{Style.RESET_ALL}")
                            print(f"{Fore.CYAN}╰══ [] {phone} - {senderid}{Style.RESET_ALL}")
                            
                            await self.broadcast_sms(phone, message, senderid, bot_app)
                            self.last_seen_id = current_id
                
                await asyncio.sleep(10)
            except Exception as e:
                print(f"Error in SMS processing: {e}")
                await asyncio.sleep(30)
    
    async def broadcast_sms(self, phone: str, message: str, service: str, bot_app):
        try:
            otp_code = Utils.extract_otp(message)
            
            if not isinstance(phone, str):
                phone = str(phone)
            
            country_info = Database.get_country_by_code(phone)
            if country_info:
                flag = country_info.get("flag", "🌐")
                country = country_info.get("name", "Unknown")
                short_name = country_info.get("shortName", "XX")
            else:
                flag = "🌐"
                country = "Unknown"
                short_name = "XX"
            
            service_abbr = Utils.get_service_abbr(service)
            masked_phone = Utils.mask_phone(phone)
            
            from datetime import timezone
            otp_data = {
                "phone": phone,
                "message": message,
                "service": service,
                "country": country,
                "otp": otp_code,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            Database.add_otp_record(otp_data)
            
            user_message = f"""<blockquote>🚨 𝗣𝗥𝗘𝗠𝗜𝗨𝗠 𝗦𝗠𝗦 𝗥𝗘𝗖𝗜𝗘𝗩𝗘𝗗 𝗗𝘇𝗗 🚨</blockquote>

» 𝗗𝗲𝘁𝗮𝗶𝗹𝘀 : {flag} <b>{country}</b> — {service}
» 𝗡𝘂𝗺𝗯𝗲𝗿 : <code>+{phone}</code>
» 𝗠𝗲𝘀𝘀𝗮𝗴𝗲 :
<pre>{Utils.escape_html(message)}</pre>

<blockquote>﹂ 𝖳𝗁𝖺𝗇𝗄 𝗒𝗈𝗎 𝖿𝗈𝗋 𝗎𝗌𝗂𝗇𝗀 DzD 𝖻𝗈𝗍💥</blockquote>"""
            
            user_keyboard = []
            if otp_code and otp_code != 'N/A':
                try:
                    button = InlineKeyboardButton(
                        text=f"{otp_code}", 
                        copy_text=CopyTextButton(text=str(otp_code))
                    )
                    user_keyboard.append([button])
                except Exception as e:
                    button = InlineKeyboardButton(text=f"{otp_code}", callback_data="copy_otp")
                    user_keyboard.append([button])
            
            groups = Database.get_groups()
            for group_id in groups:
                try:
                    if isinstance(group_id, str) and group_id.strip():
                        sms_message = f"""
<blockquote>🚨 𝗣𝗥𝗘𝗠𝗜𝗨𝗠 𝗦𝗠𝗦 𝗥𝗘𝗖𝗜𝗘𝗩𝗘𝗗 𝗗𝘇𝗗 🚨</blockquote>
▛━━━━━━━━━━━━━━━━━━━━▜
┃  <b>{flag} #{short_name} #{service_abbr}  {masked_phone}</b>  ┃
▙━━━━━━━━━━━━━━━━━━━━▟
<blockquote><b><a href="{self.config.OWNER_LINK}">©𝗣𝗼𝘄𝗲𝗿𝗲𝗱 𝗕𝘆 𝗗𝗮𝘆𝘇𝗗𝗶𝗴𝗶𝘁𝗮𝗹 𝗢𝗳𝗳𝗶𝗰𝗶𝗮𝗹亗</a></b></blockquote>
"""
                        
                        keyboard = []
                        if otp_code and otp_code != 'N/A':
                            try:
                                button = InlineKeyboardButton(
                                    text=f"{otp_code}", 
                                    copy_text=CopyTextButton(text=str(otp_code))
                                )
                            except:
                                button = InlineKeyboardButton(text=f"{otp_code}", callback_data="copy_otp")
                            keyboard.append([button])
                        
                        row = []
                        try:
                            bot_username = (await bot_app.bot.get_me()).username
                            panel_url = f"https://t.me/{bot_username}"
                            row.append(InlineKeyboardButton("🔧 𝙿𝙰𝙽𝙴𝙻", url=panel_url))
                        except:
                            pass
                        
                        if self.config.CH_INFO:
                            row.append(InlineKeyboardButton("📢 𝙸𝙽𝙵𝙾", url=self.config.CH_INFO))
                        
                        if row:
                            keyboard.append(row)
                        
                        sent_message = await bot_app.bot.send_message(
                            chat_id=int(group_id.strip()),
                            text=sms_message,
                            parse_mode=ParseMode.HTML,
                            reply_markup=InlineKeyboardMarkup(keyboard) if keyboard else None,
                            link_preview_options=LinkPreviewOptions(is_disabled=True)
                        )
                        
                        Database.add_bot_message(group_id.strip(), sent_message.message_id)
                        
                except Exception as e:
                    print(f"Error sending to group {group_id}: {e}")
            
            user_requests = Database.get_user_requests()
            for req in user_requests:
                try:
                    numbers_list = req.get("numbers", [])
                    if isinstance(numbers_list, list) and phone in numbers_list:
                        await bot_app.bot.send_message(
                            chat_id=req["user_id"],
                            text=user_message,
                            parse_mode=ParseMode.HTML,
                            reply_markup=InlineKeyboardMarkup(user_keyboard) if user_keyboard else None,
                            link_preview_options=LinkPreviewOptions(is_disabled=True)
                        )
                except Exception as e:
                    print(f"Error sending to user {req.get('user_id', 'unknown')}: {e}")
                    
        except Exception as e:
            print(f"Error in broadcast_sms: {type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()

class BotHandler:
    def __init__(self, config: Config):
        self.config = config
        self.awaiting_input = {}
        self.user_messages_to_delete = {}
        self.otp_receiver = OTPReceiver(config)
        self.auto_delete_task = None
    
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        
        if update.effective_chat.type in ['group', 'supergroup']:
            chat_id = str(update.effective_chat.id)
            groups = Database.get_groups()
            if chat_id not in groups:
                Database.add_group(chat_id)
                try:
                    await context.bot.send_message(
                        chat_id=self.config.OWNER_ID,
                        text=f"🤖 <b>Bot added to new group!</b>\n\n"
                             f"📝 <b>Group ID:</b> <code>{chat_id}</code>\n"
                             f"👥 <b>Group Name:</b> {update.effective_chat.title}\n"
                             f"👤 <b>Added by:</b> {user.first_name} (@{user.username or 'N/A'})",
                        parse_mode=ParseMode.HTML
                    )
                except:
                    pass
            
            await update.message.reply_text(
                "<blockquote>┏━━━━━━━━━━━━━━━━━━━━━┓\n│    🤖 𝗕𝗢𝗧 𝗜𝗦 𝗢𝗡𝗟𝗜𝗡𝗘   │\n┗━━━━━━━━━━━━━━━━━━━━━┛</blockquote>",
                parse_mode=ParseMode.HTML
            )
            return
        
        Database.init_db()
        
        if user.id == self.config.OWNER_ID:
            Database.add_user(user.id, verified=True)
            await self.owner_menu(update, context)
        else:
            Database.add_user(user.id, verified=False)
            await self.check_and_verify_user(update, context, user.id)
    
    async def check_and_verify_user(self, update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int):
        verifications = Database.load_verif()
        
        if not verifications:
            Database.verify_user(user_id)
            await self.user_menu(update, context)
            return
        
        all_joined = True
        for verif_id, info in verifications.items():
            group_id = info.get('id', '')
            if group_id and group_id.startswith('-100'):
                try:
                    member = await context.bot.get_chat_member(int(group_id), user_id)
                    if member.status not in ['member', 'administrator', 'creator']:
                        all_joined = False
                        break
                except Exception:
                    all_joined = False
                    break
        
        if all_joined:
            Database.verify_user(user_id)
            await self.user_menu(update, context)
        else:
            Database.remove_from_verified(user_id)
            await self.show_verification(update, context)
    
    async def show_verification(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        verifications = Database.load_verif()
        
        message = """
    <blockquote>┏━━━━━━━━━━━━━━━━━━━━━┓
    <code>│ 🚫 ACCESS DENIED 🚫 │</code>
    ┗━━━━━━━━━━━━━━━━━━━━━┛</blockquote>
    
    ﹂ Please join our channels below to unlock access:
    """
        keyboard = []
        for verif_id, info in verifications.items():
            keyboard.append([InlineKeyboardButton(f"🔗 {verif_id}", url=info.get('link', ''))])
        
        keyboard.append([InlineKeyboardButton("🔄 Refresh", callback_data="refresh_verify")])
        
        message += f"\n<i>Developer: <a href='{self.config.OWNER_LINK}'>©𝑲𝒂𝒏𝒈𝑫𝒂𝒚𝒁亗</a></i>"
        
        if update.callback_query:
            try:
                await update.callback_query.edit_message_text(
                    message,
                    parse_mode=ParseMode.HTML,
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
            except BadRequest as e:
                if "Message is not modified" not in str(e):
                    raise
        else:
            await update.message.reply_text(
                message,
                parse_mode=ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
    
    async def refresh_verify(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        if query:
            await query.answer()
            user_id = query.from_user.id
        else:
            return
        
        verifications = Database.load_verif()
        all_joined = True
        
        for verif_id, info in verifications.items():
            group_id = info.get('id', '')
            if group_id and group_id.startswith('-100'):
                try:
                    member = await context.bot.get_chat_member(int(group_id), user_id)
                    if member.status not in ['member', 'administrator', 'creator']:
                        all_joined = False
                        break
                except Exception:
                    all_joined = False
                    break
        
        if all_joined:
            Database.verify_user(user_id)
            try:
                await query.edit_message_text("✅ <b>Verification successful! Use /start</b>", parse_mode=ParseMode.HTML)
            except BadRequest as e:
                if "Message is not modified" not in str(e):
                    raise
        else:
            Database.remove_from_verified(user_id)
            await query.answer("❌ Please join all groups first!", show_alert=True)
    
    async def user_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        username = user.username or user.first_name or "User"
        
        if update.effective_chat.type in ['group', 'supergroup']:
            return
        
        if not Database.is_verified(user.id):
            await update.message.reply_text(
                "⚠️ You need to verify first!\n"
                "Please join channel for verification.",
                parse_mode=ParseMode.HTML
            )
            return
        
        try:
            if 'last_numbers_msg_id' in context.user_data:
                try:
                    await context.bot.delete_message(
                        chat_id=update.effective_chat.id,
                        message_id=context.user_data['last_numbers_msg_id']
                    )
                    context.user_data.pop('last_numbers_msg_id', None)
                except:
                    pass
        except:
            pass
        
        message = f"""
<blockquote>𝗢𝗧𝗣𝗦 𝗫 𝗗𝘇𝗗 𝗣𝗥𝗘𝗠𝗜𝗨𝗠</blockquote>
 
( 👤 ) - Info 𝗛𝗲𝗹𝗹𝗼, @{username}
𝗞𝗶𝗹𝗹𝘂𝗮 𝗫 𝗡𝗲𝘁𝘄𝗼𝗿𝗸 ボット is a fast, flexible and secure automation tool. For digital tasks, support me!.......

<blockquote>» 𝗠𝗔𝗜𝗡 𝗠𝗘𝗡𝗨</blockquote>
• 📞 𝗚𝗲𝘁 𝗡𝘂𝗺𝗯𝗲𝗿 → Request number
• 🔒 𝗢𝗧𝗣 → OTP Group
• 🔗 𝗖𝗵𝗮𝗻𝗻𝗲𝗹 → Official channel
• ❓ 𝗛𝗲𝗹𝗽 → Contact owner/support
• 📊 𝗧𝗿𝗮𝗳𝗳𝗶𝗰 → Check OTP traffic

<b>💡 Instructions:</b>
<i>Use /fastotps and send your number max 10, for fast receive otps in inbox</i>
<blockquote>© 𝗗𝗲𝘃𝗲𝗹𝗼𝗽𝗲𝗿 <a href="{self.config.OWNER_LINK}">𝑲𝒂𝒏𝒈𝑫𝒂𝒚𝒁亗</a> </blockquote>"""
        
        keyboard = [
            [
                InlineKeyboardButton("📞 𝙶𝙴𝚃 𝙽𝚄𝙼𝙱𝙴𝚁", callback_data="get_number"),
                InlineKeyboardButton("🔒 𝙾𝚃𝙿", url=self.config.OTPS_GROUP or self.config.CH_INFO)
            ],
            [
                InlineKeyboardButton("📢 𝙲𝙷𝙰𝙽𝙽𝙴𝙻", url=self.config.CH_INFO),
                InlineKeyboardButton("❓ 𝙷𝙴𝙻𝙿", url=self.config.OWNER_LINK)
            ]
        ]
        
        if user.id == self.config.OWNER_ID:
            keyboard.append([InlineKeyboardButton("👑 OWNER MENU", callback_data="owner_menu")])
        
        if update.callback_query:
            try:
                await update.callback_query.edit_message_text(
                    text=message,
                    parse_mode=ParseMode.HTML,
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
            except BadRequest as e:
                if "Message is not modified" not in str(e):
                    raise
        else:
            sent_msg = await update.message.reply_text(
                text=message,
                parse_mode=ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            context.user_data['menu_msg_id'] = sent_msg.message_id
    
    async def get_number_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        
        ranges = Database.get_ranges()
        if not ranges:
            await query.edit_message_text(
                "❌ No number range available!",
                parse_mode=ParseMode.HTML
            )
            return
        
        message = """
<blockquote>┏━━━━━━━━━━━━━━━━━━━━━┓
│     📞 𝗦𝗘𝗟𝗘𝗖𝗧 𝗥𝗔𝗡𝗚𝗘𝗦    │
┗━━━━━━━━━━━━━━━━━━━━━┛</blockquote>

<blockquote>» 𝗣𝗹𝗲𝗮𝘀𝗲 𝗰𝗵𝗼𝗼𝘀𝗲 𝗮 𝘁𝗿𝗮𝗳𝗳𝗶𝗰 𝗳𝗼𝗿 𝗻𝘂𝗺𝗯𝗲𝗿:</blockquote>
"""
        
        keyboard = []
        
        for idx, range_data in enumerate(ranges):
            service = range_data.get("service", "Unknown")
            country = range_data.get("country", "Unknown")
            flag = range_data.get("flag", "🌐")
            service_abbr = Utils.get_service_abbr(service)[:10]
            filename = range_data.get("filename", "")
            
            try:
                if filename:
                    file_path = Path("numbers") / filename
                    if file_path.exists():
                        with open(file_path, "r", encoding="utf-8") as f:
                            lines = [l.strip() for l in f.readlines() if l.strip()]
                            available = len(lines)
                    else:
                        available = 0
                else:
                    available = 0
            except:
                available = 0
            
            button_text = f"{flag} {country} {service_abbr} ({available})"
            keyboard.append([
                InlineKeyboardButton(button_text, callback_data=f"select_range_{idx}")
            ])
        
        keyboard.append([
            InlineKeyboardButton("⬅️ 𝙱𝙰𝙲𝙺 𝙼𝙴𝙽𝚄", callback_data="back_to_menu")
        ])
        
        try:
            await query.edit_message_text(
                text=message,
                parse_mode=ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        except BadRequest as e:
            if "Message is not modified" not in str(e):
                raise
    
    async def select_range(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        
        try:
            range_idx = int(query.data.replace("select_range_", ""))
        except:
            await query.edit_message_text(
                "❌ Invalid range!",
                parse_mode=ParseMode.HTML
            )
            return
        
        ranges = Database.get_ranges()
        
        if range_idx < 0 or range_idx >= len(ranges):
            await query.edit_message_text(
                "❌ Range not found!",
                parse_mode=ParseMode.HTML
            )
            return
        
        range_data = ranges[range_idx]
        filename = range_data.get("filename", "")
        
        if not filename:
            await query.edit_message_text(
                "❌ Number file not found!",
                parse_mode=ParseMode.HTML
            )
            return
        
        file_path = Path("numbers") / filename
        
        if not file_path.exists():
            await query.edit_message_text(
                "❌ Number file not found!",
                parse_mode=ParseMode.HTML
            )
            return
        
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                numbers = [line.strip() for line in f.readlines() if line.strip()]
            
            if not numbers:
                await query.edit_message_text(
                    "❌ No numbers available!",
                    parse_mode=ParseMode.HTML
                )
                return
            
            flag = range_data.get("flag", "🌐")
            country = range_data.get("country", "Unknown")
            service = range_data.get("service", "Unknown")
            capacity = len(numbers)
            
            caption = f"""
<blockquote>𝗧𝗛𝗜𝗦 𝗡𝗨𝗠𝗕𝗘𝗥𝗦 𝗗𝗘𝗧𝗔𝗜𝗟𝗦</blockquote>
» 𝗖𝗼𝘂𝗻𝘁𝗿𝘆 : {flag}{country}
» 𝗦𝗲𝗿𝘃𝗶𝗰𝗲 : {service}
» 𝗖𝗮𝗽𝗮𝗰𝗶𝘁𝘆 : {capacity}

<blockquote><i><a href="{self.config.OTPS_GROUP}">𝗢𝗧𝗣𝗦 𝗖𝗹𝗶𝗰𝗸 𝗛𝗲𝗿𝗲 𝗙𝗿𝗶𝗲𝗻𝗱𝘀</a></i></blockquote>
"""
            
            with open(file_path, "rb") as file_to_send:
                await context.bot.send_document(
                    chat_id=query.from_user.id,
                    document=file_to_send,
                    caption=caption,
                    parse_mode=ParseMode.HTML
                )
            
            await query.edit_message_text(
                text="✅ File has been sent to private chat!",
                parse_mode=ParseMode.HTML
            )
            
        except Exception as e:
            await query.edit_message_text(
                f"❌ Error: {str(e)}",
                parse_mode=ParseMode.HTML
            )
    
    async def fastotps_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        
        if update.effective_chat.type in ['group', 'supergroup']:
            return
        
        if not Database.is_verified(user.id):
            await update.message.reply_text(
                "⚠️ You need to verify first!",
                parse_mode=ParseMode.HTML
            )
            return
        
        try:
            if 'last_numbers_msg_id' in context.user_data:
                try:
                    await context.bot.delete_message(
                        chat_id=update.effective_chat.id,
                        message_id=context.user_data['last_numbers_msg_id']
                    )
                    context.user_data.pop('last_numbers_msg_id', None)
                except:
                    pass
        except:
            pass
        
        Database.remove_user_request(user.id)
        
        try:
            if 'fastotps_request_msg_id' in context.user_data:
                try:
                    await context.bot.delete_message(
                        chat_id=user.id,
                        message_id=context.user_data['fastotps_request_msg_id']
                    )
                except:
                    pass
                context.user_data.pop('fastotps_request_msg_id', None)
        except:
            pass
        
        if user.id == self.config.OWNER_ID:
            caption = (
                "<blockquote>𝗦𝗲𝗻𝗱 𝗬𝗼𝘂𝗿 𝗻𝘂𝗺𝗯𝗲𝗿𝘀 𝗳𝗼𝗿 𝗳𝗮𝘀𝘁 𝗼𝘁𝗽𝘀</blockquote>\n\n"
                "𝙼𝚒𝚗𝚒𝚖𝚊𝚕 𝟷 𝚗𝚞𝚖𝚋𝚎𝚛𝚜 𝚊𝚗𝚍 𝚖𝚊𝚡 𝟸𝟶𝟶 𝚗𝚞𝚖𝚋𝚎𝚛𝚜\n"
                "𝙾𝚝𝚙𝚜 𝚜𝚎𝚗𝚝 𝚝𝚘 𝚢𝚘𝚞𝚛 𝚙𝚛𝚒𝚟𝚊𝚝𝚎 𝚌𝚑𝚊𝚝\n\n"
                "<blockquote>©𝗣𝗼𝘄𝗲𝗿𝗲𝗱 𝗕𝘆 𝗗𝗮𝘆𝘇𝗗𝗶𝗴𝗶𝘁𝗮𝗹 𝗢𝗳𝗳𝗶𝗰𝗶𝗮𝗹亗</blockquote>"
            )
        else:
            caption = (
                "<blockquote>𝗦𝗲𝗻𝗱 𝗬𝗼𝘂𝗿 𝗻𝘂𝗺𝗯𝗲𝗿𝘀 𝗳𝗼𝗿 𝗳𝗮𝘀𝘁 𝗼𝘁𝗽𝘀</blockquote>\n\n"
                "𝙼𝚒𝚗𝚒𝚖𝚊𝚕 𝟷 𝚗𝚞𝚖𝚋𝚎𝚛𝚜 𝚊𝚗𝚍 𝚖𝚊𝚡 𝟷𝟶 𝚗𝚞𝚖𝚋𝚎𝚛𝚜\n"
                "𝙾𝚝𝚙𝚜 𝚜𝚎𝚗𝚝 𝚝𝚘 𝚢𝚘𝚞𝚛 𝚙𝚛𝚒𝚟𝚊𝚝𝚎 𝚌𝚑𝚊𝚝\n\n"
                "<blockquote>©𝗣𝗼𝘄𝗲𝗿𝗲𝗱 𝗕𝘆 𝗗𝗮𝘆𝘇𝗗𝗶𝗴𝗶𝘁𝗮𝗹 𝗢𝗳𝗳𝗶𝗰𝗶𝗮𝗹亗</blockquote>"
            )
        
        sent_msg = await update.message.reply_text(
            caption,
            parse_mode=ParseMode.HTML
        )
        
        context.user_data['fastotps_request_msg_id'] = sent_msg.message_id
        self.awaiting_input[user.id] = "fastotps_numbers"
    
    async def process_fastotps(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        
        if user.id not in self.awaiting_input:
            return
        
        if self.awaiting_input.get(user.id) != "fastotps_numbers":
            return
        
        text = update.message.text.strip()
        
        try:
            await update.message.delete()
        except:
            pass
        
        try:
            if 'fastotps_request_msg_id' in context.user_data:
                try:
                    await context.bot.delete_message(
                        chat_id=user.id,
                        message_id=context.user_data['fastotps_request_msg_id']
                    )
                except:
                    pass
                context.user_data.pop('fastotps_request_msg_id', None)
        except:
            pass
        
        numbers = Utils.extract_numbers_from_text(text)
        
        if not numbers:
            await update.message.reply_text(
                "❌ No valid numbers found! Send 11-15 digit numbers.",
                parse_mode=ParseMode.HTML
            )
            self.awaiting_input.pop(user.id, None)
            return
        
        if user.id == self.config.OWNER_ID:
            numbers = numbers[:200]
            max_limit = 200
        else:
            numbers = numbers[:10]
            max_limit = 10
        
        if len(numbers) > max_limit:
            await update.message.reply_text(
                f"❌ Maximum limit is {max_limit} numbers!",
                parse_mode=ParseMode.HTML
            )
            self.awaiting_input.pop(user.id, None)
            return
        
        Database.remove_user_request(user.id)
        Database.add_user_request(user.id, numbers)
        self.awaiting_input.pop(user.id, None)
        
        country_counts = {}
        for num in numbers:
            country_info = Database.get_country_by_code(num)
            if country_info:
                country_name = country_info.get("name", "Unknown")
                flag = country_info.get("flag", "🌐")
                if country_name not in country_counts:
                    country_counts[country_name] = {"flag": flag, "count": 0}
                country_counts[country_name]["count"] += 1
        
        message = """
<blockquote> 📞 𝗬𝗢𝗨𝗥 𝗡𝗨𝗠𝗕𝗘𝗥𝗦</blockquote>

<blockquote>» 𝗗𝗲𝘁𝗮𝗶𝗹𝘀:</blockquote>
"""
        
        for country, info in country_counts.items():
            message += f"<b>{info['flag']} {country} ({info['count']} numbers)</b>\n"
        
        message += f"\n<blockquote>» 𝗡𝘂𝗺𝗯𝗲𝗿 𝗟𝗶𝘀𝘁 ({len(numbers)} numbers)</blockquote> \n"
        
        display_numbers = numbers[:20]
        for num in display_numbers:
            message += f"<code>+{num}</code>\n"
        
        if len(numbers) > 20:
            message += f"... and {len(numbers) - 20} more numbers\n"
        
        message += f"\n﹂ 𝖶𝖺𝗂𝗍𝗂𝗇𝗀 𝖿𝗈𝗋 𝖮𝖳𝖯 𝗂𝗇 𝗂𝗇𝖻𝗈𝗑 𝗈𝗋 𝗀𝗋𝗈𝗎𝗉..."
        
        keyboard = [
            [
                InlineKeyboardButton("🆕 𝙽𝙴𝚆 𝙽𝚄𝙼𝙱𝙴𝚁", callback_data="new_number_request"),
                InlineKeyboardButton("🔒 𝙾𝚃𝙿 𝙶𝚁𝙾𝚄𝙿", url=self.config.OTPS_GROUP)
            ]
        ]
        
        sent_msg = await update.message.reply_text(
            text=message,
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        context.user_data['last_numbers_msg_id'] = sent_msg.message_id
    
    async def new_number_request_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        user_id = query.from_user.id
        
        try:
            if 'last_numbers_msg_id' in context.user_data:
                try:
                    await context.bot.delete_message(
                        chat_id=user_id,
                        message_id=context.user_data['last_numbers_msg_id']
                    )
                except:
                    pass
                context.user_data.pop('last_numbers_msg_id', None)
        except:
            pass
        
        Database.remove_user_request(user_id)
        
        try:
            await query.delete_message()
        except:
            pass
        
        caption = (
            "<blockquote>𝗦𝗲𝗻𝗱 𝗬𝗼𝘂𝗿 𝗻𝘂𝗺𝗯𝗲𝗿𝘀 𝗳𝗼𝗿 𝗳𝗮𝘀𝘁 𝗼𝘁𝗽𝘀</blockquote>\n\n"
            "𝙼𝚒𝚗𝚒𝚖𝚊𝚕 𝟷 𝚗𝚞𝗺𝗯𝗲𝗿𝘀 𝚊𝚗𝚍 𝚖𝚊𝚡 𝟷𝟶 𝚗𝚞𝗺𝗯𝗲𝗿𝘀\n"
            "𝙾𝚝𝚙𝚜 𝚜𝚎𝚗𝚝 𝚝𝚘 𝚢𝚘𝚞𝚛 𝚙𝚛𝚒𝚟𝚊𝚝𝚎 𝚌𝚑𝚊𝚝\n\n"
            "<blockquote>©𝗣𝗼𝘄𝗲𝗿𝗲𝗱 𝗕𝘆 𝗗𝗮𝘆𝘇𝗗𝗶𝗴𝗶𝘁𝗮𝗹 𝗢𝗳𝗳𝗶𝗰𝗶𝗮𝗹亗</blockquote>"
        )
        
        sent_msg = await context.bot.send_message(
            chat_id=user_id,
            text=caption,
            parse_mode=ParseMode.HTML
        )
        context.user_data['fastotps_request_msg_id'] = sent_msg.message_id
        
        self.awaiting_input[user_id] = "fastotps_numbers"
    
    async def send_new_range_notification(self, range_data: Dict, context: ContextTypes.DEFAULT_TYPE):
        flag = range_data.get("flag", "🌐")
        country = range_data.get("country", "Unknown")
        service_name = range_data.get("service", "Unknown")
        capacity = range_data.get("count", 0)
        
        if self.config.NUM_GROUP_ID:
            try:
                message = f"""
<blockquote>🚨 𝗡𝗘𝗪 𝗦𝗧𝗢𝗖𝗞 𝗡𝗨𝗠𝗕𝗘𝗥𝗦 𝗔𝗗𝗗𝗘𝗗 🚨</blockquote>
» 𝗗𝗲𝘁𝗮𝗶𝗹𝘀 : {flag}{country}
» 𝗦𝗲𝗿𝘃𝗶𝗰𝗲 : {service_name}
» 𝗖𝗮𝗽𝗮𝗰𝗶𝘁𝘆 : {capacity}

𝗢𝗧𝗣 : {self.config.OTPS_GROUP}
𝗡𝗨𝗠 : https://t.me/{context.bot.username}?start=bot

<blockquote>𝙻𝙴𝚃 𝚂𝚃𝙰𝚁𝚃𝙴𝙳 𝚃𝙾 𝚂𝙴𝙽𝙳 𝚂𝙼𝚂 𝚃𝚁𝙰𝙵𝙵𝙸𝙲</blockquote>"""
                
                await context.bot.send_message(
                    chat_id=int(self.config.NUM_GROUP_ID),
                    text=message,
                    parse_mode=ParseMode.HTML,
                    link_preview_options=LinkPreviewOptions(is_disabled=True)
                )
            except Exception as e:
                print(f"Failed to send notification to NUM_GROUP_ID: {e}")
        
        users = Database.get_users()
        all_users = users.get("not_verif", []) + users.get("Verified", [])
        for user_id in all_users:
            try:
                message = f"""
<blockquote>🚨 𝗡𝗘𝗪 𝗦𝗧𝗢𝗖𝗞 𝗡𝗨𝗠𝗕𝗘𝗥𝗦 𝗔𝗗𝗗𝗘𝗗 🚨</blockquote>
» 𝗗𝗲𝘁𝗮𝗶𝗹𝘀 : {flag}{country}
» 𝗦𝗲𝗿𝘃𝗶𝗰𝗲 : {service_name}
» 𝗖𝗮𝗽𝗮𝗰𝗶𝘁𝘆 : {capacity}

<blockquote>𝗨𝗦𝗘 /start 𝗧𝗢 𝗚𝗘𝗧 𝗡𝗘𝗪 𝗡𝗨𝗠𝗕𝗘𝗥𝗦</blockquote>"""
                
                await context.bot.send_message(
                    chat_id=user_id,
                    text=message,
                    parse_mode=ParseMode.HTML,
                    link_preview_options=LinkPreviewOptions(is_disabled=True)
                )
            except Exception as e:
                print(f"Failed to send notification to user {user_id}: {e}")
    
    async def owner_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        
        if update.effective_chat.type in ['group', 'supergroup']:
            return
        
        username = user.username or user.first_name or "Owner"
        
        message = f"""
<blockquote>𝗢𝗧𝗣𝗦 𝗫 𝗗𝘇𝗗 𝗣𝗥𝗘𝗠𝗜𝗨𝗠</blockquote>
 
( 👤 ) - Info 𝗛𝗲𝗹𝗹𝗼, @{username}
𝗞𝗶𝗹𝗹𝘂𝗮 𝗫 𝗡𝗲𝘁𝘄𝗼𝗿𝗸 ボット is a fast, flexible and secure automation tool. For digital tasks, support me!.......

<blockquote>» 𝗢𝗪𝗡𝗘𝗥 𝗠𝗘𝗡𝗨</blockquote>
❯ 𝗦𝗬𝗦𝗧𝗘𝗠 𝗢𝗣𝗧𝗜𝗢𝗡𝗦
» 𝗥𝗮𝗻𝗴𝗲𝘀  —  Ranges Configuration
» 𝗚𝗿𝗼𝘂𝗽   —  Groups Configuration
» 𝗢𝘁𝗵𝗲𝗿𝘀  —  Other Configuration

<blockquote>© 𝗗𝗲𝘃𝗲𝗹𝗼𝗽𝗲𝗿 <a href="{self.config.OWNER_LINK}">𝑲𝒂𝒏𝒈𝑫𝒂𝒚𝒁亗</a> </blockquote>
"""
        
        keyboard = [
            [
                InlineKeyboardButton("📊 𝚁𝙰𝙽𝙶𝙴𝚂", callback_data="menu_ranges"),
                InlineKeyboardButton("👥 𝙶𝚁𝙾𝚄𝙿𝚂", callback_data="menu_groups")
            ],
            [
                InlineKeyboardButton("📈 𝚂𝚃𝙰𝚃𝙸𝚂𝚃𝙸𝙲", callback_data="statistic_menu"),
                InlineKeyboardButton("⚙️ 𝙾𝚃𝙷𝙴𝚁𝚂", callback_data="menu_other")
            ],
            [
                InlineKeyboardButton("💾 𝙱𝙰𝙲𝙺𝚄𝙿", callback_data="backup_menu")
            ]
        ]
        
        if update.callback_query:
            try:
                await update.callback_query.edit_message_text(
                    text=message,
                    parse_mode=ParseMode.HTML,
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
            except BadRequest as e:
                if "Message is not modified" not in str(e):
                    raise
        else:
            await update.message.reply_text(
                text=message,
                parse_mode=ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
    
    async def ranges_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        try:
            query = update.callback_query
            if query:
                await query.answer()
                message_func = query.edit_message_text
                chat_id = query.from_user.id
            else:
                message_func = update.message.reply_text
                chat_id = update.effective_chat.id
        except:
            message_func = update.message.reply_text
            chat_id = update.effective_chat.id
        
        ranges = Database.get_ranges()
        
        message = f"""
<blockquote>𝗢𝗧𝗣𝗦 𝗫 𝗗𝘇𝗗 𝗣𝗥𝗘𝗠𝗜𝗨𝗠</blockquote>
"""
        
        user = update.effective_user
        username = user.username or user.first_name or "Owner"
        message += f"( 👤 ) - Info 𝗛𝗲𝗹𝗹𝗼, @{username}"
        message += "<blockquote>❯ 𝗔𝗖𝗧𝗜𝗩𝗘 𝗥𝗔𝗡𝗚𝗘𝗦</blockquote>\n"
        
        services = {}
        for range_data in ranges:
            service = range_data.get("service", "Unknown")
            if service not in services:
                services[service] = []
            services[service].append(range_data)
        
        for service, service_ranges in services.items():
            message += f"\n<b>{service}</b>\n"
            for range_data in service_ranges:
                range_id = range_data.get("id", 0)
                filename = range_data.get("filename", "Unknown")
                flag = range_data.get("flag", "🌐")
                country = range_data.get("country", "Unknown")
                count = range_data.get("count", 0)
                
                message += f"<b>ID : {range_id}</b> <b>{flag}{country} {service} {count}</b>\n"
                message += f" ﹂❯ <i>{filename}</i>\n\n"
        
        keyboard = [
            [
                InlineKeyboardButton("➕ 𝙰𝙳𝙳 𝚁𝙰𝙽𝙶𝙴𝚂", callback_data="new_ranges"),
                InlineKeyboardButton("🗑️ 𝙳𝙴𝙻𝙴𝚃𝙴", callback_data="delete_ranges")
            ],
            [
                InlineKeyboardButton("⬅️ 𝙱𝙰𝙲𝙺", callback_data="owner_menu")
            ]
        ]
        
        await message_func(
            text=message,
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    async def new_ranges_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        
        await query.edit_message_text(
            "📤 <b>Please send the .txt file containing numbers.</b>\n"
            "Format content: just numbers or mixed text (I will filter valid numbers).",
            parse_mode=ParseMode.HTML
        )
        
        self.awaiting_input[query.from_user.id] = "waiting_ranges_file"
    
    async def process_ranges_file(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        
        if user.id not in self.awaiting_input:
            return
        
        if self.awaiting_input.get(user.id) != "waiting_ranges_file":
            return
        
        try:
            if not update.message.document:
                await update.message.reply_text("❌ Send .txt file!")
                self.awaiting_input.pop(user.id, None)
                return
            
            file = await update.message.document.get_file()
            file_content = (await file.download_as_bytearray()).decode('utf-8')
            
            numbers = Utils.extract_numbers_from_file(file_content)
            if not numbers:
                await update.message.reply_text("❌ No valid numbers found! Make sure file contains 11-15 digit numbers.")
                self.awaiting_input.pop(user.id, None)
                return
            
            first_number = numbers[0]
            country_info = Database.get_country_by_code(first_number)
            
            if not country_info:
                await update.message.reply_text(
                    "❌ Country not recognized for this number!\n"
                    "Add country code in database/country.json"
                )
                self.awaiting_input.pop(user.id, None)
                return
            
            self.awaiting_input[user.id] = "waiting_service_name"
            context.user_data['new_range_numbers'] = numbers
            context.user_data['new_range_country'] = country_info
            
            await update.message.reply_text(
                f"📍 Country: {country_info['flag']} {country_info['name']}\n"
                f"📱 Found {len(numbers)} valid numbers\n"
                "📝 Send service name (example: WhatsApp, Facebook, Telegram):"
            )
            
        except Exception as e:
            await update.message.reply_text(f"❌ Error: {str(e)}")
            self.awaiting_input.pop(user.id, None)
    
    async def process_service_name(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        
        if user.id not in self.awaiting_input:
            return
        
        if self.awaiting_input.get(user.id) != "waiting_service_name":
            return
        
        service_name = update.message.text.strip()
        
        numbers = context.user_data.get('new_range_numbers', [])
        country_info = context.user_data.get('new_range_country', {})
        
        if not numbers or not country_info:
            await update.message.reply_text("❌ Incomplete data!")
            self.awaiting_input.pop(user.id, None)
            return
        
        flag = country_info.get("flag", "🌐")
        country = country_info.get("name", "Unknown")
        short_name = country_info.get("shortName", "XX")
        country_code = country_info.get("code", "XX")
        
        ranges = Database.get_ranges()
        range_id = len(ranges) + 1
        
        filename = f"{flag}{country}_{service_name}_{len(numbers)}.txt"
        safe_filename = f"{country_code}_{service_name}_{len(numbers)}.txt"
        
        file_path = Path("numbers") / safe_filename
        
        with open(file_path, "w", encoding="utf-8") as f:
            f.write("\n".join(numbers))
        
        range_data = {
            "id": range_id,
            "filename": safe_filename,
            "display_filename": filename,
            "country": country,
            "flag": flag,
            "service": service_name,
            "short_name": short_name,
            "country_code": country_code,
            "count": len(numbers),
            "path": f"numbers/{safe_filename}",
            "created_at": datetime.now().isoformat()
        }
        
        Database.add_range(range_data)
        
        self.awaiting_input.pop(user.id, None)
        if 'new_range_numbers' in context.user_data:
            context.user_data.pop('new_range_numbers', None)
        if 'new_range_country' in context.user_data:
            context.user_data.pop('new_range_country', None)
        
        success_msg = f"""✅ <b>New range added successfully!</b>

📊 <b>Details:</b>
• Country: {flag} {country}
• Service: {service_name}
• Numbers: {len(numbers)}
• File: {safe_filename}

<blockquote>📢 Notification sent to all users!</blockquote>"""
        
        await update.message.reply_text(
            success_msg,
            parse_mode=ParseMode.HTML
        )
        
        await self.send_new_range_notification(range_data, context)
        
        await self.ranges_menu(update, context)
    
    async def delete_ranges_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        
        ranges = Database.get_ranges()
        
        keyboard = []
        for idx, range_data in enumerate(ranges):
            service = range_data.get("service", "Unknown")
            country = range_data.get("country", "Unknown")
            flag = range_data.get("flag", "🌐")
            keyboard.append([InlineKeyboardButton(
                f"🗑 {flag} {service} ({country})", 
                callback_data=f"del_range_{idx}"
            )])
        
        keyboard.append([InlineKeyboardButton("⬅️ 𝙱𝙰𝙲𝙺", callback_data="menu_ranges")])
        
        await query.edit_message_text(
            "👇 <b>Select Range to Delete:</b>",
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    async def delete_range_confirm(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        try:
            range_idx = int(query.data.replace("del_range_", ""))
        except:
            await query.answer("❌ Range not found!", show_alert=True)
            return
        
        if Database.remove_range(range_idx):
            await query.answer("✅ Range deleted!", show_alert=True)
        else:
            await query.answer("❌ Range not found!", show_alert=True)
        
        await self.ranges_menu(update, context)
    
    async def groups_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        user = update.effective_user
        username = user.username or user.first_name or "User"
        groups = Database.get_groups()
        
        message = f"""
<blockquote>𝗢𝗧𝗣𝗦 𝗫 𝗗𝘇𝗗 𝗣𝗥𝗘𝗠𝗜𝗨𝗠</blockquote>
 
( 👤 ) - Info 𝗛𝗲𝗹𝗹𝗼, @{username}
𝗞𝗶𝗹𝗹𝘂𝗮 𝗫 𝗡𝗲𝘁𝘄𝗼𝗿𝗸 ボット is a fast, flexible and secure automation tool. For digital tasks, support me!.......

<blockquote>❯ 𝗔𝗖𝗧𝗜𝗩𝗘 𝗚𝗥𝗢𝗨𝗣𝗦</blockquote>
"""
        
        if not groups:
            message += "\n<i>No active groups yet.</i>\n"
        else:
            for group_id in groups:
                try:
                    chat = await context.bot.get_chat(int(group_id))
                    message += f"\n» 𝗜𝗗: <code>{group_id}</code>\n"
                    message += f"» 𝗡𝗮𝗺𝗲: <b>{chat.title}</b>\n"
                except Exception:
                    Database.remove_group(str(group_id))
        
        message += f"""
<blockquote>© 𝗗𝗲𝘃𝗲𝗹𝗼𝗽𝗲𝗿 <a href="{self.config.OWNER_LINK}">𝑲𝒂𝒏𝒈𝑫𝒂𝒚𝒁亗</a> </blockquote>
"""
        
        bot_info = await context.bot.get_me()
        invite_url = f"https://t.me/{bot_info.username}?startgroup=true"
        
        keyboard = [
            [InlineKeyboardButton("➕ 𝙰𝙳𝙳 𝙶𝚁𝙾𝚄𝙿", url=invite_url),
            InlineKeyboardButton("🗑️ 𝙳𝙴𝙻𝙴𝚃𝙴 ", callback_data="delete_groups")],
            [InlineKeyboardButton("⬅️ 𝙱𝙰𝙲𝙺", callback_data="owner_menu")]
        ]
        
        try:
            await query.edit_message_text(
                text=message,
                parse_mode=ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        except BadRequest as e:
            if "Message is not modified" not in str(e):
                raise
    
    async def delete_groups_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        
        groups = Database.get_groups()
        
        message = "<blockquote>❯ 𝗗𝗘𝗟𝗘𝗧𝗘 𝗚𝗥𝗢𝗨𝗣𝗦</blockquote>\n\n"
        
        for group_id in groups:
            try:
                chat = await context.bot.get_chat(int(group_id))
                message += f"» 𝗜𝗗: <code>{group_id}</code>\n"
                message += f"» 𝗡𝗮𝗺𝗲: <b>{chat.title}</b>\n\n"
            except:
                message += f"» 𝗜𝗗: <code>{group_id}</code>\n"
                message += f"» 𝗡𝗮𝗺𝗲: <i>Unknown Chat</i>\n\n"
        
        message += "\n﹂ 𝗦𝗲𝗻𝗱 𝘁𝗵𝗲 𝗚𝗿𝗼𝘂𝗽 𝗜𝗗 𝘆𝗼𝘂 𝘄𝗮𝗻𝘁 𝘁𝗼 𝗱𝗲𝗹𝗲𝘁𝗲:"
        
        user_id = query.from_user.id
        self.awaiting_input[user_id] = 'delete_group_input'
        
        sent_msg = await query.edit_message_text(message, parse_mode=ParseMode.HTML)
        self.user_messages_to_delete[user_id] = sent_msg.message_id
    
    async def process_group_delete(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        text = update.message.text.strip()
        
        if user_id not in self.awaiting_input:
            return
        
        if self.awaiting_input.get(user_id) != 'delete_group_input':
            return
        
        try:
            await update.message.delete()
            
            if user_id in self.user_messages_to_delete:
                try:
                    await context.bot.delete_message(
                        chat_id=user_id,
                        message_id=self.user_messages_to_delete[user_id]
                    )
                    self.user_messages_to_delete.pop(user_id, None)
                except:
                    pass
            
            if Database.remove_group(text):
                await update.message.reply_text("✅ 𝗚𝗿𝗼𝘂𝗽 𝗦𝘂𝗰𝗰𝗲𝘀𝘀𝗳𝘂𝗹𝗹𝘆 𝗗𝗲𝗹𝗲𝘁𝗲𝗱!", parse_mode=ParseMode.HTML)
                try:
                    await context.bot.leave_chat(int(text))
                except:
                    pass
            else:
                await update.message.reply_text("❌ 𝗚𝗿𝗼𝘂𝗽 𝗡𝗼𝘁 𝗙𝗼𝘂𝗻𝗱!", parse_mode=ParseMode.HTML)
            
            self.awaiting_input.pop(user_id, None)
            await self.groups_menu(update, context)
            
        except Exception as e:
            await update.message.reply_text(f"❌ <b>Error:</b> <code>{str(e)}</code>", parse_mode=ParseMode.HTML)
            self.awaiting_input.pop(user_id, None)
            if user_id in self.user_messages_to_delete:
                self.user_messages_to_delete.pop(user_id, None)
    
    async def statistic_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        
        stats = Database.get_all_time_stats()
        users = Database.get_users()
        total_numbers = Database.get_total_numbers()
        total_users = len(users.get("not_verif", [])) + len(users.get("Verified", []))
        verified_users = len(users.get("Verified", []))
        
        today_stats = Database.get_traffic_for_days(1)
        
        message = f"""
<blockquote>𝗢𝗧𝗣𝗦 𝗫 𝗗𝘇𝗗 𝗣𝗥𝗘𝗠𝗜𝗨𝗠</blockquote>
 
( 👤 ) - Info 𝗛𝗲𝗹𝗹𝗼, @{query.from_user.username or query.from_user.first_name}
𝗞𝗶𝗹𝗹𝘂𝗮 𝗫 𝗡𝗲𝘁𝘄𝗼𝗿𝗸 ボット is a fast, flexible and secure automation tool. For digital tasks, support me!.......

<blockquote>» 𝗦𝗧𝗔𝗧𝗜𝗦𝗧𝗜𝗖𝗦 𝗠𝗘𝗡𝗨</blockquote>

<blockquote>📊 𝗦𝗧𝗔𝗧𝗜𝗦𝗧𝗜𝗖𝗦 (𝗔𝗟𝗟 𝗧𝗜𝗠𝗘)</blockquote>

<b>📨 All Time OTPs: <i>{stats['total']}</i>
🌍 Total Countries: <i>{len(stats['countries'])}</i>
📱 Total Numbers: <i>{total_numbers}</i>
👥 Total Users: <i>{total_users}</i>
✅ Verified Users: <i>{verified_users}</i></b>

<blockquote>🚀 𝗧𝗢𝗗𝗔𝗬'𝗦 𝗧𝗥𝗔𝗙𝗙𝗜𝗖</blockquote>\n
"""
        
        if today_stats['countries']:
            sorted_traffic = sorted(today_stats['countries'].items(), key=lambda x: x[1], reverse=True)
            for country, count in sorted_traffic[:10]:
                message += f"• <b>{country}: </b><i>{count} sms</i>\n"
        else:
            message += "<i>No traffic today yet.</i>\n"
        
        keyboard = [
            [InlineKeyboardButton("⬅️ 𝙱𝙰𝙲𝙺", callback_data="owner_menu")]
        ]
        
        try:
            await query.edit_message_text(
                text=message,
                parse_mode=ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        except BadRequest as e:
            if "Message is not modified" not in str(e):
                raise
    
    async def other_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        
        if update.effective_chat.type in ['group', 'supergroup']:
            return
            
        username = user.username or user.first_name or "User"
        message = f"""
<blockquote>𝗢𝗧𝗣𝗦 𝗫 𝗗𝘇𝗗 𝗣𝗥𝗘𝗠𝗜𝗨𝗠</blockquote>
 
( 👤 ) - Info 𝗛𝗲𝗹𝗹𝗼, @{username}
𝗞𝗶𝗹𝗹𝘂𝗮 𝗫 𝗡𝗲𝘁𝘄𝗼𝗿𝗸 ボット is a fast, flexible and secure automation tool. For digital tasks, support me!.......

<blockquote>» 𝗢𝗪𝗡𝗘𝗥 𝗖𝗢𝗠𝗠𝗔𝗡𝗗𝗦</blockquote>

/setchlink - Set channel info link
/setownerlink - Set owner link  
/setsupportlink - Set support link
/setotpslink - Set OTP group link
/groupnumid - Set number group ID
/autodelmsg - Auto delete old messages
/verification - Manage user verification
/cfd - Broadcast message to all users
/fwd - Forward message to all users

<blockquote>» 𝗨𝗦𝗘𝗥 𝗖𝗢𝗠𝗠𝗔𝗡𝗗𝗦</blockquote>
/start - Start the bot
/fastotps - Fast OTPs for numbers
/traffic - Check OTP traffic (today)

<blockquote>© 𝗗𝗲𝘃𝗲𝗹𝗼𝗽𝗲𝗿 <a href="{self.config.OWNER_LINK}">𝑲𝒂𝒏𝒈𝑫𝒂𝒚𝒁亗</a> </blockquote>
"""
        
        keyboard = [
            [InlineKeyboardButton("🔐 𝚅𝙴𝚁𝙸𝙵𝙸𝙲𝙰𝚃𝙸𝙾𝙽", callback_data="menu_verification")],
            [InlineKeyboardButton("⬅️ 𝙱𝙰𝙲𝙺", callback_data="owner_menu")]
        ]
        
        if update.callback_query:
            try:
                await update.callback_query.edit_message_text(message, parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(keyboard))
            except BadRequest as e:
                if "Message is not modified" not in str(e):
                    raise
        else:
            await update.message.reply_text(message, parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(keyboard))
    
    async def verification_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        verifications = Database.load_verif()
        
        message = "<blockquote>❯ 𝗨𝗦𝗘𝗥 𝗩𝗘𝗥𝗜𝗙𝗜𝗖𝗔𝗧𝗜𝗢𝗡</blockquote>\n\n"
        
        counter = 1
        for verif_id, info in verifications.items():
            group_id = info.get('id', '')
            link = info.get('link', '')
            message += f"{counter}. » 𝗜𝗗: <code>{group_id}</code>\n"
            message += f"   » 𝗟𝗶𝗻𝗸: {link}\n\n"
            counter += 1
        
        if not verifications:
            message += "<i>No verification data available.</i>\n\n"
            
        message += "﹂ 𝖲𝖾𝗅𝖾𝖼𝗍 𝖺𝗇 𝖺𝖼𝗍𝗂𝗈𝗇 𝖻𝖾𝗅𝗈𝗐:"
        
        keyboard = [
            [InlineKeyboardButton("➕ 𝙰𝙳𝙳 𝚅𝙴𝚁𝙸𝙵", callback_data="new_verif")],
            [InlineKeyboardButton("🗑️ 𝙳𝙴𝙻𝙴𝚃𝙴 𝚅𝙴𝚁𝙸𝙵", callback_data="del_verif")],
            [InlineKeyboardButton("⬅️ 𝙱𝙰𝙲𝙺", callback_data="menu_other")]
        ]

        try:
            await update.callback_query.edit_message_text(
                text=message,
                parse_mode=ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        except BadRequest as e:
            if "Message is not modified" not in str(e):
                raise
    
    async def new_verif_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        self.awaiting_input[user_id] = 'new_verif_link'
        
        sent_msg = await query.edit_message_text(
            "» 𝗦𝗲𝗻𝗱 𝘁𝗵𝗲 𝗚𝗿𝗼𝘂𝗽 𝗟𝗶𝗻𝗸 𝗳𝗼𝗿 𝘃𝗲𝗿𝗶𝗳𝗶𝗰𝗮𝘁𝗶𝗼𝗻:\n"
            "﹂ 𝖤𝗑𝖺𝗆𝗉𝗅𝖾: <code>https://t.me/yourgroup</code>", 
            parse_mode=ParseMode.HTML)

        self.user_messages_to_delete[user_id] = sent_msg.message_id
    
    async def del_verif_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        
        verifications = Database.load_verif()
        
        message = "<blockquote>❯ 𝗗𝗘𝗟𝗘𝗧𝗘 𝗩𝗘𝗥𝗜𝗙𝗜𝗖𝗔𝗧𝗜𝗢𝗡</blockquote>\n\n"
        
        counter = 1
        for verif_id, info in verifications.items():
            group_id = info.get('id', '')
            link = info.get('link', '')
            message += f"{counter}. » 𝗜𝗗: <code>{group_id}</code>\n"
            message += f"   » 𝗟𝗶𝗻𝗸: {link}\n\n"
            counter += 1
   
        message += "﹂ 𝗦𝗲𝗻𝗱 𝘁𝗵𝗲 𝗚𝗿𝗼𝘂𝗽 𝗜𝗗 𝘆𝗼𝘂 𝘄𝗮𝗻𝘁 𝘁𝗼 𝗱𝗲𝗹𝗲𝘁𝗲:"

        
        user_id = query.from_user.id
        self.awaiting_input[user_id] = 'del_verif_id'
        
        sent_msg = await query.edit_message_text(message, parse_mode=ParseMode.HTML)
        self.user_messages_to_delete[user_id] = sent_msg.message_id
    
    async def process_verif_input(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        text = update.message.text.strip()
        
        if user_id not in self.awaiting_input:
            return
        
        action = self.awaiting_input.get(user_id)
        
        try:
            await update.message.delete()
            
            if user_id in self.user_messages_to_delete:
                try:
                    await context.bot.delete_message(
                        chat_id=user_id,
                        message_id=self.user_messages_to_delete[user_id]
                    )
                    self.user_messages_to_delete.pop(user_id, None)
                except:
                    pass
            
            if action == 'new_verif_link':
                if not text.startswith('http'):
                    await update.message.reply_text("❌ <b>Invalid link! Must start with http/https</b>", parse_mode=ParseMode.HTML)
                    self.awaiting_input.pop(user_id, None)
                    return
                
                context.user_data['verif_link'] = text
                self.awaiting_input[user_id] = 'new_verif_id'
                
                sent_msg = await update.message.reply_text(
                    "» 𝗦𝗲𝗻𝗱 𝘁𝗵𝗲 𝗚𝗿𝗼𝘂𝗽 𝗜𝗗:\n"
                    "﹂ 𝗠𝘂𝘀𝘁 𝘀𝘁𝗮𝗿𝘁 𝘄𝗶𝘁𝗵: <code>-100</code>", 
                    parse_mode=ParseMode.HTML
                )
                self.user_messages_to_delete[user_id] = sent_msg.message_id
            
            elif action == 'new_verif_id':
                link = context.user_data.get('verif_link', '')
                verif_id = f"verification {len(Database.load_verif()) + 1}"
                Database.add_verification(verif_id, link, text)
                
                if 'verif_link' in context.user_data:
                    context.user_data.pop('verif_link', None)
                
                self.awaiting_input.pop(user_id, None)
                
                await update.message.reply_text(
                    "✅ 𝗩𝗲𝗿𝗶𝗳𝗶𝗰𝗮𝘁𝗶𝗼𝗻 𝗔𝗱𝗱𝗲𝗱 𝗦𝘂𝗰𝗰𝗲𝘀𝘀𝗳𝘂𝗹𝗹𝘆!\n"
                    "﹂ 𝗣𝗹𝗲𝗮𝘀𝗲 𝗮𝗱𝗱 𝘁𝗵𝗲 𝗯𝗼𝘁 𝗮𝘀 𝗔𝗱𝗺𝗶𝗻 𝗶𝗻 𝘁𝗵𝗮𝘁 𝗴𝗿𝗼𝘂𝗽.", 
                    parse_mode=ParseMode.HTML
                )
                await self.verification_menu(update, context)
            
            elif action == 'del_verif_id':
                if Database.remove_verification(text):
                    await update.message.reply_text("✅ 𝗩𝗲𝗿𝗶𝗳𝗶𝗰𝗮𝘁𝗶𝗼𝗻 𝗦𝘂𝗰𝗰𝗲𝘀𝘀𝗳𝘂𝗹𝗹𝘆 𝗗𝗲𝗹𝗲𝘁𝗲𝗱!", parse_mode=ParseMode.HTML)
                else:
                    await update.message.reply_text("❌ 𝗜𝗗 𝗡𝗼𝘁 𝗙𝗼𝘂𝗻𝗱!", parse_mode=ParseMode.HTML)
                
                self.awaiting_input.pop(user_id, None)
                await self.verification_menu(update, context)
                
        except Exception as e:
            await update.message.reply_text(f"❌ <b>Error:</b> <code>{str(e)}</code>", parse_mode=ParseMode.HTML)
            self.awaiting_input.pop(user_id, None)
            if user_id in self.user_messages_to_delete:
                self.user_messages_to_delete.pop(user_id, None)
    
    async def backup_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        
        user = query.from_user
        username = user.username or user.first_name or "User"
        
        message = f"""
<blockquote>𝗢𝗧𝗣𝗦 𝗫 𝗗𝘇𝗗 𝗣𝗥𝗘𝗠𝗜𝗨𝗠</blockquote>
 
( 👤 ) - Info 𝗛𝗲𝗹𝗹𝗼, @{username}
𝗞𝗶𝗹𝗹𝘂𝗮 𝗫 𝗡𝗲𝘁𝘄𝗼𝗿𝗸 ボット is a fast, flexible and secure automation tool. For digital tasks, support me!.......

<blockquote>❯ 𝗕𝗔𝗖𝗞𝗨𝗣 & 𝗥𝗘𝗦𝗧𝗢𝗥𝗘 𝗠𝗘𝗡𝗨</blockquote>

» 𝗔𝗩𝗔𝗜𝗟𝗔𝗕𝗟𝗘 𝗖𝗢𝗠𝗠𝗔𝗡𝗗𝗦:
• /backupdb - Backup database
• /backupnum - Backup numbers
• /restoredb - Restore database
• /restorenum - Restore numbers

<blockquote>© 𝗗𝗲𝘃𝗲𝗹𝗼𝗽𝗲𝗿 <a href="{self.config.OWNER_LINK}">𝑲𝒂𝒏𝒈𝑫𝒂𝒚𝒁亗</a> </blockquote>
"""
        
        keyboard = [[InlineKeyboardButton("⬅️ 𝙱𝙰𝙲𝙺", callback_data="owner_menu")]]
        
        await query.edit_message_text(
            text=message,
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    async def backupdb_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if update.effective_user.id != self.config.OWNER_ID:
            await update.message.reply_text("<blockquote>𝗣𝗹𝗲𝗮𝘀𝗲 𝘀𝗲𝗻𝗱 𝗮 𝘃𝗮𝗹𝗶𝗱 𝗰𝗼𝗺𝗺𝗮𝗻𝗱</blockquote>", parse_mode=ParseMode.HTML)
            return
        
        try:
            date_str = datetime.now().strftime("%Y%m%d_%H%M%S")
            zip_filename = f"backup_db_{date_str}.zip"
            
            with zipfile.ZipFile(zip_filename, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for file_path in Path("database").glob("*.json"):
                    zipf.write(file_path, f"database/{file_path.name}")
            
            with open(zip_filename, 'rb') as f:
                await update.message.reply_document(
                    document=f,
                    caption=f"📦 <b>Database Backup</b>\n"
                           f"⏰ <i>{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</i>\n\n"
                           f"<blockquote>©𝗣𝗼𝘄𝗲𝗿𝗲𝗱 𝗕𝘆 𝗗𝗮𝘆𝘇𝗗𝗶𝗴𝗶𝘁𝗮𝗹 𝗢𝗳𝗳𝗶𝗰𝗶𝗰𝗶𝗮𝗹亗</blockquote>",
                    parse_mode=ParseMode.HTML
                )
            
            os.remove(zip_filename)
            
        except Exception as e:
            await update.message.reply_text(f"❌ <b>Backup failed:</b> <code>{str(e)}</code>", parse_mode=ParseMode.HTML)
    
    async def backupnum_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if update.effective_user.id != self.config.OWNER_ID:
            await update.message.reply_text("<blockquote>𝗣𝗹𝗲𝗮𝘀𝗲 𝘀𝗲𝗻𝗱 𝗮 𝘃𝗮𝗹𝗶𝗱 𝗰𝗼𝗺𝗺𝗮𝗻𝗱</blockquote>", parse_mode=ParseMode.HTML)
            return
        
        try:
            date_str = datetime.now().strftime("%Y%m%d_%H%M%S")
            zip_filename = f"backup_numbers_{date_str}.zip"
            
            with zipfile.ZipFile(zip_filename, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for file_path in Path("numbers").glob("*.txt"):
                    zipf.write(file_path, f"numbers/{file_path.name}")
            
            with open(zip_filename, 'rb') as f:
                await update.message.reply_document(
                    document=f,
                    caption=f"📦 <b>Numbers Backup</b>\n"
                           f"⏰ <i>{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</i>\n\n"
                           f"<blockquote>©𝗣𝗼𝘄𝗲𝗿𝗲𝗱 𝗕𝘆 𝗗𝗮𝘆𝘇𝗗𝗶𝗴𝗶𝘁𝗮𝗹 𝗢𝗳𝗳𝗶𝗰𝗶𝗮𝗹亗</blockquote>",
                    parse_mode=ParseMode.HTML
                )
            
            os.remove(zip_filename)
            
        except Exception as e:
            await update.message.reply_text(f"❌ <b>Backup failed:</b> <code>{str(e)}</code>", parse_mode=ParseMode.HTML)
    
    async def restoredb_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if update.effective_user.id != self.config.OWNER_ID:
            await update.message.reply_text("<blockquote>𝗣𝗹𝗲𝗮𝘀𝗲 𝘀𝗲𝗻𝗱 𝗮 𝘃𝗮𝗹𝗶𝗱 𝗰𝗼𝗺𝗺𝗮𝗻𝗱</blockquote>", parse_mode=ParseMode.HTML)
            return
        
        if not update.message.reply_to_message or not update.message.reply_to_message.document:
            await update.message.reply_text("📝 <b>Reply to a .zip backup file!</b>", parse_mode=ParseMode.HTML)
            return
        
        try:
            await update.message.reply_text("🔄 <b>Processing restore...</b>", parse_mode=ParseMode.HTML)
            
            file = await update.message.reply_to_message.document.get_file()
            temp_file = f"temp_restore_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"
            await file.download_to_drive(temp_file)
            
            with zipfile.ZipFile(temp_file, 'r') as zipf:
                zipf.extractall(".")
            
            os.remove(temp_file)
            
            await update.message.reply_text(
                "✅ <b>Database restored successfully!</b>\n"
                "🔄 <i>Bot will reload database...</i>",
                parse_mode=ParseMode.HTML
            )
            
        except Exception as e:
            await update.message.reply_text(f"❌ <b>Restore failed:</b> <code>{str(e)}</code>", parse_mode=ParseMode.HTML)
    
    async def restorenum_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if update.effective_user.id != self.config.OWNER_ID:
            await update.message.reply_text("<blockquote>𝗣𝗹𝗲𝗮𝘀𝗲 𝘀𝗲𝗻𝗱 𝗮 𝘃𝗮𝗹𝗶𝗱 𝗰𝗼𝗺𝗺𝗮𝗻𝗱</blockquote>", parse_mode=ParseMode.HTML)
            return
        
        if not update.message.reply_to_message or not update.message.reply_to_message.document:
            await update.message.reply_text("📝 <b>Reply to a .zip backup file!</b>", parse_mode=ParseMode.HTML)
            return
        
        try:
            await update.message.reply_text("🔄 <b>Processing restore...</b>", parse_mode=ParseMode.HTML)
            
            file = await update.message.reply_to_message.document.get_file()
            temp_file = f"temp_restore_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"
            await file.download_to_drive(temp_file)
            
            with zipfile.ZipFile(temp_file, 'r') as zipf:
                zipf.extractall(".")
            
            os.remove(temp_file)
            
            await update.message.reply_text(
                "✅ <b>Numbers restored successfully!</b>\n"
                "🔄 <i>Bot will reload numbers...</i>",
                parse_mode=ParseMode.HTML
            )
            
        except Exception as e:
            await update.message.reply_text(f"❌ <b>Restore failed:</b> <code>{str(e)}</code>", parse_mode=ParseMode.HTML)
    
    async def setchlink_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if update.effective_user.id != self.config.OWNER_ID:
            await update.message.reply_text("<blockquote>𝗣𝗹𝗲𝗮𝘀𝗲 𝘀𝗲𝗻𝗱 𝗮 𝘃𝗮𝗹𝗶𝗱 𝗰𝗼𝗺𝗺𝗮𝗻𝗱</blockquote>", parse_mode=ParseMode.HTML)
            return
        
        if not context.args:
            await update.message.reply_text("📝 <b>Usage:</b> <code>/setchlink [url]</code>", parse_mode=ParseMode.HTML)
            return
        
        url = context.args[0]
        if not url.startswith('http'):
            await update.message.reply_text("❌ <b>URL must start with http:// or https://</b>", parse_mode=ParseMode.HTML)
            return
        
        Config.save_env('CH_INFO', url)
        await update.message.reply_text(f"✅ <b>CH_INFO updated</b>\n<code>{url}</code>", parse_mode=ParseMode.HTML)
    
    async def setownerlink_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if update.effective_user.id != self.config.OWNER_ID:
            await update.message.reply_text("<blockquote>𝗣𝗹𝗲𝗮𝘀𝗲 𝘀𝗲𝗻𝗱 𝗮 𝘃𝗮𝗹𝗶𝗱 𝗰𝗼𝗺𝗺𝗮𝗻𝗱</blockquote>", parse_mode=ParseMode.HTML)
            return
        
        if not context.args:
            await update.message.reply_text("📝 <b>Usage:</b> <code>/setownerlink [url]</code>", parse_mode=ParseMode.HTML)
            return
        
        url = context.args[0]
        if not url.startswith('http'):
            await update.message.reply_text("❌ <b>URL must start with http:// or https://</b>", parse_mode=ParseMode.HTML)
            return
        
        Config.save_env('OWNER_LINK', url)
        await update.message.reply_text(f"✅ <b>OWNER_LINK updated</b>\n<code>{url}</code>", parse_mode=ParseMode.HTML)
    
    async def setsupportlink_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if update.effective_user.id != self.config.OWNER_ID:
            await update.message.reply_text("<blockquote>𝗣𝗹𝗲𝗮𝘀𝗲 𝘀𝗲𝗻𝗱 𝗮 𝘃𝗮𝗹𝗶𝗱 𝗰𝗼𝗺𝗺𝗮𝗻𝗱</blockquote>", parse_mode=ParseMode.HTML)
            return
        
        if not context.args:
            await update.message.reply_text("📝 <b>Usage:</b> <code>/setsupportlink [url]</code>", parse_mode=ParseMode.HTML)
            return
        
        url = context.args[0]
        if not url.startswith('http'):
            await update.message.reply_text("❌ <b>URL must start with http:// or https://</b>", parse_mode=ParseMode.HTML)
            return
        
        Config.save_env('SUPPORT', url)
        await update.message.reply_text(f"✅ <b>SUPPORT updated</b>\n<code>{url}</code>", parse_mode=ParseMode.HTML)
    
    async def setotpslink_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if update.effective_user.id != self.config.OWNER_ID:
            await update.message.reply_text("<blockquote>𝗣𝗹𝗲𝗮𝘀𝗲 𝘀𝗲𝗻𝗱 𝗮 𝘃𝗮𝗹𝗶𝗱 𝗰𝗼𝗺𝗺𝗮𝗻𝗱</blockquote>", parse_mode=ParseMode.HTML)
            return
        
        if not context.args:
            await update.message.reply_text("📝 <b>Usage:</b> <code>/setotpslink [url]</code>", parse_mode=ParseMode.HTML)
            return
        
        url = context.args[0]
        if not url.startswith('http'):
            await update.message.reply_text("❌ <b>URL must start with http:// or https://</b>", parse_mode=ParseMode.HTML)
            return
        
        Config.save_env('OTPS_GROUP', url)
        await update.message.reply_text(f"✅ <b>OTPS_GROUP updated</b>\n<code>{url}</code>", parse_mode=ParseMode.HTML)
    
    async def groupnumid_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if update.effective_user.id != self.config.OWNER_ID:
            await update.message.reply_text("<blockquote>𝗣𝗹𝗲𝗮𝘀𝗲 𝘀𝗲𝗻𝗱 𝗮 𝘃𝗮𝗹𝗶𝗱 𝗰𝗼𝗺𝗺𝗮𝗻𝗱</blockquote>", parse_mode=ParseMode.HTML)
            return
        
        if not context.args:
            await update.message.reply_text("📝 <b>Usage:</b> <code>/groupnumid [group_id]</code>", parse_mode=ParseMode.HTML)
            return
        
        group_id = context.args[0]
        Config.save_env('NUM_GROUP_ID', group_id)
        await update.message.reply_text(f"✅ <b>NUM_GROUP_ID updated</b>\n<code>{group_id}</code>", parse_mode=ParseMode.HTML)
    
    async def autodelmsg_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if update.effective_user.id != self.config.OWNER_ID:
            await update.message.reply_text("<blockquote>𝗣𝗹𝗲𝗮𝘀𝗲 𝘀𝗲𝗻𝗱 𝗮 𝘃𝗮𝗹𝗶𝗱 𝗰𝗼𝗺𝗺𝗮𝗻𝗱</blockquote>", parse_mode=ParseMode.HTML)
            return
        
        if not context.args:
            await update.message.reply_text("📝 <b>Usage:</b> <code>/autodelmsg [minutes|off]</code>", parse_mode=ParseMode.HTML)
            return
        
        arg = context.args[0].lower()
        
        if arg == 'off':
            minutes = 0
            Database.set_autodel_setting(0, {})
            
            if context.job_queue:
                current_jobs = context.job_queue.get_jobs_by_name("auto_delete")
                for job in current_jobs:
                    job.schedule_removal()
            
            await update.message.reply_text("✅ <b>Auto delete disabled!</b>", parse_mode=ParseMode.HTML)
            return
        
        try:
            minutes = int(arg)
            if minutes <= 0:
                await update.message.reply_text("❌ <b>Minutes must be greater than 0</b>", parse_mode=ParseMode.HTML)
                return
        except ValueError:
            await update.message.reply_text("❌ <b>Invalid minutes</b>", parse_mode=ParseMode.HTML)
            return
        
        autodel_setting = Database.get_autodel_setting()
        old_notif_ids = autodel_setting.get("notif_message_ids", {})
        
        for group_id, msg_id in old_notif_ids.items():
            try:
                await context.bot.delete_message(
                    chat_id=int(group_id),
                    message_id=msg_id
                )
            except:
                pass
        
        new_notif_ids = {}
        groups = Database.get_groups()
        for group_id in groups:
            try:
                message = f"""
<blockquote>𝗡𝗢𝗧𝗜𝗙𝗜𝗖𝗔𝗧𝗜𝗢𝗡 𝗙𝗢𝗥 𝗙𝗢𝗥𝗪𝗔𝗥𝗗 📢</blockquote>
━━━━━━━━━━━━━━━━━━━━━━━━━
<pre>🚀 𝚂𝚃𝙰𝚁𝚃𝙴𝙳 𝚃𝙾 𝚂𝙴𝙽𝙳 𝚂𝙼𝚂 𝚃𝚁𝙰𝙵𝙵𝙸𝙲
🤖 𝙰𝚄𝚃𝙾𝙼𝙰𝚃𝙸𝙲 𝙳𝙴𝙻 𝙾𝙻𝙳 𝙼𝙴𝚂𝚂𝙰𝙶𝙴
⏱️ 𝚃𝙸𝙼𝙴 : {minutes} 𝙼𝙸𝙽𝚄𝚃𝙴𝚂</pre>
━━━━━━━━━━━━━━━━━━━━━━━━━
<blockquote>𝚃𝙸𝙼𝙴 {minutes} 𝙼𝙸𝙽𝚄𝚃𝙴𝚂 | 🗑️ 𝙰𝚄𝚃𝙾 𝙳𝙴𝙻𝙴𝚃𝙴</blockquote>
<blockquote>𝗣𝗼𝘄𝗲𝗿𝗲𝗱 𝗕𝘆 𝗗𝗮𝘆𝘇𝗗𝗶𝗴𝗶𝘁𝗮𝗹 𝗢𝗳𝗳𝗶𝗰𝗶𝗮𝗹</blockquote>"""
                
                sent_msg = await context.bot.send_message(
                    chat_id=int(group_id),
                    text=message,
                    parse_mode=ParseMode.HTML,
                    link_preview_options=LinkPreviewOptions(is_disabled=True)
                )
                
                new_notif_ids[group_id] = sent_msg.message_id
                
            except Exception as e:
                print(f"Failed to send notification to group {group_id}: {e}")
        
        Database.set_autodel_setting(minutes, new_notif_ids)
        
        if context.job_queue:
            current_jobs = context.job_queue.get_jobs_by_name("auto_delete")
            for job in current_jobs:
                job.schedule_removal()
        
        if minutes > 0 and context.job_queue:
            context.job_queue.run_repeating(
                self.auto_delete_old_messages,
                interval=15,
                first=10,
                name="auto_delete",
                data={"minutes": minutes}
            )
        
        await update.message.reply_text(f"✅ <b>Auto delete enabled! Messages older than {minutes} minutes will be deleted.</b>", parse_mode=ParseMode.HTML)
    
    async def auto_delete_old_messages(self, context: ContextTypes.DEFAULT_TYPE):
        try:
            job = context.job
            minutes = job.data.get("minutes", 0) if job and hasattr(job, 'data') else 0
            
            if minutes <= 0:
                return
            
            groups = Database.get_groups()
            for group_id in groups:
                try:
                    old_messages = Database.get_old_bot_messages(minutes)
                    
                    group_messages = [msg for msg in old_messages if msg.get("group_id") == group_id]
                    
                    for msg in group_messages:
                        try:
                            await context.bot.delete_message(
                                chat_id=group_id,
                                message_id=msg.get("message_id")
                            )
                            Database.remove_bot_message(group_id, msg.get("message_id"))
                        except Exception as e:
                            Database.remove_bot_message(group_id, msg.get("message_id"))
                            continue
                except Exception as e:
                    print(f"Error in auto delete for group {group_id}: {e}")
        except Exception as e:
            print(f"Error in auto_delete_old_messages: {e}")
    
    async def verification_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if update.effective_user.id != self.config.OWNER_ID:
            await update.message.reply_text("<blockquote>𝗣𝗹𝗲𝗮𝘀𝗲 𝘀𝗲𝗻𝗱 𝗮 𝘃𝗮𝗹𝗶𝗱 𝗰𝗼𝗺𝗺𝗮𝗻𝗱</blockquote>", parse_mode=ParseMode.HTML)
            return
        
        await self.verification_menu(update, context)
    
    async def new_chat_members(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if update.message.new_chat_members:
            for member in update.message.new_chat_members:
                if member.id == context.bot.id:
                    chat_id = update.effective_chat.id
                    
                    groups = Database.get_groups()
                    if str(chat_id) in groups:
                        return
    
    async def callback_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        if query:
            await query.answer()
            data = query.data
        else:
            return
        
        if data == "back_to_menu":
            await self.user_menu(update, context)
        elif data == "get_number":
            await self.get_number_menu(update, context)
        elif data.startswith("select_range_"):
            await self.select_range(update, context)
        elif data == "new_number_request":
            await self.new_number_request_handler(update, context)
        elif data == "owner_menu":
            await self.owner_menu(update, context)
        elif data == "menu_ranges":
            await self.ranges_menu(update, context)
        elif data == "new_ranges":
            await self.new_ranges_handler(update, context)
        elif data == "delete_ranges":
            await self.delete_ranges_handler(update, context)
        elif data.startswith("del_range_"):
            await self.delete_range_confirm(update, context)
        elif data == "menu_groups":
            await self.groups_menu(update, context)
        elif data == "delete_groups":
            await self.delete_groups_handler(update, context)
        elif data == "statistic_menu":
            await self.statistic_menu(update, context)
        elif data == "menu_other":
            await self.other_menu(update, context)
        elif data == "menu_verification":
            await self.verification_menu(update, context)
        elif data == "new_verif":
            await self.new_verif_handler(update, context)
        elif data == "del_verif":
            await self.del_verif_handler(update, context)
        elif data == "copy_otp":
            await query.answer("OTP copied to clipboard!", show_alert=True)
        elif data == "refresh_verify":
            await self.refresh_verify(update, context)
        elif data == "backup_menu":
            await self.backup_menu(update, context)
    
    async def message_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        
        if update.effective_chat.type in ['group', 'supergroup']:
            return
        
        user_id = user.id
        
        if user_id in self.awaiting_input:
            if self.awaiting_input.get(user_id) in ['waiting_service_name']:
                await self.process_service_name(update, context)
            elif self.awaiting_input.get(user_id) in ['delete_group_input']:
                await self.process_group_delete(update, context)
            elif self.awaiting_input.get(user_id) in ['new_verif_link', 'new_verif_id', 'del_verif_id']:
                await self.process_verif_input(update, context)
            elif self.awaiting_input.get(user_id) in ['fastotps_numbers']:
                await self.process_fastotps(update, context)
        else:
            await update.message.reply_text(
                "<blockquote>𝗣𝗹𝗲𝗮𝘀𝗲 𝘀𝗲𝗻𝗱 𝗮 𝘃𝗮𝗹𝗶𝗱 𝗰𝗼𝗺𝗺𝗮𝗻𝗱</blockquote>",
                parse_mode=ParseMode.HTML
            )
    
    async def cfd_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if update.effective_user.id != self.config.OWNER_ID:
            await update.message.reply_text("<blockquote>𝗣𝗹𝗲𝗮𝘀𝗲 𝘀𝗲𝗻𝗱 𝗮 𝘃𝗮𝗹𝗶𝗱 𝗰𝗼𝗺𝗺𝗮𝗻𝗱</blockquote>", parse_mode=ParseMode.HTML)
            return
        
        replied_message = update.message.reply_to_message
        
        if not replied_message:
            if len(context.args) == 0:
                await update.message.reply_text("📝 <b>Usage:</b> <code>/cfd [message] or reply to message</code>", parse_mode=ParseMode.HTML)
                return
            
            message_text = " ".join(context.args)
            media_type = None
            media_content = None
            caption = None
        else:
            if replied_message.text:
                message_text = replied_message.text
                media_type = None
                media_content = None
                caption = None
            elif replied_message.photo:
                message_text = replied_message.caption or ""
                media_type = "photo"
                media_content = replied_message.photo[-1].file_id
                caption = replied_message.caption
            elif replied_message.video:
                message_text = replied_message.caption or ""
                media_type = "video"
                media_content = replied_message.video.file_id
                caption = replied_message.caption
            elif replied_message.document:
                message_text = replied_message.caption or ""
                media_type = "document"
                media_content = replied_message.document.file_id
                caption = replied_message.caption
            else:
                message_text = replied_message.caption or ""
                media_type = None
                media_content = None
                caption = None
        
        users = Database.get_users()
        all_users = users.get("not_verif", []) + users.get("Verified", [])
        
        success = 0
        fail = 0
        
        processing_msg = await update.message.reply_text(f"📤 <b>Sending message to {len(all_users)} users...</b>", parse_mode=ParseMode.HTML)
        
        for user_id in all_users:
            if user_id == self.config.OWNER_ID:
                continue
                
            try:
                if media_type == "photo":
                    await context.bot.send_photo(
                        chat_id=user_id,
                        photo=media_content,
                        caption=caption.replace('\n', '<br>') if caption else None,
                        parse_mode=ParseMode.HTML
                    )
                elif media_type == "video":
                    await context.bot.send_video(
                        chat_id=user_id,
                        video=media_content,
                        caption=caption.replace('\n', '<br>') if caption else None,
                        parse_mode=ParseMode.HTML
                    )
                elif media_type == "document":
                    await context.bot.send_document(
                        chat_id=user_id,
                        document=media_content,
                        caption=caption.replace('\n', '<br>') if caption else None,
                        parse_mode=ParseMode.HTML
                    )
                else:
                    await context.bot.send_message(
                        chat_id=user_id,
                        text=message_text.replace('\n', '<br>'),
                        parse_mode=ParseMode.HTML
                    )
                success += 1
            except Exception as e:
                fail += 1
        
        try:
            await processing_msg.edit_text(
                f"✅ <b>Broadcast completed!</b>\n"
                f"• ✅ Success: {success}\n"
                f"• ❌ Failed: {fail}",
                parse_mode=ParseMode.HTML
            )
        except BadRequest as e:
            if "Message is not modified" not in str(e):
                raise
    
    async def fwd_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if update.effective_user.id != self.config.OWNER_ID:
            await update.message.reply_text("<blockquote>𝗣𝗹𝗲𝗮𝘀𝗲 𝘀𝗲𝗻𝗱 𝗮 𝘃𝗮𝗹𝗶𝗱 𝗰𝗼𝗺𝗺𝗮𝗻𝗱</blockquote>", parse_mode=ParseMode.HTML)
            return
        
        if not update.message.reply_to_message:
            await update.message.reply_text("📝 <b>Reply to a message to forward!</b>", parse_mode=ParseMode.HTML)
            return
        
        users = Database.get_users()
        all_users = users.get("not_verif", []) + users.get("Verified", [])
        
        success = 0
        fail = 0
        
        processing_msg = await update.message.reply_text(f"📤 <b>Forwarding message to {len(all_users)} users...</b>", parse_mode=ParseMode.HTML)
        
        for user_id in all_users:
            if user_id == self.config.OWNER_ID:
                continue
                
            try:
                await update.message.reply_to_message.forward(chat_id=user_id)
                success += 1
            except Exception as e:
                fail += 1
        
        try:
            await processing_msg.edit_text(
                f"✅ <b>Forward completed!</b>\n"
                f"• ✅ Success: {success}\n"
                f"• ❌ Failed: {fail}",
                parse_mode=ParseMode.HTML
            )
        except BadRequest as e:
            if "Message is not modified" not in str(e):
                raise
    
    async def traffic_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        
        if not Database.is_verified(user.id):
            await update.message.reply_text(
                "⚠️ You need to verify first!",
                parse_mode=ParseMode.HTML
            )
            return
        
        traffic_data = Database.get_today_traffic_by_service_and_country()
        
        if not traffic_data:
            await update.message.reply_text(
                "📊 <b>No traffic data available today.</b>",
                parse_mode=ParseMode.HTML
            )
            return
        
        message = "<blockquote>❯ 𝗧𝗢𝗗𝗔𝗬'𝗦 𝗔𝗖𝗧𝗜𝗩𝗘 𝗧𝗥𝗔𝗙𝗙𝗜𝗖</blockquote>\n\n"
        
        countries_db = Database.get_countries()
        
        for service, country_data in sorted(traffic_data.items(), key=lambda x: sum(x[1].values()), reverse=True):
            total_service = sum(country_data.values())
            
            if total_service > 200:
                service_emoji = "🔥"
            elif total_service > 50:
                service_emoji = "🚀"
            else:
                service_emoji = "✅"
            
            message += f"<blockquote><b>{service} {service_emoji}</b></blockquote>\n"
            
            for country, count in sorted(country_data.items(), key=lambda x: x[1], reverse=True):
                country_info = next((c for c in countries_db.values() if c['name'] == country), None)
                flag = country_info['flag'] if country_info else "🌐"
                
                if count > 200:
                    country_emoji = "🔥"
                elif count > 50:
                    country_emoji = "🚀"
                else:
                    country_emoji = "✅"
                
                message += f"<b>{flag}{country} : {count} {country_emoji}</b>\n"
            
            message += "\n"
        
        message += "<blockquote>𝗣𝗼𝘄𝗲𝗿𝗲𝗱 𝗕𝘆 𝗗𝗮𝘆𝘇𝗗𝗶𝗴𝗶𝘁𝗮𝗹 𝗢𝗳𝗳𝗶𝗰𝗶𝗮𝗹</blockquote>"
        
        await update.message.reply_text(
            message,
            parse_mode=ParseMode.HTML,
            link_preview_options=LinkPreviewOptions(is_disabled=True)
        )

def main():
    Database.init_db()
    config = Config()
    bot_handler = BotHandler(config)
    
    print(f"{Fore.GREEN}[]════════[] LOGIN SUCCESSFULLY []════════[]{Style.RESET_ALL}")
    
    application = Application.builder().token(config.BOT_TOKEN).build()
    
    application.add_handler(CommandHandler("start", bot_handler.start))
    application.add_handler(CommandHandler("fastotps", bot_handler.fastotps_command))
    application.add_handler(CommandHandler("traffic", bot_handler.traffic_command))
    application.add_handler(CommandHandler("setchlink", bot_handler.setchlink_command))
    application.add_handler(CommandHandler("setownerlink", bot_handler.setownerlink_command))
    application.add_handler(CommandHandler("setsupportlink", bot_handler.setsupportlink_command))
    application.add_handler(CommandHandler("setotpslink", bot_handler.setotpslink_command))
    application.add_handler(CommandHandler("groupnumid", bot_handler.groupnumid_command))
    application.add_handler(CommandHandler("autodelmsg", bot_handler.autodelmsg_command))
    application.add_handler(CommandHandler("verification", bot_handler.verification_command))
    application.add_handler(CommandHandler("cfd", bot_handler.cfd_command))
    application.add_handler(CommandHandler("fwd", bot_handler.fwd_command))
    application.add_handler(CommandHandler("backupdb", bot_handler.backupdb_command))
    application.add_handler(CommandHandler("backupnum", bot_handler.backupnum_command))
    application.add_handler(CommandHandler("restoredb", bot_handler.restoredb_command))
    application.add_handler(CommandHandler("restorenum", bot_handler.restorenum_command))
    
    application.add_handler(CallbackQueryHandler(bot_handler.callback_handler))
    
    application.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND,
        bot_handler.message_handler
    ))
    
    application.add_handler(MessageHandler(
        filters.Document.ALL,
        bot_handler.process_ranges_file
    ))
    
    application.add_handler(MessageHandler(
        filters.StatusUpdate.NEW_CHAT_MEMBERS,
        bot_handler.new_chat_members
    ))
    
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    async def run_bot():
        await application.initialize()
        await application.start()
        await application.updater.start_polling()
        
        otp_task = asyncio.create_task(bot_handler.otp_receiver.process_sms(application))
        
        print(f"{Fore.GREEN}[]════════[] BOT STARTED SUCCESSFULLY []════════[]{Style.RESET_ALL}")
        
        await otp_task
    
    try:
        loop.run_until_complete(run_bot())
        loop.run_forever()
    except KeyboardInterrupt:
        print(f"\n{Fore.YELLOW}[]════════[] BOT STOPPED []════════[]{Style.RESET_ALL}")
    finally:
        loop.run_until_complete(application.stop())
        loop.close()

if __name__ == "__main__":
    main()