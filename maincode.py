import time
import threading
import os
from dotenv import load_dotenv
from keep_alive import keep_alive

import discord
from discord.ext import commands
from discord import app_commands
from discord.ui import View, Button, Modal, TextInput
from datetime import datetime

import aiohttp
import asyncio

# Функция для вывода в консоль "живой"
def loop_forever():
    while True:
        print("Я живой...")
        time.sleep(60)

# Запуск веб-сервера, чтобы бот не отключался
keep_alive()

# Запуск потока с сообщениями в консоль
t = threading.Thread(target=loop_forever, daemon=True)
t.start()

# Загрузка токена
load_dotenv()
TOKEN = os.getenv("TOKEN")
if not TOKEN:
    raise ValueError("Переменная окружения TOKEN не найдена! Добавь её в .env файл.")

# Константы и настройки
GUILD_ID = 1360340501152141463
APPLICATIONS_CHANNEL_ID = 1360341903765147698
LOG_CHANNEL_ID = 1360341946257899580
PING_ROLE_ID = 1360343985565995208

MODERATOR_ROLE_NAMES = [
    "ʀᴇᴄʀᴜɪᴛᴇʀ", "ᴅꜱ ᴍᴏᴅ ᴏᴡɴᴇʀ", "ʟᴇᴀᴅᴇʀ", "ᴅꜱ ᴍᴏᴅᴇʀᴀᴛᴏʀ",
    "ᴅᴇᴘᴜᴛʏ ʟᴇᴀᴅᴇʀ", "PIDORAAAAS", "🐹Hamster🐹", "ʜɪɢʜ"
]
ROLES_TO_GIVE_IDS = [1360343840308986098, 1360343865940246629]

intents = discord.Intents.default()
intents.members = True
bot = commands.Bot(command_prefix="!", intents=intents)

# --- Self-ping для Replit ---
async def self_ping():
    await bot.wait_until_ready()
    url = "https://48cb05f0-0bb7-4b86-b8b6-8fb84b9e6006-00-3ay13cljouwhu.kirk.replit.dev/"
    while not bot.is_closed():
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as resp:
                    print(f"[Self Ping] Status: {resp.status}")
        except Exception as e:
            print(f"[Self Ping] Error: {e}")
        await asyncio.sleep(240)

