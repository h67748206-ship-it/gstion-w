import ast
import json
import operator
import os
import re
import threading
import time
from datetime import datetime, timedelta
from urllib.parse import quote

import aiohttp
import discord
from discord.ext import commands, tasks
from flask import Flask

# ============================================================
# CONFIG
# ============================================================
TOKEN = os.getenv("DISCORD_TOKEN")
PORT = int(os.getenv("PORT", "10000"))
PREFIX = "+"
BOT_NAME = "Mon Bot"
EMBED_COLOR = 0x2B2D31
OWNER_IDS = {int(x) for x in os.getenv("OWNER_IDS", "").split(",") if x.strip().isdigit()}
DATA_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "bot_data.json")
MAX_TIMEOUT = 28 * 86400  # limite Discord pour un timeout
DANGEROUS_PERMS = (
    "administrator", "manage_guild", "manage_roles", "ban_members",
    "kick_members", "manage_channels", "manage_webhooks",
)

PARAM_NOTE = (
    "Les paramètres peuvent être des noms, des mentions, ou des IDs. "
    "Si ce ne sont pas des mentions ils doivent être séparés par `,`"
)

# ============================================================
# DONNÉES PERSISTANTES (fichier JSON local)
# ============================================================
def load_data() -> dict:
    try:
        with open(DATA_FILE, encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


DATA = load_data()
for _key in ("sanctions", "notes", "blacklist", "blrank", "lockednames", "antiraid", "suggestions"):
    DATA.setdefault(_key, {})
DATA.setdefault("tempbans", [])


def save() -> None:
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(DATA, f, ensure_ascii=False, indent=2)


snipes: dict = {}          # channel_id -> dernier message supprimé
recent_msgs: dict = {}     # (guild, user) -> [(contenu, timestamp)] pour doublons

# ============================================================
# CONTENU DU MENU D'AIDE
# ============================================================
CATEGORIES = {
    "moderation": {
        "label": "Modération", "emoji": "🛡️",
        "description": "Sanctions et modération des membres",
        "commands": [
            ("sanctions <membre>", "Affiche les sanctions reçues par un membre"),
            ("del sanction <membre> <numéro/all>", "Supprime une sanction ou toutes les sanctions"),
            ("clear sanctions <membre>", "Supprime toutes les sanctions d'un membre"),
            ("clear [nombre] [membre]", "Supprime le nombre de messages donné dans le salon actuel"),
            ("note <membre> [raison]", "Ajoute une note de modération à un membre"),
            ("note delete <membre> <nombre/all>", "Supprime une ou toutes les notes d'un membre"),
            ("note delete all", "Supprime toutes les notes du serveur"),
            ("warn <membre> [raison]", "Donne un warn à un membre"),
            ("mute <membre> [raison]", "Mute un membre (timeout 28 jours)"),
            ("unmute <membre>", "Met fin au mute d'un membre"),
            ("tempmute <membre> <durée> [raison]", "Mute un membre pour une durée déterminée"),
            ("kick <membre> [raison]", "Expulse un membre du serveur"),
            ("ban <membre> [raison]", "Banni un membre du serveur"),
            ("tempban <membre> <durée> [raison]", "Banni un membre pour une durée déterminée"),
            ("unban <id>", "Enlève le bannissement d'un membre"),
            ("banlist", "Affiche la liste des bannissements en cours"),
            ("addrole <membre> <rôle>", "Ajoute un ou plusieurs rôles à un membre (séparés par ,)"),
            ("delrole <membre> <rôle>", "Supprime un ou plusieurs rôles d'un membre (séparés par ,)"),
            ("derank <membre>", "Supprime tous les rôles d'un membre"),
            ("nick <membre> <nom>", "Change le pseudo d'un membre sur le serveur"),
            ("lockname <membre>", "Verrouille le pseudo actuel d'un membre"),
            ("unlockname <membre>", "Déverrouille le pseudo d'un membre"),
            ("locknamelist", "Affiche la liste des membres ayant un pseudo verrouillé"),
        ],
    },
    "configuration": {
        "label": "Configuration du serveur", "emoji": "⚙️",
        "description": "Permissions et réglages du serveur",
        "commands": [
            ("perms", "Affiche les rôles ayant des permissions sensibles sur le serveur"),
        ],
    },
    "gestion": {
        "label": "Gestion du serveur", "emoji": "🧰",
        "description": "Outils de gestion vocale et serveur",
        "commands": [
            ("voicekick <membre>", "Déconnecte un membre de son salon vocal actuel"),
        ],
    },
    "antiraid": {
        "label": "Antiraid", "emoji": "🚨",
        "description": "Protection anti-raid et blacklist rank",
        "commands": [
            ("antiraid", "Affiche l'état des modules : antiphish, salon piège, doublons"),
            ("antiraid antiphish <on/off>", "Bloque les liens postés par les comptes récents (< 7 jours)"),
            ("antiraid doublons <on/off>", "Détecte et sanctionne le spam de messages identiques"),
            ("antiraid piege <#salon/off>", "Bannit quiconque écrit dans le salon piège"),
            ("blrank", "Affiche la blacklist rank et son mode"),
            ("blrank on/off", "Active ou désactive la blacklist rank"),
            ("blrank danger/all", "Bloque seulement les rôles dangereux, ou tous les rôles"),
            ("blrank add/del <membre>", "Ajoute ou retire un membre de la blacklist rank"),
            ("clear blrank", "Retire tous les membres de la blacklist rank"),
        ],
    },
    "controle": {
        "label": "Contrôle du bot", "emoji": "🤖",
        "description": "Gestion globale du bot (propriétaires)",
        "commands": [
            ("bl <membre> <raison>", "Ajoute quelqu'un à la blacklist, il sera banni de tous les serveurs du bot"),
            ("bl", "Affiche la blacklist du bot"),
            ("unbl <membre>", "Retire quelqu'un de la blacklist du bot"),
            ("blinfo <membre>", "Affiche les informations de blacklist d'un membre"),
        ],
    },
    "utilitaire": {
        "label": "Utilitaire", "emoji": "🧩",
        "description": "Outils divers : avatars, emojis, recherches",
        "commands": [
            ("pic [membre]", "Permet de récupérer la photo de profil de quelqu'un"),
            ("banner [membre]", "Permet de récupérer la bannière de quelqu'un"),
            ("server pic", "Permet de récupérer l'icône du serveur"),
            ("server banner", "Permet de récupérer la bannière du serveur"),
            ("emoji <emoji>", "Permet de récupérer l'image d'un émoji"),
            ("snipe", "Affiche le dernier message supprimé du salon"),
            ("image <mot-clé>", "Lance une recherche Google Images avec le mot-clé"),
            ("suggestion <message>", "Poste une suggestion sur le serveur"),
            ("lb suggestions", "Affiche les suggestions les mieux notées du serveur"),
            ("wiki <mot-clé>", "Fait une recherche Wikipedia avec le mot-clé"),
            ("calc <calcul>", "Permet de résoudre des calculs ou des équations"),
            ("help [catégorie]", "Affiche l'aide par catégorie, ou l'aide sur une commande"),
        ],
    },
}
KEYS = list(CATEGORIES.keys())


# ============================================================
# HELPERS
# ============================================================
def simple_embed(text: str, color: int = EMBED_COLOR) -> discord.Embed:
    return discord.Embed(description=text, color=color)


def ok(text: str) -> discord.Embed:
    return simple_embed(f"✅ {text}", 0x23A55A)


def err(text: str) -> discord.Embed:
    return simple_embed(f"❌ {text}", 0xF23F43)


def footer(embed: discord.Embed) -> discord.Embed:
    embed.set_footer(text=f"{BOT_NAME} • Préfixe actuel : {PREFIX}")
    return embed


def home_embed() -> discord.Embed:
    lines = [f"{c['emoji']} **{c['label']}** — {c['description']}" for c in CATEGORIES.values()]
    return footer(discord.Embed(
        title=f"{BOT_NAME} — Menu d'aide",
        description="Choisis une catégorie dans le menu ci-dessous.\n\n" + "\n".join(lines),
        color=EMBED_COLOR,
    ))


def category_embed(key: str) -> discord.Embed:
    cat = CATEGORIES[key]
    body = [f"*{PARAM_NOTE}*", ""]
    for cmd, desc in cat["commands"]:
        body.append(f"**`{PREFIX}{cmd}`**\n{desc}\n")
    return footer(discord.Embed(
        title=f"{cat['emoji']} {cat['label']}",
        description="\n".join(body)[:4096],
        color=EMBED_COLOR,
    ))


def make_embed(index):
    return home_embed() if index is None else category_embed(KEYS[index])


def parse_duration(text: str):
    """'10' ou '10m' -> minutes ; '2h', '1d', '30s' supportés."""
    m = re.fullmatch(r"(\d+)\s*([smhdj]?)", text.strip().lower())
    if not m:
        return None
    unit = m.group(2) or "m"
    return int(m.group(1)) * {"s": 1, "m": 60, "h": 3600, "d": 86400, "j": 86400}[unit]


def is_exempt(member: discord.Member) -> bool:
    p = member.guild_permissions
    return p.administrator or p.manage_guild


def resolve_role(guild: discord.Guild, text: str):
    text = text.strip()
    m = re.search(r"\d{15,20}", text)
    if m:
        return guild.get_role(int(m.group()))
    return discord.utils.get(guild.roles, name=text)


async def fetch_user_from(text: str) -> discord.User:
    m = re.search(r"\d{15,20}", text)
    if not m:
        raise commands.BadArgument("ID invalide")
    return await bot.fetch_user(int(m.group()))


def sanction_list(gid: int, uid: int) -> list:
    return DATA["sanctions"].setdefault(str(gid), {}).setdefault(str(uid), [])


def add_sanction(guild_id: int, user_id: int, kind: str, reason: str, mod_id: int) -> None:
    sanction_list(guild_id, user_id).append({
        "type": kind, "reason": reason, "mod": str(mod_id), "date": time.time(),
    })
    save()


def get_blrank(gid: int) -> dict:
    return DATA["blrank"].setdefault(str(gid), {"enabled": False, "mode": "danger", "members": []})


def get_antiraid(gid: int) -> dict:
    return DATA["antiraid"].setdefault(str(gid), {"antiphish": False, "doublons": False, "piege": None})


def owner_only():
    async def predicate(ctx):
        if ctx.author.id not in OWNER_IDS:
            raise commands.CheckFailure("owner")
        return True
    return commands.check(predicate)


# ============================================================
# VIEW DU MENU +help : select + boutons ◀ 🏠 ▶
# ============================================================
SELECT_OPTIONS = [
    discord.SelectOption(label=c["label"], value=k, emoji=c["emoji"], description=c["description"][:100])
    for k, c in CATEGORIES.items()
]


class HelpView(discord.ui.View):
    def __init__(self, owner_id: int):
        super().__init__(timeout=180)
        self.owner_id = owner_id
        self.index = None

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.owner_id:
            await interaction.response.send_message("Ce menu n'est pas pour toi.", ephemeral=True)
            return False
        return True

    @discord.ui.select(placeholder="Fais un choix", min_values=1, max_values=1, options=SELECT_OPTIONS)
    async def choose(self, interaction: discord.Interaction, select: discord.ui.Select):
        self.index = KEYS.index(select.values[0])
        await interaction.response.edit_message(embed=make_embed(self.index), view=self)

    @discord.ui.button(emoji="◀️", style=discord.ButtonStyle.primary)
    async def prev_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        n = len(KEYS)
        self.index = n - 1 if self.index is None else (self.index - 1) % n
        await interaction.response.edit_message(embed=make_embed(self.index), view=self)

    @discord.ui.button(emoji="🏠", style=discord.ButtonStyle.secondary)
    async def home_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.index = None
        await interaction.response.edit_message(embed=make_embed(self.index), view=self)

    @discord.ui.button(emoji="▶️", style=discord.ButtonStyle.primary)
    async def next_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        n = len(KEYS)
        self.index = 0 if self.index is None else (self.index + 1) % n
        await interaction.response.edit_message(embed=make_embed(self.index), view=self)


# ============================================================
# BOT
# ============================================================
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.voice_states = True
intents.reactions = True

bot = commands.Bot(command_prefix=PREFIX, intents=intents, help_command=None)


@tasks.loop(seconds=60)
async def check_tempbans():
    """Débannit automatiquement les tempbans arrivés à échéance."""
    now = time.time()
    remaining = []
    for t in DATA["tempbans"]:
        if t["until"] <= now:
            guild = bot.get_guild(t["gid"])
            if guild:
                try:
                    await guild.unban(discord.Object(id=t["uid"]), reason="Fin du tempban")
                except discord.HTTPException:
                    pass
        else:
            remaining.append(t)
    if len(remaining) != len(DATA["tempbans"]):
        DATA["tempbans"] = remaining
        save()


@bot.event
async def on_ready():
    print(f"[OK] Connecté en tant que {bot.user} ({len(bot.guilds)} serveur(s))")
    if not check_tempbans.is_running():
        check_tempbans.start()
    # Applique la blacklist globale sur tous les serveurs du bot
    for uid, entry in DATA["blacklist"].items():
        for guild in bot.guilds:
            try:
                await guild.ban(discord.Object(id=int(uid)), reason=f"Blacklist : {entry['reason']}")
            except discord.HTTPException:
                pass


@bot.event
async def on_member_join(member: discord.Member):
    if str(member.id) in DATA["blacklist"]:
        try:
            await member.ban(reason="Blacklist du bot")
        except discord.HTTPException:
            pass


@bot.event
async def on_member_update(before: discord.Member, after: discord.Member):
    gid, uid = str(after.guild.id), str(after.id)

    # Pseudo verrouillé
    locked = DATA["lockednames"].get(gid, {}).get(uid)
    if locked is not None and after.nick != locked:
        try:
            await after.edit(nick=locked, reason="Pseudo verrouillé")
        except discord.HTTPException:
            pass

    # Blacklist rank : retire les rôles interdits
    cfg = get_blrank(after.guild.id)
    if cfg["enabled"] and after.id in cfg["members"]:
        added = [r for r in after.roles if r not in before.roles and r != after.guild.default_role]
        for role in added:
            dangerous = any(getattr(role.permissions, p) for p in DANGEROUS_PERMS)
            if cfg["mode"] == "all" or dangerous:
                try:
                    await after.remove_roles(role, reason="Blacklist rank")
                except discord.HTTPException:
                    pass


@bot.event
async def on_raw_reaction_add(payload: discord.RawReactionActionEvent):
    await _vote(payload, +1)


@bot.event
async def on_raw_reaction_remove(payload: discord.RawReactionActionEvent):
    await _vote(payload, -1)


async def _vote(payload, delta: int):
    if payload.guild_id is None or payload.user_id == bot.user.id or str(payload.emoji) != "👍":
        return
    for s in DATA["suggestions"].get(str(payload.guild_id), []):
        if s["msg_id"] == payload.message_id:
            s["up"] = max(0, s["up"] + delta)
            save()
            return


@bot.event
async def on_message_delete(message: discord.Message):
    if message.guild and not message.author.bot:
        snipes[message.channel.id] = (message.content, message.author, time.time())


async def antiraid_check(message: discord.Message) -> bool:
    """Retourne True si le message a été traité par l'antiraid."""
    member = message.author
    if not isinstance(member, discord.Member) or is_exempt(member):
        return False
    cfg = get_antiraid(message.guild.id)

    # Salon piège
    if cfg["piege"] and message.channel.id == cfg["piege"]:
        try:
            await message.delete()
            await member.ban(reason="Salon piège (antiraid)")
        except discord.HTTPException:
            pass
        return True

    # Antiphish : liens postés par un compte de moins de 7 jours
    if cfg["antiphish"] and "http" in message.content.lower():
        age = discord.utils.utcnow() - member.created_at
        if age < timedelta(days=7):
            try:
                await message.delete()
                await member.timeout(discord.utils.utcnow() + timedelta(hours=1), reason="Antiphish")
            except discord.HTTPException:
                pass
            return True

    # Doublons : 3 messages identiques en moins de 10 secondes
    if cfg["doublons"]:
        key = f"{message.guild.id}:{member.id}"
        now = time.time()
        history = [(c, t) for c, t in recent_msgs.get(key, []) if now - t < 10]
        history.append((message.content, now))
        recent_msgs[key] = history[-5:]
        same = [c for c, _ in history if c == message.content]
        if len(same) >= 3:
            try:
                await message.delete()
                await member.timeout(discord.utils.utcnow() + timedelta(minutes=10), reason="Spam (doublons)")
            except discord.HTTPException:
                pass
            return True
    return False


@bot.event
async def on_message(message: discord.Message):
    if message.guild and not message.author.bot:
        if await antiraid_check(message):
            return
    await bot.process_commands(message)


@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        return
    if isinstance(error, commands.MissingPermissions):
        await ctx.send(embed=err("Tu n'as pas la permission pour cette commande."))
    elif isinstance(error, commands.CheckFailure):
        await ctx.send(embed=err("Cette commande est réservée aux propriétaires du bot."))
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(embed=err(f"Argument manquant. Regarde `{PREFIX}help`."))
    elif isinstance(error, (commands.BadArgument, commands.MemberNotFound, commands.UserNotFound)):
        await ctx.send(embed=err(f"Argument invalide. Regarde `{PREFIX}help`."))
    elif isinstance(error, discord.Forbidden):
        await ctx.send(embed=err("Je n'ai pas les permissions (vérifie la hiérarchie des rôles)."))
    else:
        print(f"[ERREUR] {error}")


# ============================================================
# MENU D'AIDE
# ============================================================
@bot.command(name="help")
async def help_cmd(ctx: commands.Context, *, sujet: str = None):
    if sujet is None:
        return await ctx.send(embed=home_embed(), view=HelpView(ctx.author.id))
    key = sujet.lower()
    for k, c in CATEGORIES.items():
        if key in (k, c["label"].lower()):
            return await ctx.send(embed=category_embed(k))
    for c in CATEGORIES.values():
        for cmd, desc in c["commands"]:
            if cmd.split(" ")[0].lower() == key.split(" ")[0]:
                return await ctx.send(embed=footer(discord.Embed(
                    title=f"{PREFIX}{cmd}", description=desc, color=EMBED_COLOR)))
    await ctx.send(embed=err(f"Aucune commande ou catégorie « {sujet} »."))


# ============================================================
# MODÉRATION
# ============================================================
@bot.command(name="sanctions")
@commands.has_permissions(manage_messages=True)
async def sanctions(ctx, membre: discord.Member):
    items = sanction_list(ctx.guild.id, membre.id)
    if not items:
        return await ctx.send(embed=ok(f"{membre} n'a aucune sanction."))
    lines = [
        f"**{i}.** `{s['type']}` — {s['reason']} *({datetime.fromtimestamp(s['date']):%d/%m/%Y %H:%M})*"
        for i, s in enumerate(items, 1)
    ]
    await ctx.send(embed=discord.Embed(title=f"Sanctions de {membre}", description="\n".join(lines)[:4096], color=EMBED_COLOR))


@bot.group(name="del", invoke_without_command=True)
async def del_group(ctx):
    await ctx.send(embed=simple_embed(f"Utilise `{PREFIX}del sanction <membre> <numéro/all>`."))


@del_group.command(name="sanction")
@commands.has_permissions(manage_messages=True)
async def del_sanction(ctx, membre: discord.Member, numero: str):
    items = sanction_list(ctx.guild.id, membre.id)
    if numero.lower() == "all":
        items.clear()
    else:
        if not numero.isdigit() or not (1 <= int(numero) <= len(items)):
            return await ctx.send(embed=err("Numéro de sanction invalide."))
        items.pop(int(numero) - 1)
    save()
    await ctx.send(embed=ok("Sanction(s) supprimée(s)."))


@bot.group(name="clear", invoke_without_command=True)
@commands.has_permissions(manage_messages=True)
async def clear(ctx, nombre: int = 10, membre: discord.Member = None):
    nombre = max(1, min(nombre, 500))

    def check(m: discord.Message) -> bool:
        return membre is None or m.author.id == membre.id

    deleted = await ctx.channel.purge(limit=nombre, check=check, before=ctx.message)
    await ctx.send(embed=ok(f"{len(deleted)} message(s) supprimé(s)."), delete_after=5)


@clear.command(name="sanctions")
@commands.has_permissions(manage_messages=True)
async def clear_sanctions(ctx, membre: discord.Member):
    DATA["sanctions"].get(str(ctx.guild.id), {}).pop(str(membre.id), None)
    save()
    await ctx.send(embed=ok(f"Sanctions de {membre} supprimées."))


@clear.command(name="blrank")
@commands.has_permissions(manage_roles=True)
async def clear_blrank(ctx):
    get_blrank(ctx.guild.id)["members"] = []
    save()
    await ctx.send(embed=ok("Blacklist rank vidée."))


@bot.group(name="note", invoke_without_command=True)
@commands.has_permissions(manage_messages=True)
async def note(ctx, membre: discord.Member, *, raison: str = "Aucune raison"):
    DATA["notes"].setdefault(str(ctx.guild.id), {}).setdefault(str(membre.id), []).append({
        "raison": raison, "mod": str(ctx.author.id), "date": time.time(),
    })
    save()
    await ctx.send(embed=ok(f"Note ajoutée à {membre}."))


@note.command(name="delete")
@commands.has_permissions(manage_messages=True)
async def note_delete(ctx, cible: str, nombre: str = None):
    gid = str(ctx.guild.id)
    if cible.lower() == "all" and nombre is None:
        DATA["notes"][gid] = {}
        save()
        return await ctx.send(embed=ok("Toutes les notes du serveur ont été supprimées."))
    membre = await commands.MemberConverter().convert(ctx, cible)
    lst = DATA["notes"].get(gid, {}).get(str(membre.id), [])
    if nombre is None or nombre.lower() == "all":
        lst.clear()
    elif nombre.isdigit() and 1 <= int(nombre) <= len(lst):
        lst.pop(int(nombre) - 1)
    else:
        return await ctx.send(embed=err("Numéro de note invalide."))
    save()
    await ctx.send(embed=ok(f"Note(s) de {membre} supprimée(s)."))


@bot.command(name="warn")
@commands.has_permissions(kick_members=True)
async def warn(ctx, membre: discord.Member, *, raison: str = "Aucune raison"):
    add_sanction(ctx.guild.id, membre.id, "warn", raison, ctx.author.id)
    await ctx.send(embed=simple_embed(f"⚠️ {membre} a reçu un warn.\nRaison : {raison}", 0xFEE75C))


@bot.command(name="mute")
@commands.has_permissions(moderate_members=True)
async def mute(ctx, membre: discord.Member, *, raison: str = "Aucune raison"):
    await membre.timeout(discord.utils.utcnow() + timedelta(seconds=MAX_TIMEOUT), reason=raison)
    add_sanction(ctx.guild.id, membre.id, "mute", raison, ctx.author.id)
    await ctx.send(embed=simple_embed(f"🔇 {membre} a été mute.\nRaison : {raison}"))


@bot.command(name="unmute")
@commands.has_permissions(moderate_members=True)
async def unmute(ctx, membre: discord.Member):
    await membre.timeout(None, reason=f"Unmute par {ctx.author}")
    await ctx.send(embed=ok(f"{membre} n'est plus mute."))


@bot.command(name="tempmute")
@commands.has_permissions(moderate_members=True)
async def tempmute(ctx, membre: discord.Member, duree: str, *, raison: str = "Aucune raison"):
    secondes = parse_duration(duree)
    if not secondes:
        return await ctx.send(embed=err("Durée invalide (ex : `10m`, `2h`, `1d`)."))
    secondes = min(secondes * (1 if duree[-1].isalpha() else 60), MAX_TIMEOUT)
    await membre.timeout(discord.utils.utcnow() + timedelta(seconds=secondes), reason=raison)
    add_sanction(ctx.guild.id, membre.id, f"tempmute {duree}", raison, ctx.author.id)
    await ctx.send(embed=simple_embed(f"🔇 {membre} mute pour {duree}.\nRaison : {raison}"))


@bot.command(name="kick")
@commands.has_permissions(kick_members=True)
async def kick(ctx, membre: discord.Member, *, raison: str = "Aucune raison"):
    await membre.kick(reason=f"{ctx.author} : {raison}")
    add_sanction(ctx.guild.id, membre.id, "kick", raison, ctx.author.id)
    await ctx.send(embed=simple_embed(f"👢 {membre} a été expulsé.\nRaison : {raison}"))


@bot.command(name="ban")
@commands.has_permissions(ban_members=True)
async def ban(ctx, membre: discord.Member, *, raison: str = "Aucune raison"):
    await membre.ban(reason=f"{ctx.author} : {raison}")
    add_sanction(ctx.guild.id, membre.id, "ban", raison, ctx.author.id)
    await ctx.send(embed=simple_embed(f"🔨 {membre} a été banni.\nRaison : {raison}"))


@bot.command(name="tempban")
@commands.has_permissions(ban_members=True)
async def tempban(ctx, membre: discord.Member, duree: str, *, raison: str = "Aucune raison"):
    secondes = parse_duration(duree)
    if not secondes:
        return await ctx.send(embed=err("Durée invalide (ex : `10m`, `2h`, `1d`)."))
    secondes = secondes * (1 if duree[-1].isalpha() else 60)
    await membre.ban(reason=f"Tempban {duree} : {raison}")
    DATA["tempbans"].append({"gid": ctx.guild.id, "uid": membre.id, "until": time.time() + secondes})
    add_sanction(ctx.guild.id, membre.id, f"tempban {duree}", raison, ctx.author.id)
    await ctx.send(embed=simple_embed(f"🔨 {membre} est banni pour {duree}.\nRaison : {raison}"))


@bot.command(name="unban")
@commands.has_permissions(ban_members=True)
async def unban(ctx, cible: str):
    user = await fetch_user_from(cible)
    await ctx.guild.unban(discord.Object(id=user.id), reason=f"Unban par {ctx.author}")
    DATA["tempbans"] = [t for t in DATA["tempbans"] if not (t["gid"] == ctx.guild.id and t["uid"] == user.id)]
    save()
    await ctx.send(embed=ok(f"Bannissement retiré pour {user}."))


@bot.command(name="banlist")
@commands.has_permissions(ban_members=True)
async def banlist(ctx):
    entries = [e async for e in ctx.guild.bans(limit=20)]
    if not entries:
        return await ctx.send(embed=simple_embed("Aucun bannissement en cours."))
    lines = [f"`{e.user.id}` **{e.user}** — {e.reason or 'Aucune raison'}" for e in entries]
    await ctx.send(embed=discord.Embed(title="🔨 Bannissements", description="\n".join(lines), color=EMBED_COLOR))


@bot.command(name="addrole")
@commands.has_permissions(manage_roles=True)
async def addrole(ctx, membre: discord.Member, *, roles: str):
    found = [resolve_role(ctx.guild, r) for r in roles.split(",") if r.strip()]
    found = [r for r in found if r]
    if not found:
        return await ctx.send(embed=err("Aucun rôle reconnu."))
    await membre.add_roles(*found, reason=f"Par {ctx.author}")
    await ctx.send(embed=ok(f"Rôle(s) ajouté(s) à {membre}."))


@bot.command(name="delrole")
@commands.has_permissions(manage_roles=True)
async def delrole(ctx, membre: discord.Member, *, roles: str):
    found = [resolve_role(ctx.guild, r) for r in roles.split(",") if r.strip()]
    found = [r for r in found if r]
    if not found:
        return await ctx.send(embed=err("Aucun rôle reconnu."))
    await membre.remove_roles(*found, reason=f"Par {ctx.author}")
    await ctx.send(embed=ok(f"Rôle(s) retiré(s) à {membre}."))


@bot.command(name="derank")
@commands.has_permissions(manage_roles=True)
async def derank(ctx, membre: discord.Member):
    roles = [r for r in membre.roles if r != ctx.guild.default_role and not r.managed]
    if roles:
        await membre.remove_roles(*roles, reason=f"Derank par {ctx.author}")
    await ctx.send(embed=ok(f"Rôles de {membre} retirés."))


@bot.command(name="nick")
@commands.has_permissions(manage_nicknames=True)
async def nick(ctx, membre: discord.Member, *, pseudo: str):
    await membre.edit(nick=pseudo)
    await ctx.send(embed=ok(f"Pseudo de {membre} changé en **{pseudo}**."))


@bot.command(name="lockname")
@commands.has_permissions(manage_nicknames=True)
async def lockname(ctx, membre: discord.Member):
    DATA["lockednames"].setdefault(str(ctx.guild.id), {})[str(membre.id)] = membre.nick or membre.name
    save()
    await ctx.send(embed=ok(f"Pseudo de {membre} verrouillé."))


@bot.command(name="unlockname")
@commands.has_permissions(manage_nicknames=True)
async def unlockname(ctx, membre: discord.Member):
    DATA["lockednames"].get(str(ctx.guild.id), {}).pop(str(membre.id), None)
    save()
    await ctx.send(embed=ok(f"Pseudo de {membre} déverrouillé."))


@bot.command(name="locknamelist")
@commands.has_permissions(manage_nicknames=True)
async def locknamelist(ctx):
    locks = DATA["lockednames"].get(str(ctx.guild.id), {})
    if not locks:
        return await ctx.send(embed=simple_embed("Aucun pseudo verrouillé."))
    lines = [f"<@{uid}> → **{name}**" for uid, name in locks.items()]
    await ctx.send(embed=discord.Embed(title="🔒 Pseudos verrouillés", description="\n".join(lines), color=EMBED_COLOR))


# ============================================================
# CONFIGURATION / GESTION
# ============================================================
@bot.command(name="perms")
@commands.has_permissions(manage_guild=True)
async def perms(ctx):
    lines = []
    for role in ctx.guild.roles:
        if role == ctx.guild.default_role:
            continue
        flags = [p.replace("_", " ") for p in DANGEROUS_PERMS if getattr(role.permissions, p)]
        if flags:
            lines.append(f"{role.mention} — {', '.join(flags)}")
    await ctx.send(embed=discord.Embed(
        title="⚙️ Rôles sensibles", description="\n".join(lines)[:4096] or "Aucun rôle sensible.", color=EMBED_COLOR))


@bot.command(name="voicekick")
@commands.has_permissions(move_members=True)
async def voicekick(ctx, membre: discord.Member):
    if not membre.voice:
        return await ctx.send(embed=err(f"{membre} n'est dans aucun salon vocal."))
    await membre.move_to(None, reason=f"Voicekick par {ctx.author}")
    await ctx.send(embed=ok(f"{membre} a été déconnecté du vocal."))


# ============================================================
# ANTIRAID
# ============================================================
@bot.command(name="antiraid")
@commands.has_permissions(administrator=True)
async def antiraid(ctx, option: str = None, valeur: str = None):
    cfg = get_antiraid(ctx.guild.id)
    if option is None:
        piege = f"<#{cfg['piege']}>" if cfg["piege"] else "désactivé"
        return await ctx.send(embed=footer(discord.Embed(
            title="🚨 Antiraid",
            description=(f"**Antiphish** : {'on' if cfg['antiphish'] else 'off'}\n"
                         f"**Doublons** : {'on' if cfg['doublons'] else 'off'}\n"
                         f"**Salon piège** : {piege}"),
            color=EMBED_COLOR)))

    option = option.lower()
    if option in ("antiphish", "doublons"):
        if valeur not in ("on", "off"):
            return await ctx.send(embed=err("Utilise `on` ou `off`."))
        cfg[option] = valeur == "on"
    elif option == "piege":
        if valeur is None or valeur.lower() == "off":
            cfg["piege"] = None
        else:
            m = re.search(r"\d{15,20}", valeur)
            if not m or not ctx.guild.get_channel(int(m.group())):
                return await ctx.send(embed=err("Salon introuvable."))
            cfg["piege"] = int(m.group())
    else:
        return await ctx.send(embed=err("Option inconnue : `antiphish`, `doublons` ou `piege`."))
    save()
    await ctx.send(embed=ok("Antiraid mis à jour."))


@bot.group(name="blrank", invoke_without_command=True)
async def blrank(ctx):
    cfg = get_blrank(ctx.guild.id)
    members = "\n".join(f"<@{uid}>" for uid in cfg["members"]) or "Aucun membre."
    await ctx.send(embed=footer(discord.Embed(
        title="🚫 Blacklist rank",
        description=(f"**Statut** : {'on' if cfg['enabled'] else 'off'}\n"
                     f"**Mode** : {cfg['mode']}\n\n{members}"),
        color=EMBED_COLOR)))


@blrank.command(name="on")
@commands.has_permissions(manage_roles=True)
async def blrank_on(ctx):
    get_blrank(ctx.guild.id)["enabled"] = True
    save()
    await ctx.send(embed=ok("Blacklist rank activée."))


@blrank.command(name="off")
@commands.has_permissions(manage_roles=True)
async def blrank_off(ctx):
    get_blrank(ctx.guild.id)["enabled"] = False
    save()
    await ctx.send(embed=ok("Blacklist rank désactivée."))


@blrank.command(name="danger")
@commands.has_permissions(manage_roles=True)
async def blrank_danger(ctx):
    get_blrank(ctx.guild.id)["mode"] = "danger"
    save()
    await ctx.send(embed=ok("Mode : rôles dangereux seulement."))


@blrank.command(name="all")
@commands.has_permissions(manage_roles=True)
async def blrank_all(ctx):
    get_blrank(ctx.guild.id)["mode"] = "all"
    save()
    await ctx.send(embed=ok("Mode : tous les rôles."))


@blrank.command(name="add")
@commands.has_permissions(manage_roles=True)
async def blrank_add(ctx, membre: discord.Member):
    cfg = get_blrank(ctx.guild.id)
    if membre.id not in cfg["members"]:
        cfg["members"].append(membre.id)
    save()
    await ctx.send(embed=ok(f"{membre} ajouté à la blacklist rank."))


@blrank.command(name="del")
@commands.has_permissions(manage_roles=True)
async def blrank_del(ctx, membre: discord.Member):
    cfg = get_blrank(ctx.guild.id)
    if membre.id in cfg["members"]:
        cfg["members"].remove(membre.id)
    save()
    await ctx.send(embed=ok(f"{membre} retiré de la blacklist rank."))


# ============================================================
# CONTRÔLE DU BOT (propriétaires)
# ============================================================
@bot.group(name="bl", invoke_without_command=True)
@owner_only()
async def bl(ctx, cible: str = None, *, raison: str = "Aucune raison"):
    if cible is None:
        if not DATA["blacklist"]:
            return await ctx.send(embed=simple_embed("La blacklist du bot est vide."))
        lines = [f"`{uid}` — {e['reason']}" for uid, e in list(DATA["blacklist"].items())[:30]]
        return await ctx.send(embed=discord.Embed(title="🚫 Blacklist du bot", description="\n".join(lines), color=EMBED_COLOR))
    user = await fetch_user_from(cible)
    DATA["blacklist"][str(user.id)] = {"reason": raison, "by": str(ctx.author.id), "date": time.time()}
    save()
    banned = 0
    for guild in bot.guilds:
        try:
            await guild.ban(discord.Object(id=user.id), reason=f"Blacklist : {raison}")
            banned += 1
        except discord.HTTPException:
            pass
    await ctx.send(embed=ok(f"{user} blacklisté et banni sur {banned} serveur(s)."))


@bot.command(name="unbl")
@owner_only()
async def unbl(ctx, cible: str):
    user = await fetch_user_from(cible)
    if DATA["blacklist"].pop(str(user.id), None) is None:
        return await ctx.send(embed=err("Cet utilisateur n'est pas blacklisté."))
    save()
    for guild in bot.guilds:
        try:
            await guild.unban(discord.Object(id=user.id), reason="Retiré de la blacklist")
        except discord.HTTPException:
            pass
    await ctx.send(embed=ok(f"{user} retiré de la blacklist."))


@bot.command(name="blinfo")
@owner_only()
async def blinfo(ctx, cible: str):
    user = await fetch_user_from(cible)
    entry = DATA["blacklist"].get(str(user.id))
    if not entry:
        return await ctx.send(embed=simple_embed(f"{user} n'est pas blacklisté."))
    await ctx.send(embed=discord.Embed(
        title=f"Blacklist — {user}",
        description=(f"**Raison** : {entry['reason']}\n"
                     f"**Ajouté par** : <@{entry['by']}>\n"
                     f"**Date** : {datetime.fromtimestamp(entry['date']):%d/%m/%Y %H:%M}"),
        color=EMBED_COLOR))


# ============================================================
# UTILITAIRE
# ============================================================
@bot.command(name="pic")
async def pic(ctx, membre: discord.Member = None):
    membre = membre or ctx.author
    embed = discord.Embed(title=f"Avatar de {membre}", color=EMBED_COLOR)
    embed.set_image(url=membre.display_avatar.url)
    await ctx.send(embed=embed)


@bot.command(name="banner")
async def banner(ctx, membre: discord.Member = None):
    membre = membre or ctx.author
    user = await bot.fetch_user(membre.id)
    if not user.banner:
        return await ctx.send(embed=simple_embed(f"{membre} n'a pas de bannière."))
    embed = discord.Embed(title=f"Bannière de {membre}", color=EMBED_COLOR)
    embed.set_image(url=user.banner.url)
    await ctx.send(embed=embed)


@bot.group(name="server", invoke_without_command=True)
async def server(ctx):
    await ctx.send(embed=simple_embed(f"Utilise `{PREFIX}server pic` ou `{PREFIX}server banner`."))


@server.command(name="pic")
async def server_pic(ctx):
    if not ctx.guild.icon:
        return await ctx.send(embed=simple_embed("Ce serveur n'a pas d'icône."))
    embed = discord.Embed(title=f"Icône de {ctx.guild.name}", color=EMBED_COLOR)
    embed.set_image(url=ctx.guild.icon.url)
    await ctx.send(embed=embed)


@server.command(name="banner")
async def server_banner(ctx):
    if not ctx.guild.banner:
        return await ctx.send(embed=simple_embed("Ce serveur n'a pas de bannière."))
    embed = discord.Embed(title=f"Bannière de {ctx.guild.name}", color=EMBED_COLOR)
    embed.set_image(url=ctx.guild.banner.url)
    await ctx.send(embed=embed)


@bot.command(name="emoji")
async def emoji(ctx, emoji_str: str):
    match = re.match(r"<(a?):(\w+):(\d+)>", emoji_str)
    if not match:
        return await ctx.send(embed=simple_embed("Donne un émoji personnalisé du serveur."))
    animated, name, eid = match.groups()
    ext = "gif" if animated else "png"
    embed = discord.Embed(title=f":{name}:", color=EMBED_COLOR)
    embed.set_image(url=f"https://cdn.discordapp.com/emojis/{eid}.{ext}?size=256")
    await ctx.send(embed=embed)


@bot.command(name="snipe")
async def snipe(ctx):
    data = snipes.get(ctx.channel.id)
    if not data:
        return await ctx.send(embed=simple_embed("Rien à sniper dans ce salon."))
    content, author, ts = data
    embed = discord.Embed(description=content or "*(vide)*", color=EMBED_COLOR, timestamp=datetime.fromtimestamp(ts))
    embed.set_author(name=str(author), icon_url=author.display_avatar.url)
    await ctx.send(embed=embed)


@bot.command(name="image")
async def image(ctx, *, mot: str):
    url = f"https://www.google.com/search?tbm=isch&q={quote(mot)}"
    await ctx.send(embed=simple_embed(f"🔎 Recherche d'images pour **{mot}** :\n{url}"))


@bot.command(name="suggestion")
async def suggestion(ctx, *, message: str):
    embed = footer(discord.Embed(title="💡 Suggestion", description=message, color=EMBED_COLOR))
    embed.set_author(name=str(ctx.author), icon_url=ctx.author.display_avatar.url)
    msg = await ctx.send(embed=embed)
    await msg.add_reaction("👍")
    await msg.add_reaction("👎")
    DATA["suggestions"].setdefault(str(ctx.guild.id), []).append({
        "msg_id": msg.id, "author": str(ctx.author.id), "content": message, "up": 0,
    })
    save()


@bot.group(name="lb", invoke_without_command=True)
async def lb(ctx):
    await ctx.send(embed=simple_embed(f"Utilise `{PREFIX}lb suggestions`."))


@lb.command(name="suggestions")
async def lb_suggestions(ctx):
    items = sorted(DATA["suggestions"].get(str(ctx.guild.id), []), key=lambda s: s["up"], reverse=True)[:10]
    if not items:
        return await ctx.send(embed=simple_embed("Aucune suggestion pour le moment."))
    lines = [f"**{i}.** 👍 {s['up']} — {s['content'][:80]} (<@{s['author']}>)" for i, s in enumerate(items, 1)]
    await ctx.send(embed=discord.Embed(title="🏆 Meilleures suggestions", description="\n".join(lines), color=EMBED_COLOR))


@bot.command(name="wiki")
async def wiki(ctx, *, mot: str):
    url = f"https://fr.wikipedia.org/api/rest_v1/page/summary/{quote(mot)}"
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers={"User-Agent": f"{BOT_NAME}/1.0"}) as resp:
            if resp.status != 200:
                return await ctx.send(embed=err(f"Aucun article trouvé pour « {mot} »."))
            data = await resp.json()
    embed = discord.Embed(title=data.get("title", mot), description=data.get("extract", "")[:900], color=EMBED_COLOR)
    page = data.get("content_urls", {}).get("desktop", {}).get("page")
    if page:
        embed.url = page
    await ctx.send(embed=footer(embed))


