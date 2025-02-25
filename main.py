"""
Telegram Bitcoin Shop Bot
Требуемые библиотеки: 
pip install python-bitcoinrpc aiogram psycopg2 requests python-dotenv
"""

import os
import logging
import asyncio
from decimal import Decimal
from datetime import datetime
from typing import List, Dict, Optional

import psycopg2
from bitcoinrpc.authproxy import AuthServiceProxy, JSONRPCException
from bitcoinutils.setup import setup
from bitcoinutils.hdwallet import HDWallet
from aiogram import Bot, Dispatcher, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters import Command
from dotenv import load_dotenv

load_dotenv()

# --- Конфигурация ---
class Config:
    TOKEN = os.getenv("TELEGRAM_TOKEN")
    BITCOIN_RPC = {
        'user': os.getenv("BTC_RPC_USER"),
        'password': os.getenv("BTC_RPC_PASS"),
        'host': 'localhost',
        'port': 8332
    }
    DB_CONFIG = {
        'dbname': os.getenv("DB_NAME"),
        'user': os.getenv("DB_USER"),
        'password': os.getenv("DB_PASS"),
        'host': os.getenv("DB_HOST")
    }
    WALLET_SEED = os.getenv("WALLET_SEED")
    ADMIN_IDS = list(map(int, os.getenv("ADMIN_IDS").split(',')))

# Инициализация
bot = Bot(token=Config.TOKEN)
dp = Dispatcher(bot, storage=MemoryStorage())
setup('mainnet')

# --- Работа с Bitcoin ---
class BitcoinManager:
    def __init__(self):
        self.rpc = AuthServiceProxy(
            f"http://{Config.BITCOIN_RPC['user']}:{Config.BITCOIN_RPC['password']}"
            f"@{Config.BITCOIN_RPC['host']}:{Config.BITCOIN_RPC['port']}"
        )
        self.wallet = HDWallet.from_seed(Config.WALLET_SEED)

    def get_new_address(self, user_id: int) -> str:
        """Генерация дочернего адреса для пользователя"""
        path = f"m/44'/0'/0'/0/{user_id}"
        self.wallet.from_path(path)
        return self.wallet.get_address().to_string()

# --- База данных ---
class Database:
    def __init__(self):
        self.conn = psycopg2.connect(**Config.DB_CONFIG)
        self._init_db()

    def _init_db(self):
        """Инициализация таблиц"""
        with self.conn.cursor() as cur:
            # Пользователи
            cur.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id BIGINT PRIMARY KEY,
                    address TEXT NOT NULL,
                    balance DECIMAL DEFAULT 0
                )""")
            
            # Транзакции пополнения
            cur.execute("""
                CREATE TABLE IF NOT EXISTS invoices (
                    txid TEXT PRIMARY KEY,
                    user_id BIGINT,
                    amount DECIMAL,
                    confirmations INT,
                    timestamp TIMESTAMP
                )""")
            
            # Товары
            cur.execute("""
                CREATE TABLE IF NOT EXISTS products (
                    id SERIAL PRIMARY KEY,
                    category TEXT,
                    name TEXT,
                    price_rub DECIMAL,
                    description TEXT
                )""")
            
            # Промокоды
            cur.execute("""
                CREATE TABLE IF NOT EXISTS promocodes (
                    code TEXT PRIMARY KEY,
                    product_id INT,
                    used BOOLEAN DEFAULT FALSE
                )""")
            
            # Покупки
            cur.execute("""
                CREATE TABLE IF NOT EXISTS purchases (
                    user_id BIGINT,
                    product_id INT,
                    code TEXT,
                    timestamp TIMESTAMP
                )""")
            self.conn.commit()

    # --- Методы для работы с пользователями ---
    def create_user(self, user_id: int, address: str):
        with self.conn.cursor() as cur:
            cur.execute(
                "INSERT INTO users (user_id, address) VALUES (%s, %s)",
                (user_id, address)
            self.conn.commit()

# --- Обработчики команд ---
@dp.message_handler(Command('start'))
async def cmd_start(message: types.Message):
    """Регистрация пользователя"""
    user_id = message.from_user.id
    btc = BitcoinManager()
    address = btc.get_new_address(user_id)
    
    db = Database()
    db.create_user(user_id, address)
    
    await message.answer(
        f"👋 Добро пожаловать!\nВаш адрес для пополнения: `{address}`\n"
        "Баланс обновляется после 2 подтверждений в сети Bitcoin.",
        parse_mode="Markdown")

# --- Полный код продолжается ---