class OpenApplicationView(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Открыть заявку", style=discord.ButtonStyle.green, custom_id="open_app")
    async def open_app(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_modal(ApplicationModal())

class ApplicationModal(Modal):
    def __init__(self):
        super().__init__(title="Форма заявки")
        self.name    = TextInput(label="Имя | Статик", max_length=100)
        self.source  = TextInput(label="Как вы нас нашли?", max_length=200)
        self.ooc_age = TextInput(label="OOC возраст", max_length=3)
        self.hours   = TextInput(label="Сколько часов?", max_length=10)
        for item in (self.name, self.source, self.ooc_age, self.hours):
            self.add_item(item)

    async def on_submit(self, interaction: discord.Interaction):
        guild = interaction.guild
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            interaction.user:   discord.PermissionOverwrite(view_channel=True, send_messages=True, read_messages=True),
        }
        for rn in MODERATOR_ROLE_NAMES:
            r = discord.utils.get(guild.roles, name=rn)
            if r:
                overwrites[r] = discord.PermissionOverwrite(
                    view_channel=True, send_messages=True,
                    read_messages=True, manage_messages=True
                )

        chan = await guild.create_text_channel(
            name=f"заявка-{interaction.user.name}".lower(),
            overwrites=overwrites,
            reason="Новая заявка"
        )

        embed = discord.Embed(title="Новая заявка", color=0x8B0000)
        embed.add_field(name="Пользователь", value=interaction.user.mention, inline=False)
        embed.add_field(name="Имя | Статик", value=self.name.value, inline=False)
        embed.add_field(name="Как нашли нас?", value=self.source.value, inline=False)
        embed.add_field(name="OOC возраст", value=self.ooc_age.value, inline=False)
        embed.add_field(name="Сколько часов?", value=self.hours.value, inline=False)

        view = ApplicationDecisionView(interaction.user, chan, embed)
        await chan.send(content=f"<@&{PING_ROLE_ID}>", embed=embed, view=view)
        await interaction.response.send_message(f"Ваша заявка создана: {chan.mention}", ephemeral=True)

class ApplicationDecisionView(View):
    def __init__(self, applicant: discord.Member, channel: discord.TextChannel, embed: discord.Embed):
        super().__init__(timeout=None)
        self.applicant = applicant
        self.channel = channel
        self.embed = embed

    @discord.ui.button(label="Принять", style=discord.ButtonStyle.green)
    async def accept(self, interaction: discord.Interaction, button: Button):
        if not any(r.name in MODERATOR_ROLE_NAMES for r in interaction.user.roles):
            return await interaction.response.send_message("Нет прав!", ephemeral=True)
        for rid in ROLES_TO_GIVE_IDS:
            role = interaction.guild.get_role(rid)
            if role:
                await self.applicant.add_roles(role, reason="Заявка принята")
        try:
            await self.applicant.send("Ваша заявка была принята! Добро пожаловать.")
        except discord.Forbidden:
            pass
        await interaction.response.send_message("Заявка принята", ephemeral=True)
        await self.channel.delete(reason="Принято")

    @discord.ui.button(label="Отклонить", style=discord.ButtonStyle.danger)
    async def reject(self, interaction: discord.Interaction, button: Button):
        if not any(r.name in MODERATOR_ROLE_NAMES for r in interaction.user.roles):
            return await interaction.response.send_message("Нет прав!", ephemeral=True)
        await interaction.response.send_modal(RejectReasonModal(self.applicant, self.channel, self.embed))

class RejectReasonModal(Modal, title="Причина отклонения"):
    reason = TextInput(label="Введите причину", style=discord.TextStyle.paragraph)

    def __init__(self, applicant, channel, embed):
        super().__init__()
        self.applicant = applicant
        self.channel = channel
        self.embed = embed

    async def on_submit(self, interaction: discord.Interaction):
        log_channel = interaction.guild.get_channel(LOG_CHANNEL_ID)
        if log_channel:
            rej_embed = discord.Embed(
                title="Заявка отклонена",
                description=f"Причина: {self.reason.value}",
                color=0x8B0000
            )
            rej_embed.add_field(name="Отклонено", value=self.applicant.mention, inline=False)
            rej_embed.set_footer(text=f"Отклонил: {interaction.user.display_name} | {datetime.now().strftime('%d.%m.%Y %H:%M')}")
            await log_channel.send(embed=rej_embed)
        await interaction.response.send_message("Заявка отклонена и отправлена в лог", ephemeral=True)
        await self.channel.delete(reason="Отклонено")

@bot.tree.command(guild=discord.Object(id=GUILD_ID), name="эмбит", description="Создать эмбед сообщение")
@app_commands.describe(
    title="Заголовок",
    description="Основной текст",
    color="Цвет: красный, белый и т.д.",
    button_type="Тип кнопки: link или def",
    button_url="Ссылка, если тип link"
)
async def эмбит(
    interaction: discord.Interaction,
    title: str,
    description: str,
    color: str,
    button_type: str = None,
    button_url: str = None
):
    color_map = {
        "красный": 0xFF0000,
        "белый": 0xFFFFFF,
        "зелёный": 0x00FF00,
        "синий": 0x0000FF,
        "жёлтый": 0xFFFF00,
        "чёрный": 0x000000,
    }
    hex_color = color_map.get(color.lower())
    if hex_color is None:
        return await interaction.response.send_message("Неверный цвет. Доступные: красный, белый, зелёный, синий, жёлтый, чёрный", ephemeral=True)

    embed = discord.Embed(title=title, description=description, color=hex_color)
    view = None

    if button_type:
        view = View()
        if button_type == "link":
            if not button_url:
                return await interaction.response.send_message("Для кнопки 'link' нужно указать URL.", ephemeral=True)
            view.add_item(Button(label="Перейти", style=discord.ButtonStyle.link, url=button_url))
        elif button_type == "def":
            button = Button(label="Нажми", style=discord.ButtonStyle.primary)

            async def callback(i: discord.Interaction):
                try:
                    await i.user.send("Зачем нажал?")
                    await i.response.send_message("Сообщение отправлено в ЛС", ephemeral=True)
                except discord.Forbidden:
                    await i.response.send_message("Не удалось отправить сообщение в ЛС.", ephemeral=True)

            button.callback = callback
            view.add_item(button)

    await interaction.response.send_message(embed=embed, view=view)

@bot.event
async def on_ready():
    bot.add_view(OpenApplicationView())
    await bot.tree.sync(guild=discord.Object(id=GUILD_ID))
    print(f"Бот {bot.user} готов и persistent view зарегистрирован")
    bot.loop.create_task(self_ping())

bot.run(TOKEN)