_OPS = {
    ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul,
    ast.Div: operator.truediv, ast.FloorDiv: operator.floordiv, ast.Mod: operator.mod,
    ast.Pow: operator.pow, ast.USub: operator.neg, ast.UAdd: operator.pos,
}


def _safe_eval(node):
    if isinstance(node, ast.Expression):
        return _safe_eval(node.body)
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return node.value
    if isinstance(node, ast.BinOp) and type(node.op) in _OPS:
        right = _safe_eval(node.right)
        if isinstance(node.op, ast.Pow) and abs(right) > 1000:
            raise ValueError("Exposant trop grand")
        return _OPS[type(node.op)](_safe_eval(node.left), right)
    if isinstance(node, ast.UnaryOp) and type(node.op) in _OPS:
        return _OPS[type(node.op)](_safe_eval(node.operand))
    raise ValueError("Expression non autorisée")


@bot.command(name="calc")
async def calc(ctx, *, expression: str):
    expr = expression.replace("×", "*").replace("÷", "/").replace("^", "**").replace(",", ".")
    try:
        result = _safe_eval(ast.parse(expr, mode="eval"))
    except (ValueError, SyntaxError, ZeroDivisionError, TypeError) as e:
        return await ctx.send(embed=err(f"Calcul impossible : {e}"))
    await ctx.send(embed=discord.Embed(title="🧮 Calcul", description=f"`{expression}` = **{result}**", color=EMBED_COLOR))


# ============================================================
# MINI SITE WEB (pour Render)
# ============================================================
app = Flask(__name__)


@app.route("/")
def home():
    online = bot.is_ready()
    guilds = len(bot.guilds) if online else 0
    status_text = "En ligne" if online else "Démarrage..."
    dot_color = "#23a55a" if online else "#f23f43"
    return f"""<!doctype html>
<html lang="fr">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{BOT_NAME}</title>
  <style>
    body {{ background:#1e1f22; color:#dbdee1; font-family:system-ui,sans-serif;
            display:flex; min-height:100vh; align-items:center; justify-content:center; margin:0; }}
    .card {{ background:#2b2d31; padding:32px; border-radius:12px; text-align:center; max-width:360px; }}
    .dot {{ display:inline-block; width:10px; height:10px; border-radius:50%;
            background:{dot_color}; margin-right:6px; }}
  </style>
</head>
<body>
  <div class="card">
    <h1>{BOT_NAME}</h1>
    <p><span class="dot"></span>{status_text}</p>
    <p>{guilds} serveur(s)</p>
  </div>
</body>
</html>"""


@app.route("/health")
def health():
    return "ok", 200


def run_web():
    app.run(host="0.0.0.0", port=PORT)


# ============================================================
# MAIN
# ============================================================
if __name__ == "__main__":
    if not TOKEN:
        raise SystemExit("❌ Variable d'environnement DISCORD_TOKEN manquante.")
    threading.Thread(target=run_web, daemon=True).start()
    bot.run(TOKEN)
