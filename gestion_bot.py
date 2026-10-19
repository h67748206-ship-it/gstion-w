"""
gestion_bot.py - Bot de gestion pour le serveur Yuu
Préfixe : +        Aide : +help   (ou +help <catégorie> / +help <commande>)
Installation : pip install -U discord.py
Lancement    : export DISCORD_TOKEN="ton_token"  puis  python gestion_bot.py
"""
import asyncio
import datetime
import json
import os
import re
import time
import urllib.parse
import urllib.request
from collections import defaultdict, deque

import discord
from discord.ext import commands

TOKEN = os.getenv("DISCORD_TOKEN")  # ne jamais écrire le token dans le code
PREFIX = "+"
CONFIG_FILE = "config.json"
WARNS_FILE = "warns.json"


def load_json(path, default):
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return default


def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


config = load_json(CONFIG_FILE, {})
warns = load_json(WARNS_FILE, {})
MSG_FILE = "msgstats.json"
msg_stats = load_json(MSG_FILE, {})  # {guild_id: {channel_id: nombre_de_messages}}

intents = discord.Intents.default()
intents.members = True
intents.message_content = True

bot = commands.Bot(command_prefix=PREFIX, intents=intents, help_command=None)

# Emojis personnalisés par catégorie (rendus par Discord si le bot a accès au serveur de l'emoji)
CATEGORY_EMOJIS = {
    "Configuration": "<:Crown:1561379407195545641>",
    "Salons": "<:lock:1561379416414879777>",
    "Modération": "<:b_DiscordModerateur:1561379409355739239>",
    "Utilitaires": "<:b_DiscordStaff:1561379413902233673>",
    "Protection": "<:1462041546160472095:1561379419178672158>",
    "Statistiques": "📊",
    "Outils": "🛠️",
    "Gestion": "🧩",
    "Modération avancée": "🔨",
    "Recherche & infos": "🌐",
    "Suggestions": "💡",
    "Antiraid & antihack": "🛡️",
}


async def log_action(guild, title, description, color=discord.Color.orange()):
    channel_id = config.get("log_channel")
    if not channel_id:
        return
    channel = guild.get_channel(channel_id)
    if channel:
        await channel.send(embed=discord.Embed(title=title, description=description, color=color))


def voice_targets(ctx, scope):
    """'all' = tous les vocaux, sinon le vocal où se trouve l'auteur (None si aucun)."""
    if scope == "all":
        return ctx.guild.voice_channels
    if ctx.author.voice and ctx.author.voice.channel:
        return [ctx.author.voice.channel]
    return None


# ---------------------------------------------------------------- CONFIG

class Configuration(commands.Cog):
    """⚙️ Configuration"""

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def setlog(self, ctx, channel: discord.TextChannel):
        """Définit le salon des logs de modération."""
        config["log_channel"] = channel.id
        save_json(CONFIG_FILE, config)
        await ctx.send(f"✅ Salon de logs : {channel.mention}")

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def setwelcome(self, ctx, channel: discord.TextChannel):
        """Définit le salon de bienvenue."""
        config["welcome_channel"] = channel.id
        save_json(CONFIG_FILE, config)
        await ctx.send(f"✅ Salon de bienvenue : {channel.mention}")


# ---------------------------------------------------------------- SALONS

class Salons(commands.Cog):
    """🔐 Salons"""

    @commands.command()
    @commands.has_permissions(manage_channels=True)
    async def hideall(self, ctx):
        """Masque tous les salons pour @everyone."""
        await ctx.send("🙈 Masquage de tous les salons...")
        for channel in ctx.guild.channels:
            await channel.set_permissions(ctx.guild.default_role, view_channel=False,
                                          reason=f"hideall par {ctx.author}")
        await ctx.send("🙈 Tous les salons sont masqués pour @everyone.")

    @commands.command()
    @commands.has_permissions(manage_channels=True)
    async def showall(self, ctx):
        """Réaffiche tous les salons pour @everyone."""
        await ctx.send("👀 Réaffichage de tous les salons...")
        for channel in ctx.guild.channels:
            await channel.set_permissions(ctx.guild.default_role, view_channel=None,
                                          reason=f"showall par {ctx.author}")
        await ctx.send("👀 Tous les salons sont réaffichés pour @everyone.")

    @commands.command()
    @commands.has_permissions(manage_channels=True)
    async def lock(self, ctx):
        """Verrouille le salon texte pour @everyone."""
        await ctx.channel.set_permissions(ctx.guild.default_role, send_messages=False)
        await ctx.send("🔒 Salon verrouillé.")

    @commands.command()
    @commands.has_permissions(manage_channels=True)
    async def unlock(self, ctx):
        """Déverrouille le salon texte pour @everyone."""
        await ctx.channel.set_permissions(ctx.guild.default_role, send_messages=None)
        await ctx.send("🔓 Salon déverrouillé.")

    @commands.command()
    @commands.has_permissions(manage_channels=True)
    async def lockvoc(self, ctx, scope: str = None):
        """Verrouille ton vocal, ou tous les vocaux avec +lockvoc all."""
        targets = voice_targets(ctx, scope)
        if targets is None:
            return await ctx.send(f"❌ Rejoins un vocal ou tape `{PREFIX}lockvoc all`.")
        for vc in targets:
            await vc.set_permissions(ctx.guild.default_role, connect=False)
        await ctx.send(f"🔒 {len(targets)} vocal(aux) verrouillé(s).")

    @commands.command()
    @commands.has_permissions(manage_channels=True)
    async def unlockvoc(self, ctx, scope: str = None):
        """Déverrouille ton vocal, ou tous les vocaux avec +unlockvoc all."""
        targets = voice_targets(ctx, scope)
        if targets is None:
            return await ctx.send(f"❌ Rejoins un vocal ou tape `{PREFIX}unlockvoc all`.")
        for vc in targets:
            await vc.set_permissions(ctx.guild.default_role, connect=None)
        await ctx.send(f"🔓 {len(targets)} vocal(aux) déverrouillé(s).")

    @commands.command()
    @commands.has_permissions(manage_channels=True)
    async def slowmode(self, ctx, seconds: int = 0):
        """Active le mode lent (0 pour désactiver), en secondes."""
        await ctx.channel.edit(slowmode_delay=seconds)
        await ctx.send(f"🐢 Mode lent : {seconds} s." if seconds else "🐇 Mode lent désactivé.")


# ---------------------------------------------------------------- MODÉRATION

class Moderation(commands.Cog):
    """🛡️ Modération"""

    @commands.command()
    @commands.has_permissions(kick_members=True)
    async def kick(self, ctx, member: discord.Member, *, reason="Aucune raison"):
        """Expulse un membre."""
        await member.kick(reason=reason)
        await ctx.send(f"👢 {member} a été expulsé. ({reason})")
        await log_action(ctx.guild, "Kick", f"{member} par {ctx.author}\nRaison : {reason}")

    @commands.command()
    @commands.has_permissions(ban_members=True)
    async def ban(self, ctx, member: discord.Member, *, reason="Aucune raison"):
        """Bannit un membre."""
        await member.ban(reason=reason)
        await ctx.send(f"🔨 {member} a été banni. ({reason})")
        await log_action(ctx.guild, "Ban", f"{member} par {ctx.author}\nRaison : {reason}",
                         discord.Color.red())

    @commands.command()
    @commands.has_permissions(ban_members=True)
    async def unban(self, ctx, user_id: int):
        """Débannit un utilisateur via son ID."""
        await ctx.guild.unban(discord.Object(id=user_id))
        await ctx.send(f"✅ Utilisateur {user_id} débanni.")

    @commands.command()
    @commands.has_permissions(moderate_members=True)
    async def timeout(self, ctx, member: discord.Member, minutes: int, *, reason="Aucune raison"):
        """Met un membre en timeout (mute) pendant X minutes."""
        until = discord.utils.utcnow() + datetime.timedelta(minutes=minutes)
        await member.timeout(until, reason=reason)
        await ctx.send(f"🔇 {member} est en timeout pour {minutes} min.")
        await log_action(ctx.guild, "Timeout", f"{member} ({minutes} min) par {ctx.author}\nRaison : {reason}")

    @commands.command(aliases=["unmute"])
    @commands.has_permissions(moderate_members=True)
    async def untimeout(self, ctx, member: discord.Member):
        """Retire le timeout d'un membre."""
        await member.timeout(None)
        await ctx.send(f"🔊 Timeout retiré pour {member}.")

    @commands.command()
    @commands.has_permissions(moderate_members=True)
    async def warn(self, ctx, members: commands.Greedy[discord.Member], *, reason="Aucune raison"):
        """Donne un avertissement à un ou plusieurs membres."""
        if not members:
            return await ctx.send("❌ Mentionne au moins un membre.")
        guild_warns = warns.setdefault(str(ctx.guild.id), {})
        now = datetime.datetime.utcnow().isoformat(timespec="minutes")
        for member in members:
            guild_warns.setdefault(str(member.id), []).append({
                "raison": reason, "par": ctx.author.id, "date": now,
            })
        save_json(WARNS_FILE, warns)
        await ctx.send(f"⚠️ Avertissement donné à {', '.join(m.mention for m in members)}.")
        await log_action(ctx.guild, "Warn", f"{', '.join(str(m) for m in members)} par {ctx.author}\nRaison : {reason}",
                         discord.Color.gold())

    @commands.command()
    async def warnings(self, ctx, member: discord.Member = None):
        """Affiche les avertissements d'un membre."""
        member = member or ctx.author
        items = warns.get(str(ctx.guild.id), {}).get(str(member.id), [])
        if not items:
            return await ctx.send(f"{member.display_name} n'a aucun avertissement.")
        lines = [f"**{i}.** {w['date']} - {w['raison']}" for i, w in enumerate(items, 1)]
        embed = discord.Embed(title=f"Avertissements de {member.display_name}",
                              description="\n".join(lines), color=discord.Color.gold())
        await ctx.send(embed=embed)

    @commands.command()
    @commands.has_permissions(moderate_members=True)
    async def clearwarns(self, ctx, member: discord.Member):
        """Supprime tous les avertissements d'un membre."""
        warns.get(str(ctx.guild.id), {}).pop(str(member.id), None)
        save_json(WARNS_FILE, warns)
        await ctx.send(f"🧽 Avertissements de {member.display_name} supprimés.")

    @commands.group(invoke_without_command=True)
    @commands.has_permissions(manage_messages=True)
    async def clear(self, ctx, amount: int = 10, member: discord.Member = None):
        """Supprime X messages, ou seulement ceux d'un membre. Sous-commandes : sanctions, blrank."""
        if member is None:
            deleted = await ctx.channel.purge(limit=amount + 1)
            return await ctx.send(f"🧹 {len(deleted) - 1} messages supprimés.", delete_after=3)
        deleted = await ctx.channel.purge(limit=min(amount, 200), check=lambda m: m.author == member)
        await ctx.send(f"🧹 {len(deleted)} message(s) de {member.display_name} supprimé(s).", delete_after=3)

    @clear.command(name="sanctions")
    @commands.has_permissions(moderate_members=True)
    async def clear_sanctions(self, ctx, member: discord.Member):
        """Supprime toutes les sanctions d'un membre."""
        warns.get(str(ctx.guild.id), {}).pop(str(member.id), None)
        save_json(WARNS_FILE, warns)
        await ctx.send(f"🧽 Sanctions de {member.display_name} supprimées.")

    @clear.command(name="blrank")
    @commands.has_permissions(manage_roles=True)
    async def clear_blrank(self, ctx):
        """Retire tous les membres de la blacklist rank."""
        blrank_state()["members"] = []
        save_json(CONFIG_FILE, config)
        await ctx.send("🧹 Blacklist rank vidée.")


# ---------------------------------------------------------------- UTILITAIRES

class Utility(commands.Cog):
    """🧰 Utilitaires"""

    @commands.command()
    async def ping(self, ctx):
        """Affiche la latence du bot."""
        await ctx.send(f"🏓 Pong ! {round(bot.latency * 1000)} ms")

    @commands.command()
    async def userinfo(self, ctx, member: discord.Member = None):
        """Affiche les infos d'un membre."""
        member = member or ctx.author
        embed = discord.Embed(title=str(member), color=member.color)
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.add_field(name="ID", value=member.id)
        embed.add_field(name="Compte créé", value=discord.utils.format_dt(member.created_at, "D"))
        embed.add_field(name="A rejoint", value=discord.utils.format_dt(member.joined_at, "D"))
        embed.add_field(name="Rôles", value=f"{len(member.roles) - 1}", inline=False)
        await ctx.send(embed=embed)

    @commands.command()
    async def serverinfo(self, ctx):
        """Affiche les infos du serveur."""
        g = ctx.guild
        embed = discord.Embed(title=g.name, color=discord.Color.blurple())
        if g.icon:
            embed.set_thumbnail(url=g.icon.url)
        embed.add_field(name="Membres", value=g.member_count)
        embed.add_field(name="Salons", value=len(g.channels))
        embed.add_field(name="Rôles", value=len(g.roles))
        embed.add_field(name="Créé le", value=discord.utils.format_dt(g.created_at, "D"))
        await ctx.send(embed=embed)

    @commands.command()
    async def avatar(self, ctx, member: discord.Member = None):
        """Affiche l'avatar d'un membre."""
        member = member or ctx.author
        embed = discord.Embed(title=f"Avatar de {member.display_name}", color=member.color)
        embed.set_image(url=member.display_avatar.url)
        await ctx.send(embed=embed)


# ---------------------------------------------------------------- PROTECTION

LINK_RE = re.compile(r"(https?://\S+|discord\.gg/\S+|www\.\S+)", re.IGNORECASE)
NUKE_LIMIT = 3       # nombre d'actions destructrices autorisées...
NUKE_WINDOW = 10     # ...dans cette fenêtre (secondes)
nuke_tracker = {}    # {(guild_id, user_id): [timestamps]}


def prot(guild_id):
    """Réglages de protection d'un serveur (créés au besoin)."""
    return config.setdefault("protection", {}).setdefault(
        str(guild_id), {"antilink": False, "antinuke": False, "whitelist": []})


def is_trusted(member):
    """Admins, gérants et membres whitelistés ne sont pas concernés par l'anti-link."""
    if member.guild_permissions.administrator or member.guild_permissions.manage_guild:
        return True
    return member.id in prot(member.guild.id)["whitelist"]


async def nuke_check(guild, action, label):
    cfg = prot(guild.id)
    if not cfg["antinuke"]:
        return
    entry = None
    async for e in guild.audit_logs(limit=1, action=action):
        entry = e
        break
    if entry is None or entry.user is None:
        return
    if discord.utils.utcnow() - entry.created_at > datetime.timedelta(seconds=NUKE_WINDOW):
        return  # entrée d'audit ancienne : elle ne correspond pas à cette action
    user = entry.user
    if user.id in (bot.user.id, guild.owner_id) or user.id in cfg["whitelist"]:
        return

    now = time.time()
    key = (guild.id, user.id)
    hits = [t for t in nuke_tracker.get(key, []) if now - t < NUKE_WINDOW] + [now]
    nuke_tracker[key] = hits
    if len(hits) < NUKE_LIMIT:
        return

    nuke_tracker.pop(key, None)
    member = guild.get_member(user.id)
    punished = "aucune (membre introuvable)"
    if member:
        try:
            await member.ban(reason=f"Anti-nuke : {label} en masse")
            punished = "banni"
        except discord.HTTPException:
            punished = "impossible à bannir (rôle trop haut ?)"
    await log_action(guild, "🚨 Anti-nuke",
                     f"{user} ({label}, {len(hits)} actions en {NUKE_WINDOW}s)\nSanction : {punished}",
                     discord.Color.red())


@bot.event
async def on_message(message):
    if message.author.bot or not message.guild:
        return await bot.process_commands(message)
    if prot(message.guild.id)["antilink"] and LINK_RE.search(message.content) \
            and not is_trusted(message.author):
        try:
            await message.delete()
        except discord.HTTPException:
            pass
        await message.channel.send(f"🔗 {message.author.mention}, les liens ne sont pas autorisés ici.",
                                   delete_after=5)
        await log_action(message.guild, "🔗 Anti-link",
                         f"{message.author} a envoyé un lien dans {message.channel.mention}")
        return
    await bot.process_commands(message)


@bot.event
async def on_guild_channel_delete(channel):
    await nuke_check(channel.guild, discord.AuditLogAction.channel_delete, "suppression de salons")


@bot.event
async def on_guild_role_delete(role):
    await nuke_check(role.guild, discord.AuditLogAction.role_delete, "suppression de rôles")


@bot.event
async def on_member_ban(guild, user):
    await nuke_check(guild, discord.AuditLogAction.ban, "bans en masse")


class Protection(commands.Cog):
    """🛡️ Protection"""

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def antilink(self, ctx, etat: str):
        """Active ou désactive l'anti-link (on/off)."""
        cfg = prot(ctx.guild.id)
        cfg["antilink"] = etat.lower() == "on"
        save_json(CONFIG_FILE, config)
        await ctx.send(f"🔗 Anti-link {'activé' if cfg['antilink'] else 'désactivé'}.")

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def antinuke(self, ctx, etat: str):
        """Active ou désactive l'anti-nuke (on/off)."""
        cfg = prot(ctx.guild.id)
        cfg["antinuke"] = etat.lower() == "on"
        save_json(CONFIG_FILE, config)
        await ctx.send(f"🚨 Anti-nuke {'activé' if cfg['antinuke'] else 'désactivé'}.")

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def whitelist(self, ctx, member: discord.Member):
        """Ajoute un membre à la whitelist (exempté de l'anti-link et de l'anti-nuke)."""
        cfg = prot(ctx.guild.id)
        if member.id not in cfg["whitelist"]:
            cfg["whitelist"].append(member.id)
            save_json(CONFIG_FILE, config)
        await ctx.send(f"✅ {member.display_name} est whitelisté.")

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def unwhitelist(self, ctx, member: discord.Member):
        """Retire un membre de la whitelist."""
        cfg = prot(ctx.guild.id)
        if member.id in cfg["whitelist"]:
            cfg["whitelist"].remove(member.id)
            save_json(CONFIG_FILE, config)
        await ctx.send(f"❌ {member.display_name} n'est plus whitelisté.")

    @commands.command()
    async def protection(self, ctx):
        """Affiche l'état des protections du serveur."""
        cfg = prot(ctx.guild.id)
        embed = discord.Embed(title="🛡️ État des protections", color=discord.Color.blurple())
        embed.add_field(name="🔗 Anti-link", value="activé" if cfg["antilink"] else "désactivé")
        embed.add_field(name="🚨 Anti-nuke", value="activé" if cfg["antinuke"] else "désactivé")
        embed.add_field(name="✅ Whitelist", value=f"{len(cfg['whitelist'])} membre(s)")
        await ctx.send(embed=embed)


# ---------------------------------------------------------------- STATISTIQUES

class Statistiques(commands.Cog):
    """📊 Statistiques"""

    @commands.command()
    async def stats(self, ctx):
        """Affiche les statistiques du serveur."""
        g = ctx.guild
        members = g.members
        bots = sum(1 for m in members if m.bot)
        humans = len(members) - bots

        embed = discord.Embed(
            title=f"📊 Statistiques de {g.name}",
            color=discord.Color.blurple(),
            timestamp=discord.utils.utcnow(),
        )
        if g.icon:
            embed.set_thumbnail(url=g.icon.url)
        embed.add_field(name="👥 Membres", value=f"**{g.member_count}** au total", inline=True)
        embed.add_field(name="🧑 Humains", value=str(humans), inline=True)
        embed.add_field(name="🤖 Bots", value=str(bots), inline=True)
        embed.add_field(name="💬 Salons texte", value=str(len(g.text_channels)), inline=True)
        embed.add_field(name="🔊 Salons vocaux", value=str(len(g.voice_channels)), inline=True)
        embed.add_field(name="📁 Catégories", value=str(len(g.categories)), inline=True)
        embed.add_field(name="🎭 Rôles", value=str(len(g.roles) - 1), inline=True)
        embed.add_field(name="💎 Boosts",
                        value=f"{g.premium_subscription_count} (niveau {g.premium_tier})", inline=True)
        embed.add_field(name="📅 Créé le", value=discord.utils.format_dt(g.created_at, "D"), inline=True)
        embed.set_footer(text=f"Demandé par {ctx.author}")
        await ctx.send(embed=embed)

    @commands.command()
    async def rolemembers(self, ctx, role: discord.Role):
        """Affiche le nombre de membres ayant un rôle donné."""
        embed = discord.Embed(title=f"🎭 {role.name}", color=role.color)
        embed.add_field(name="Membres", value=str(len(role.members)), inline=True)
        embed.add_field(name="Mentionnable", value="oui" if role.mentionable else "non", inline=True)
        embed.add_field(name="Créé le", value=discord.utils.format_dt(role.created_at, "D"), inline=True)
        await ctx.send(embed=embed)


    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot or not message.guild:
            return
        guild_stats = msg_stats.setdefault(str(message.guild.id), {})
        cid = str(message.channel.id)
        guild_stats[cid] = guild_stats.get(cid, 0) + 1
        save_json(MSG_FILE, msg_stats)

    @commands.command()
    async def topsalons(self, ctx):
        """Affiche les 5 salons les plus actifs (messages comptés depuis l'installation)."""
        counts = msg_stats.get(str(ctx.guild.id), {})
        if not counts:
            return await ctx.send("📭 Aucun message compté pour l'instant.")
        top = sorted(counts.items(), key=lambda kv: kv[1], reverse=True)[:5]
        medals = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣"]
        lines = []
        for i, (cid, n) in enumerate(top):
            channel = ctx.guild.get_channel(int(cid))
            name = channel.mention if channel else f"(salon supprimé {cid})"
            lines.append(f"{medals[i]} {name} : **{n}** messages")
        embed = discord.Embed(title="💬 Salons les plus actifs", description="\n".join(lines),
                              color=discord.Color.blurple())
        embed.set_footer(text=f"Total compté : {sum(counts.values())} messages")
        await ctx.send(embed=embed)


# ---------------------------------------------------------------- OUTILS

class Outils(commands.Cog):
    """🛠️ Outils"""

    @commands.command()
    @commands.has_permissions(manage_messages=True)
    async def sondage(self, ctx, *, question: str):
        """Lance un sondage oui/non avec réactions."""
        embed = discord.Embed(title="📊 Sondage", description=question, color=discord.Color.blurple())
        embed.set_footer(text=f"Proposé par {ctx.author}")
        msg = await ctx.send(embed=embed)
        await msg.add_reaction("👍")
        await msg.add_reaction("👎")

    @commands.command()
    @commands.has_permissions(manage_messages=True)
    async def annonce(self, ctx, channel: discord.TextChannel, *, texte: str):
        """Publie une annonce en embed dans un salon."""
        embed = discord.Embed(title="📢 Annonce", description=texte, color=discord.Color.gold(),
                              timestamp=discord.utils.utcnow())
        embed.set_footer(text=f"Par {ctx.author}")
        await channel.send(embed=embed)
        await ctx.send(f"✅ Annonce publiée dans {channel.mention}.", delete_after=5)


# ---------------------------------------------------------------- GESTION

import ast
import operator

NOTES_FILE = "notes.json"
notes = load_json(NOTES_FILE, {})
last_deleted = {}  # channel_id -> dernier message supprimé (pour +snipe)

_SAFE_OPS = {
    ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul,
    ast.Div: operator.truediv, ast.Mod: operator.mod, ast.Pow: operator.pow,
    ast.USub: operator.neg, ast.UAdd: operator.pos,
}


def safe_eval(node):
    """Évalue une expression mathématique simple, sans exécuter de code."""
    if isinstance(node, ast.Expression):
        return safe_eval(node.body)
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return node.value
    if isinstance(node, ast.BinOp) and type(node.op) in _SAFE_OPS:
        right = safe_eval(node.right)
        if isinstance(node.op, ast.Pow) and abs(right) > 1000:
            raise ValueError("exposant trop grand")
        return _SAFE_OPS[type(node.op)](safe_eval(node.left), right)
    if isinstance(node, ast.UnaryOp) and type(node.op) in _SAFE_OPS:
        return _SAFE_OPS[type(node.op)](safe_eval(node.operand))
    raise ValueError("expression non supportée")


class Gestion(commands.Cog):
    """🧩 Gestion"""

    # ---- Raccourcis demandés (+del sanction, +server pic, +mute multi)
    @commands.group(name="del", invoke_without_command=True)
    @commands.has_permissions(moderate_members=True)
    async def del_group(self, ctx):
        """Sous-commandes : +del sanction <membre> <nombre>."""
        await ctx.send(f"❌ Utilise `{PREFIX}del sanction <membre> <nombre>`.")

    @del_group.command(name="sanction")
    @commands.has_permissions(moderate_members=True)
    async def del_sanction(self, ctx, member: discord.Member, numero: int):
        """Supprime une sanction pour un membre."""
        await ctx.invoke(bot.get_command("delsanction"), member=member, numero=numero)

    @commands.group(name="server", invoke_without_command=True)
    async def server_group(self, ctx):
        """Sous-commandes : +server pic, +server banner."""
        await ctx.send(f"❌ Utilise `{PREFIX}server pic` ou `{PREFIX}server banner`.")

    @server_group.command(name="pic")
    async def server_pic(self, ctx):
        """Récupère l'icône du serveur."""
        await ctx.invoke(bot.get_command("serverpic"))

    @server_group.command(name="banner")
    async def server_banner(self, ctx):
        """Récupère la bannière du serveur."""
        await ctx.invoke(bot.get_command("serverbanner"))

    @commands.command()
    @commands.has_permissions(moderate_members=True)
    async def mute(self, ctx, members: commands.Greedy[discord.Member], *, raison="Aucune raison"):
        """Mute un ou plusieurs membres pendant 60 min (+tempmute pour choisir la durée)."""
        if not members:
            return await ctx.send("❌ Mentionne au moins un membre.")
        until = discord.utils.utcnow() + datetime.timedelta(minutes=60)
        for member in members:
            await member.timeout(until, reason=raison)
        await ctx.send(f"🔇 {', '.join(m.mention for m in members)} mute(s) pendant 60 min.")
        await log_action(ctx.guild, "Mute", f"{', '.join(str(m) for m in members)} par {ctx.author}\nRaison : {raison}")

    # ---- Sanctions
    @commands.command()
    @commands.has_permissions(moderate_members=True)
    async def sanctions(self, ctx, member: discord.Member):
        """Affiche les sanctions d'un membre."""
        await ctx.invoke(bot.get_command("warnings"), member=member)

    @commands.command()
    @commands.has_permissions(moderate_members=True)
    async def delsanction(self, ctx, member: discord.Member, numero: int):
        """Supprime la sanction n° X d'un membre (voir +sanctions)."""
        items = warns.get(str(ctx.guild.id), {}).get(str(member.id), [])
        if not 1 <= numero <= len(items):
            return await ctx.send("❌ Numéro de sanction invalide.")
        removed = items.pop(numero - 1)
        save_json(WARNS_FILE, warns)
        await ctx.send(f"🗑️ Sanction n°{numero} retirée pour {member.display_name} ({removed['raison']}).")

    @commands.command()
    @commands.has_permissions(moderate_members=True)
    async def clearsanctions(self, ctx, member: discord.Member):
        """Supprime toutes les sanctions d'un membre."""
        await ctx.invoke(bot.get_command("clearwarns"), member=member)

    # ---- Notes de modération
    @commands.group(invoke_without_command=True)
    @commands.has_permissions(moderate_members=True)
    async def note(self, ctx, member: discord.Member, *, texte: str = None):
        """Ajoute une note de modération, ou affiche les notes sans texte."""
        guild_notes = notes.setdefault(str(ctx.guild.id), {}).setdefault(str(member.id), [])
        if texte is None:
            if not guild_notes:
                return await ctx.send(f"{member.display_name} n'a aucune note.")
            lines = [f"**{i}.** {n['date']} par <@{n['par']}> - {n['texte']}"
                     for i, n in enumerate(guild_notes, 1)]
            embed = discord.Embed(title=f"Notes de {member.display_name}",
                                  description="\n".join(lines), color=discord.Color.blurple())
            return await ctx.send(embed=embed)
        guild_notes.append({"texte": texte, "par": ctx.author.id,
                            "date": datetime.datetime.utcnow().isoformat(timespec="minutes")})
        save_json(NOTES_FILE, notes)
        await ctx.send(f"📝 Note ajoutée pour {member.display_name} ({len(guild_notes)} au total).")

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def notedelete(self, ctx, cible: str, numero: str = None):
        """+notedelete all : supprime toutes les notes du serveur. +notedelete @membre <n/all> : supprime des notes."""
        guild_notes = notes.setdefault(str(ctx.guild.id), {})
        if cible.lower() == "all" and numero is None:
            notes[str(ctx.guild.id)] = {}
            save_json(NOTES_FILE, notes)
            return await ctx.send("🗑️ Toutes les notes du serveur ont été supprimées.")
        member = await commands.MemberConverter().convert(ctx, cible)
        if numero is None:
            return await ctx.send(f"❌ Précise un numéro ou `all`. Ex : `{PREFIX}notedelete {member.mention} all`")
        if numero.lower() == "all":
            guild_notes.pop(str(member.id), None)
            msg = f"🗑️ Toutes les notes de {member.display_name} ont été supprimées."
        else:
            items = guild_notes.get(str(member.id), [])
            if not numero.isdigit() or not 1 <= int(numero) <= len(items):
                return await ctx.send("❌ Numéro de note invalide.")
            items.pop(int(numero) - 1)
            msg = f"🗑️ Note n°{numero} supprimée pour {member.display_name}."
        save_json(NOTES_FILE, notes)
        await ctx.send(msg)

    @note.command(name="delete")
    @commands.has_permissions(administrator=True)
    async def note_delete(self, ctx, cible: str, numero: str = None):
        """+note delete all : toutes les notes du serveur. +note delete @membre <n/all> : notes d'un membre."""
        await ctx.invoke(bot.get_command("notedelete"), cible=cible, numero=numero)

    # ---- Messages
    @commands.command()
    @commands.has_permissions(manage_messages=True)
    async def clearuser(self, ctx, member: discord.Member, amount: int = 50):
        """Supprime les messages d'un membre dans le salon (30 derniers par défaut, 50 max)."""
        deleted = await ctx.channel.purge(limit=min(amount, 200), check=lambda m: m.author == member)
        await ctx.send(f"🧹 {len(deleted)} message(s) de {member.display_name} supprimé(s).", delete_after=3)

    @commands.Cog.listener()
    async def on_message_delete(self, message):
        if message.guild and not message.author.bot:
            last_deleted[message.channel.id] = message

    @commands.command()
    @commands.has_permissions(manage_messages=True)
    async def snipe(self, ctx):
        """Affiche le dernier message supprimé du salon."""
        msg = last_deleted.get(ctx.channel.id)
        if not msg:
            return await ctx.send("❌ Aucun message supprimé récemment dans ce salon.")
        embed = discord.Embed(description=msg.content or "*(pas de texte)*", color=discord.Color.red(),
                              timestamp=msg.created_at)
        embed.set_author(name=str(msg.author), icon_url=msg.author.display_avatar.url)
        await ctx.send(embed=embed)

    # ---- Rôles
    @commands.command()
    @commands.has_permissions(manage_roles=True)
    async def addrole(self, ctx, member: discord.Member, *roles: discord.Role):
        """Ajoute un ou plusieurs rôles à un membre."""
        ok = [r for r in roles if r < ctx.guild.me.top_role and not r.managed]
        if not ok:
            return await ctx.send("❌ Aucun rôle ajoutable (hiérarchie ou rôle géré).")
        await member.add_roles(*ok, reason=f"addrole par {ctx.author}")
        await ctx.send(f"✅ Rôle(s) ajouté(s) à {member.display_name} : {', '.join(r.name for r in ok)}")

    @commands.command()
    @commands.has_permissions(manage_roles=True)
    async def delrole(self, ctx, member: discord.Member, *roles: discord.Role):
        """Retire un ou plusieurs rôles à un membre."""
        ok = [r for r in roles if r < ctx.guild.me.top_role and not r.managed and r in member.roles]
        if not ok:
            return await ctx.send("❌ Aucun rôle retirable (hiérarchie, rôle géré ou absent).")
        await member.remove_roles(*ok, reason=f"delrole par {ctx.author}")
        await ctx.send(f"✅ Rôle(s) retiré(s) à {member.display_name} : {', '.join(r.name for r in ok)}")

    @commands.command()
    @commands.has_permissions(manage_roles=True)
    async def derank(self, ctx, member: discord.Member):
        """Retire tous les rôles retirables d'un membre."""
        ok = [r for r in member.roles if not r.is_default() and not r.managed and r < ctx.guild.me.top_role]
        if not ok:
            return await ctx.send("❌ Ce membre n'a aucun rôle retirable.")
        await member.remove_roles(*ok, reason=f"derank par {ctx.author}")
        await ctx.send(f"✅ {len(ok)} rôle(s) retiré(s) à {member.display_name}.")

    # ---- Pseudos
    @commands.command()
    @commands.has_permissions(manage_nicknames=True)
    async def nick(self, ctx, member: discord.Member, *, nom: str):
        """Change le pseudo d'un membre sur le serveur."""
        await member.edit(nick=nom, reason=f"nick par {ctx.author}")
        await ctx.send(f"✏️ Pseudo de {member.mention} changé en **{nom}**.")

    @commands.command()
    @commands.has_permissions(manage_nicknames=True)
    async def lockname(self, ctx, member: discord.Member, *, nom: str):
        """Verrouille le pseudo d'un membre : il ne pourra plus le changer."""
        config.setdefault("locked_names", {})[str(member.id)] = nom
        save_json(CONFIG_FILE, config)
        await member.edit(nick=nom, reason=f"lockname par {ctx.author}")
        await ctx.send(f"🔒 Pseudo de {member.mention} verrouillé sur **{nom}**.")

    @commands.command()
    @commands.has_permissions(manage_nicknames=True)
    async def unlockname(self, ctx, member: discord.Member):
        """Déverrouille le pseudo d'un membre."""
        config.get("locked_names", {}).pop(str(member.id), None)
        save_json(CONFIG_FILE, config)
        await ctx.send(f"🔓 Pseudo de {member.mention} déverrouillé.")

    @commands.command()
    @commands.has_permissions(manage_nicknames=True)
    async def locknamelist(self, ctx):
        """Affiche les membres dont le pseudo est verrouillé."""
        locked = config.get("locked_names", {})
        if not locked:
            return await ctx.send("Aucun pseudo verrouillé.")
        lines = [f"<@{uid}> → **{nom}**" for uid, nom in locked.items()]
        await ctx.send(embed=discord.Embed(title="🔒 Pseudos verrouillés",
                                           description="\n".join(lines), color=discord.Color.blurple()))

    @commands.Cog.listener()
    async def on_member_update(self, before, after):
        if before.nick == after.nick:
            return
        locked = config.get("locked_names", {}).get(str(after.id))
        if locked and after.nick != locked:
            try:
                await after.edit(nick=locked, reason="Pseudo verrouillé")
            except discord.Forbidden:
                pass

    # ---- Suggestions
    @commands.command()
    @commands.has_permissions(administrator=True)
    async def setsuggestion(self, ctx, channel: discord.TextChannel):
        """Définit le salon des suggestions."""
        config["suggestion_channel"] = channel.id
        save_json(CONFIG_FILE, config)
        await ctx.send(f"✅ Salon des suggestions : {channel.mention}")

    @commands.command()
    async def suggestion(self, ctx, *, texte: str):
        """Poste une suggestion dans le salon des suggestions."""
        channel = ctx.guild.get_channel(config.get("suggestion_channel", 0))
        if not channel:
            return await ctx.send("❌ Aucun salon de suggestions défini (`+setsuggestion #salon`).")
        embed = discord.Embed(title="💡 Suggestion", description=texte, color=discord.Color.gold(),
                              timestamp=discord.utils.utcnow())
        embed.set_footer(text=f"Par {ctx.author}")
        msg = await channel.send(embed=embed)
        await msg.add_reaction("👍")
        await msg.add_reaction("👎")
        await ctx.send("✅ Suggestion envoyée.", delete_after=5)

    # ---- Utilitaires
    @commands.command()
    async def calc(self, ctx, *, expression: str):
        """Calcule une expression, ex : +calc (3+4)*2^3"""
        try:
            result = safe_eval(ast.parse(expression.replace("^", "**"), mode="eval"))
        except Exception:
            return await ctx.send("❌ Calcul invalide. Opérations acceptées : + - * / % ^ et parenthèses.")
        await ctx.send(embed=discord.Embed(title="🧮 Calcul", description=f"`{expression}` = **{result}**",
                                           color=discord.Color.blurple()))

    @commands.command()
    async def serverpic(self, ctx):
        """Affiche l'icône du serveur en grand."""
        if not ctx.guild.icon:
            return await ctx.send("❌ Ce serveur n'a pas d'icône.")
        embed = discord.Embed(title=f"Icône de {ctx.guild.name}", color=discord.Color.blurple())
        embed.set_image(url=ctx.guild.icon.url)
        await ctx.send(embed=embed)

    @commands.command()
    async def serverbanner(self, ctx):
        """Affiche la bannière du serveur."""
        if not ctx.guild.banner:
            return await ctx.send("❌ Ce serveur n'a pas de bannière.")
        embed = discord.Embed(title=f"Bannière de {ctx.guild.name}", color=discord.Color.blurple())
        embed.set_image(url=ctx.guild.banner.url)
        await ctx.send(embed=embed)


# ---------------------------------------------------------------- MODÉRATION AVANCÉE

DUREE_UNITES = {"s": 1, "m": 60, "h": 3600, "d": 86400, "w": 604800}


def parse_duree(texte):
    m = re.fullmatch(r"(\d+)([smhdw])", texte.lower())
    if not m:
        return None
    return datetime.timedelta(seconds=int(m.group(1)) * DUREE_UNITES[m.group(2)])


class ModerationAvancee(commands.Cog, name="Modération avancée"):
    """🔨 Modération avancée"""

    @commands.command()
    @commands.has_permissions(moderate_members=True)
    async def tempmute(self, ctx, member: discord.Member, duree: str, *, raison="Aucune raison"):
        """Mute un membre pendant une durée, ex : 10m, 2h, 1d (28 jours max)."""
        delta = parse_duree(duree)
        if delta is None or delta > datetime.timedelta(days=28):
            return await ctx.send("❌ Durée invalide. Exemples : `10m`, `2h`, `1d` (28 jours max).")
        await member.timeout(discord.utils.utcnow() + delta, reason=raison)
        await ctx.send(f"🔇 {member.mention} est mute pendant {duree}.")
        await log_action(ctx.guild, "Tempmute", f"{member} ({duree}) par {ctx.author}\nRaison : {raison}")

    @commands.command()
    @commands.has_permissions(ban_members=True)
    async def banlist(self, ctx):
        """Affiche les bannissements en cours sur le serveur."""
        bans = [entry async for entry in ctx.guild.bans(limit=50)]
        if not bans:
            return await ctx.send("✅ Aucun bannissement en cours.")
        lignes = [f"• **{b.user}** (`{b.user.id}`) - {b.reason or 'Aucune raison'}" for b in bans]
        embed = discord.Embed(title=f"🔨 Bannissements ({len(bans)})", description="\n".join(lignes)[:4000],
                              color=discord.Color.red())
        await ctx.send(embed=embed)

    @commands.command()
    async def perms(self, ctx):
        """Affiche les rôles ayant des permissions sensibles sur le serveur."""
        sensibles = {
            "administrator": "Administrateur", "manage_guild": "Gérer le serveur",
            "ban_members": "Bannir", "kick_members": "Expulser", "manage_roles": "Gérer les rôles",
            "manage_channels": "Gérer les salons", "moderate_members": "Modérer",
        }
        lignes = []
        for role in reversed(ctx.guild.roles):
            if role.is_default():
                continue
            droits = [nom for attr, nom in sensibles.items() if getattr(role.permissions, attr)]
            if droits:
                lignes.append(f"**{role.name}** : {', '.join(droits)}")
        embed = discord.Embed(title="🔑 Permissions sensibles", description="\n".join(lignes)[:4000] or "Aucun rôle sensible.",
                              color=discord.Color.orange())
        await ctx.send(embed=embed)


# ---------------------------------------------------------------- RECHERCHE

def http_json(url):
    req = urllib.request.Request(url, headers={"User-Agent": "gestion-bot/1.0"})
    with urllib.request.urlopen(req, timeout=10) as reponse:
        return json.loads(reponse.read().decode("utf-8"))


class Recherche(commands.Cog, name="Recherche & infos"):
    """🌐 Recherche & infos"""

    @commands.command()
    async def wiki(self, ctx, *, mot: str):
        """Affiche le résumé d'un article Wikipédia (fr)."""
        url = "https://fr.wikipedia.org/api/rest_v1/page/summary/" + urllib.parse.quote(mot.replace(" ", "_"))
        try:
            data = await asyncio.to_thread(http_json, url)
        except Exception:
            return await ctx.send("❌ Aucun article trouvé.")
        page = data.get("content_urls", {}).get("desktop", {}).get("page")
        embed = discord.Embed(title=data.get("title", mot), url=page,
                              description=(data.get("extract") or "Pas de résumé.")[:1000],
                              color=discord.Color.blurple())
        if data.get("thumbnail"):
            embed.set_thumbnail(url=data["thumbnail"]["source"])
        await ctx.send(embed=embed)

    @commands.command()
    async def searchwiki(self, ctx, *, mot: str):
        """Liste les articles Wikipédia liés à un mot-clé."""
        url = ("https://fr.wikipedia.org/w/api.php?action=opensearch&limit=5&format=json&search="
               + urllib.parse.quote(mot))
        try:
            _, titres, _, liens = await asyncio.to_thread(http_json, url)
        except Exception:
            return await ctx.send("❌ Recherche impossible pour le moment.")
        if not titres:
            return await ctx.send("❌ Aucun article trouvé.")
        lignes = [f"• [{t}]({l})" for t, l in zip(titres, liens)]
        await ctx.send(embed=discord.Embed(title=f"📚 Wikipédia : {mot}", description="\n".join(lignes),
                                           color=discord.Color.blurple()))

    @commands.command()
    async def image(self, ctx, *, mot: str):
        """Donne le lien de recherche d'images Google pour un mot-clé."""
        url = "https://www.google.com/search?tbm=isch&q=" + urllib.parse.quote(mot)
        await ctx.send(embed=discord.Embed(title=f"🖼️ Images : {mot}", description=f"[Ouvrir la recherche]({url})",
                                           url=url, color=discord.Color.blurple()))

    @commands.command()
    async def emoji(self, ctx, emoji_texte: str):
        """Récupère l'image d'un emoji personnalisé."""
        m = re.fullmatch(r"<(a?):\w+:(\d+)>", emoji_texte.strip())
        if not m:
            return await ctx.send("❌ Donne un emoji personnalisé (pas un emoji Unicode).")
        extension = "gif" if m.group(1) else "png"
        url = f"https://cdn.discordapp.com/emojis/{m.group(2)}.{extension}"
        embed = discord.Embed(title="😀 Emoji", url=url, color=discord.Color.blurple())
        embed.set_image(url=url)
        await ctx.send(embed=embed)

    @commands.command()
    async def banner(self, ctx, member: discord.Member = None):
        """Affiche la bannière d'un membre."""
        member = member or ctx.author
        user = await bot.fetch_user(member.id)
        if not user.banner:
            return await ctx.send("❌ Ce membre n'a pas de bannière.")
        embed = discord.Embed(title=f"Bannière de {member.display_name}", color=member.color)
        embed.set_image(url=user.banner.url)
        await ctx.send(embed=embed)


# ---------------------------------------------------------------- SUGGESTIONS

class Suggestions(commands.Cog):
    """💡 Suggestions"""

    @commands.group(name="lb", invoke_without_command=True)
    async def lb(self, ctx):
        """Classements. Ex : +lb suggestions"""
        await ctx.send(f"❌ Utilise `{PREFIX}lb suggestions`.")

    @lb.command(name="suggestions")
    async def lb_suggestions(self, ctx):
        """Affiche les suggestions les mieux notées du salon des suggestions."""
        salon = ctx.guild.get_channel(config.get("suggestion_channel", 0))
        if not salon:
            return await ctx.send(f"❌ Aucun salon de suggestions défini (`{PREFIX}setsuggestion #salon`).")
        scores = []
        async for msg in salon.history(limit=200):
            if not msg.embeds or msg.embeds[0].title != "💡 Suggestion":
                continue
            # r.count - 1 : on retire la réaction du bot
            pouces = {str(r.emoji): r.count - 1 for r in msg.reactions}
            scores.append((pouces.get("👍", 0) - pouces.get("👎", 0), msg))
        if not scores:
            return await ctx.send("Aucune suggestion trouvée.")
        scores.sort(key=lambda x: x[0], reverse=True)
        lignes = [f"**{s:+d}** · {(msg.embeds[0].description or '')[:120]} · [lien]({msg.jump_url})"
                  for s, msg in scores[:5]]
        await ctx.send(embed=discord.Embed(title="🏆 Meilleures suggestions", description="\n".join(lignes),
                                           color=discord.Color.gold()))


# ---------------------------------------------------------------- ANTIRAID

DANGER_PERMS = ("administrator", "manage_guild", "manage_roles", "manage_channels",
                "ban_members", "kick_members", "manage_webhooks")
PHISH_RE = re.compile(
    r"(free\s*nitro|nitro\s*gratuit|discord\S*\.(gift|ru|xyz|click|top)|steam\S*\.(ru|gift|cc))",
    re.IGNORECASE,
)


def blrank_state():
    return config.setdefault("blrank", {"enabled": False, "scope": "danger", "members": []})


def antihack_state():
    return config.setdefault("antihack", {"antiphish": False, "trap_channel": 0, "doublons": False})


def is_dangerous(role):
    return any(getattr(role.permissions, p) for p in DANGER_PERMS)


class Antiraid(commands.Cog, name="Antiraid & antihack"):
    """🛡️ Antiraid & antihack"""

    # ---- Blacklist rank
    @commands.group(name="blrank", invoke_without_command=True)
    @commands.has_permissions(manage_roles=True)
    async def blrank(self, ctx):
        """Affiche l'état de la blacklist rank."""
        st = blrank_state()
        scope = "rôles dangereux" if st["scope"] == "danger" else "tous les rôles"
        lines = [
            f"Statut : {'activée' if st['enabled'] else 'désactivée'}",
            f"Portée : {scope}",
            f"Membres blacklistés : {len(st['members'])}",
        ]
        await ctx.send(embed=discord.Embed(title="🚫 Blacklist rank", description="\n".join(lines),
                                           color=discord.Color.blurple()))

    @blrank.command(name="on", aliases=["max"])
    async def blrank_on(self, ctx):
        """Active la blacklist rank."""
        blrank_state()["enabled"] = True
        save_json(CONFIG_FILE, config)
        await ctx.send("🚫 Blacklist rank activée.")

    @blrank.command(name="off")
    async def blrank_off(self, ctx):
        """Désactive la blacklist rank."""
        blrank_state()["enabled"] = False
        save_json(CONFIG_FILE, config)
        await ctx.send("🚫 Blacklist rank désactivée.")

    @blrank.command(name="danger")
    async def blrank_danger(self, ctx):
        """Ne bloque que les rôles dangereux (admin, ban, gestion des rôles…)."""
        blrank_state()["scope"] = "danger"
        save_json(CONFIG_FILE, config)
        await ctx.send("🚫 Portée : rôles dangereux.")

    @blrank.command(name="all")
    async def blrank_all(self, ctx):
        """Bloque tous les rôles pour les membres blacklistés."""
        blrank_state()["scope"] = "all"
        save_json(CONFIG_FILE, config)
        await ctx.send("🚫 Portée : tous les rôles.")

    @blrank.command(name="add")
    async def blrank_add(self, ctx, member: discord.Member):
        """Ajoute un membre à la blacklist rank."""
        st = blrank_state()
        if member.id in st["members"]:
            return await ctx.send(f"{member.display_name} est déjà blacklisté.")
        st["members"].append(member.id)
        save_json(CONFIG_FILE, config)
        await ctx.send(f"🚫 {member.mention} ajouté à la blacklist rank.")

    @blrank.command(name="del")
    async def blrank_del(self, ctx, member: discord.Member):
        """Retire un membre de la blacklist rank."""
        st = blrank_state()
        if member.id not in st["members"]:
            return await ctx.send(f"{member.display_name} n'est pas blacklisté.")
        st["members"].remove(member.id)
        save_json(CONFIG_FILE, config)
        await ctx.send(f"✅ {member.mention} retiré de la blacklist rank.")

    @commands.command()
    @commands.has_permissions(manage_roles=True)
    async def unbl(self, ctx, user_id: int):
        """Retire un membre de la blacklist rank par son ID (même s'il a quitté le serveur)."""
        st = blrank_state()
        if user_id not in st["members"]:
            return await ctx.send("❌ Cet ID n'est pas dans la blacklist rank.")
        st["members"].remove(user_id)
        save_json(CONFIG_FILE, config)
        await ctx.send(f"✅ <@{user_id}> retiré de la blacklist rank.")

    # ---- Panneau antihack
    @commands.group(name="antihack", invoke_without_command=True)
    @commands.has_permissions(administrator=True)
    async def antihack(self, ctx):
        """Panneau antihack : antiphish, salon piège, doublons."""
        st = antihack_state()
        trap = ctx.guild.get_channel(st["trap_channel"]) if st["trap_channel"] else None
        embed = discord.Embed(title="🔐 Antihack",
                              description="Protection contre les comptes piratés.",
                              color=discord.Color.red())
        embed.add_field(name="🎣 Antiphish", value="activé" if st["antiphish"] else "désactivé")
        embed.add_field(name="🪤 Salon piège", value=trap.mention if trap else "non défini")
        embed.add_field(name="👥 Doublons", value="activé" if st["doublons"] else "désactivé")
        embed.set_footer(text=f"{PREFIX}antihack antiphish on/off · {PREFIX}antihack piege #salon · "
                              f"{PREFIX}antihack doublons on/off")
        await ctx.send(embed=embed)

    @antihack.command(name="antiphish")
    async def antihack_antiphish(self, ctx, etat: str):
        """Supprime les liens de phishing connus et met leur auteur en timeout 1 h (on/off)."""
        antihack_state()["antiphish"] = etat.lower() == "on"
        save_json(CONFIG_FILE, config)
        await ctx.send(f"🎣 Antiphish {'activé' if antihack_state()['antiphish'] else 'désactivé'}.")

    @antihack.command(name="piege")
    async def antihack_piege(self, ctx, channel: discord.TextChannel = None):
        """Définit le salon piège : tout message posté dedans entraîne un ban. Sans salon : désactive."""
        antihack_state()["trap_channel"] = channel.id if channel else 0
        save_json(CONFIG_FILE, config)
        await ctx.send(f"🪤 Salon piège : {channel.mention}" if channel else "🪤 Salon piège désactivé.")

    @antihack.command(name="doublons")
    async def antihack_doublons(self, ctx, etat: str):
        """Signale les arrivées suspectes : compte récent ou pseudo identique à un membre (on/off)."""
        antihack_state()["doublons"] = etat.lower() == "on"
        save_json(CONFIG_FILE, config)
        await ctx.send(f"👥 Détection des doublons {'activée' if antihack_state()['doublons'] else 'désactivée'}.")

    # ---- Listeners
    @commands.Cog.listener()
    async def on_member_update(self, before, after):
        st = blrank_state()
        if not st["enabled"] or after.id not in st["members"]:
            return
        added = [r for r in after.roles if r not in before.roles and not r.is_default() and not r.managed]
        if st["scope"] == "danger":
            added = [r for r in added if is_dangerous(r)]
        if not added:
            return
        try:
            await after.remove_roles(*added, reason="Blacklist rank")
        except discord.Forbidden:
            return
        await log_action(after.guild, "Blacklist rank",
                         f"{after} a reçu {', '.join(r.name for r in added)} : rôle(s) retiré(s).",
                         discord.Color.red())

    @commands.Cog.listener()
    async def on_message(self, message):
        if not message.guild or message.author.bot:
            return
        st = antihack_state()
        if st["trap_channel"] and message.channel.id == st["trap_channel"]:
            try:
                await message.delete()
                await message.guild.ban(message.author, reason="Salon piège (antihack)", delete_message_days=1)
            except discord.HTTPException:
                return
            await log_action(message.guild, "Salon piège", f"{message.author} banni (message dans le salon piège).",
                             discord.Color.red())
            return
        if st["antiphish"] and PHISH_RE.search(message.content):
            try:
                await message.delete()
            except discord.HTTPException:
                return
            try:
                await message.author.timeout(discord.utils.utcnow() + datetime.timedelta(hours=1),
                                             reason="Antiphish")
            except discord.HTTPException:
                pass
            await message.channel.send(f"🎣 Lien suspect supprimé ({message.author.mention} en timeout 1 h).",
                                       delete_after=8)
            await log_action(message.guild, "Antiphish", f"Lien suspect de {message.author} supprimé.",
                             discord.Color.red())

    @commands.Cog.listener()
    async def on_member_join(self, member):
        if not antihack_state()["doublons"]:
            return
        alerts = []
        age = discord.utils.utcnow() - member.created_at
        if age < datetime.timedelta(days=7):
            alerts.append(f"compte récent ({age.days} j)")
        same = [m for m in member.guild.members
                if m.id != member.id and m.name.lower() == member.name.lower()]
        if same:
            alerts.append(f"même pseudo que {', '.join(str(m) for m in same[:5])}")
        if alerts:
            await log_action(member.guild, "Doublon suspect", f"{member.mention} : " + " · ".join(alerts),
                             discord.Color.red())


# ---------------------------------------------------------------- AIDE

INTRO = ("*Les paramètres peuvent être des noms, des mentions ou des IDs.\n"
         "Si ce ne sont pas des mentions, ils doivent être séparés par `, `.*")


def help_footer():
    name = bot.user.name if bot.user else "Gestion Bot"
    return f"{name} • Préfixe actuel : {PREFIX}"


def command_block(c):
    sig = f" {c.signature}" if c.signature else ""
    return f"**`{PREFIX}{c.name}{sig}`**\n{c.short_doc or 'Pas de description'}"


async def send_category(ctx, title, cmds, color=discord.Color.blurple()):
    """Envoie la liste des commandes au format embed, découpée si elle est trop longue."""
    chunks, current = [], ""
    for c in cmds:
        block = command_block(c) + "\n\n"
        if len(current) + len(block) > 3500:
            chunks.append(current)
            current = ""
        current += block
    if current:
        chunks.append(current)
    for i, body in enumerate(chunks):
        intro = INTRO + "\n\n" if i == 0 else ""
        embed = discord.Embed(title=title if i == 0 else f"{title} (suite)",
                              description=(intro + body).rstrip(), color=color)
        embed.set_footer(text=help_footer())
        await ctx.send(embed=embed)


@bot.command(name="help")
async def help_cmd(ctx, *, sujet: str = None):
    """Affiche la liste des commandes. +help <catégorie> ou +help <commande>."""
    if sujet is None:
        embed = discord.Embed(
            title="📖 Aide",
            description=INTRO + f"\n\nTape `{PREFIX}help <catégorie>` pour le détail d'une catégorie.",
            color=discord.Color.blurple(),
        )
        for name, cog in bot.cogs.items():
            cmds = [c for c in cog.get_commands() if not c.hidden]
            if cmds:
                value = " · ".join(f"`{PREFIX}{c.name}`" for c in cmds)
                embed.add_field(
                    name=f"{CATEGORY_EMOJIS.get(name, '📁')} {name} ({len(cmds)})",
                    value=value[:1000],
                    inline=False,
                )
        embed.set_footer(text=help_footer())
        return await ctx.send(embed=embed)

    for name, cog in bot.cogs.items():
        if name.lower() == sujet.lower() or name.lower().endswith(sujet.lower()):
            cmds = [c for c in cog.get_commands() if not c.hidden]
            return await send_category(ctx, f"{CATEGORY_EMOJIS.get(name, '📁')} {name}", cmds)

    cmd = bot.get_command(sujet)
    if cmd:
        sig = f" {cmd.signature}" if cmd.signature else ""
        embed = discord.Embed(
            title=f"{CATEGORY_EMOJIS.get(cmd.cog_name, '📁')} {cmd.cog_name or 'Commande'}",
            description=f"**`{PREFIX}{cmd.name}{sig}`**\n{cmd.short_doc or 'Pas de description'}",
            color=discord.Color.blurple(),
        )
        if cmd.aliases:
            embed.add_field(name="Alias", value=" · ".join(f"`{PREFIX}{a}`" for a in cmd.aliases))
        embed.set_footer(text=help_footer())
        return await ctx.send(embed=embed)

    await ctx.send(f"❌ Aucune catégorie ni commande « {sujet} ». Tape `{PREFIX}help`.")


# ---------------------------------------------------------------- EVENTS

@bot.event
async def on_ready():
    print(f"Connecté en tant que {bot.user} ({len(bot.guilds)} serveur(s))")


@bot.event
async def on_member_join(member):
    channel_id = config.get("welcome_channel")
    channel = member.guild.get_channel(channel_id) if channel_id else None
    if channel:
        await channel.send(f"👋 Bienvenue {member.mention} sur **{member.guild.name}** !")


@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        return
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("❌ Tu n'as pas la permission d'utiliser cette commande.")
    elif isinstance(error, (commands.MissingRequiredArgument, commands.BadArgument)):
        await ctx.send(f"❌ Arguments invalides. Tape `{PREFIX}help {ctx.command}`.")
    else:
        print(f"Erreur dans {ctx.command}: {error}")
        await ctx.send("❌ Une erreur est survenue.")


# ---------------------------------------------------------------- SITE WEB (Render)

import html as html_lib
import http.server
import threading

START_TIME = time.time()


def build_status_page():
    ready = bot.is_ready()
    guilds = bot.guilds if ready else []
    members = sum(g.member_count or 0 for g in guilds)
    latency = f"{round(bot.latency * 1000)} ms" if ready else "-"
    uptime = str(datetime.timedelta(seconds=int(time.time() - START_TIME)))
    commands_count = len({c.qualified_name for c in bot.walk_commands()})
    name = html_lib.escape(str(bot.user)) if bot.user else "Gestion Bot"
    status, color = ("En ligne", "#3ba55d") if ready else ("Démarrage...", "#faa61a")
    cards = [
        ("Statut", status),
        ("Serveurs", len(guilds)),
        ("Membres", members),
        ("Latence", latency),
        ("Uptime", uptime),
        ("Commandes", commands_count),
    ]
    cards_html = "".join(
        f'<div class="card"><span>{html_lib.escape(str(k))}</span><strong>{html_lib.escape(str(v))}</strong></div>'
        for k, v in cards
    )
    return f"""<!doctype html>
<html lang="fr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{name}</title>
<style>
  body {{ margin:0; font-family: system-ui, sans-serif; background:#1e1f22; color:#f2f3f5;
         display:flex; min-height:100vh; align-items:center; justify-content:center; }}
  main {{ width:min(720px, 92vw); text-align:center; }}
  h1 {{ margin:0 0 .3rem; }}
  .badge {{ display:inline-block; padding:.3rem .8rem; border-radius:999px; background:{color};
           color:#111; font-weight:600; margin-bottom:1.5rem; }}
  .grid {{ display:grid; grid-template-columns:repeat(auto-fit, minmax(150px,1fr)); gap:12px; }}
  .card {{ background:#2b2d31; border-radius:12px; padding:1rem; display:flex; flex-direction:column; gap:.4rem; }}
  .card span {{ color:#b5bac1; font-size:.85rem; }}
  .card strong {{ font-size:1.3rem; }}
  footer {{ margin-top:1.5rem; color:#949ba4; font-size:.85rem; }}
</style>
</head>
<body>
<main>
  <h1>{name}</h1>
  <div class="badge">{status}</div>
  <div class="grid">{cards_html}</div>
  <footer>Préfixe : {PREFIX} · Aide : {PREFIX}help</footer>
</main>
</body>
</html>"""


class StatusHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path.startswith("/health"):
            body, ctype = b"ok", "text/plain; charset=utf-8"
        else:
            body, ctype = build_status_page().encode("utf-8"), "text/html; charset=utf-8"
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args):
        pass  # silence les logs HTTP


def start_web_server():
    port = int(os.getenv("PORT", "10000"))  # Render fournit PORT automatiquement
    server = http.server.ThreadingHTTPServer(("0.0.0.0", port), StatusHandler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    print(f"Site de statut en ligne sur le port {port}")


# ---------------------------------------------------------------- LANCEMENT

async def main():
    async with bot:
        for cog in (Configuration(), Salons(), Moderation(), Utility(), Protection(), Statistiques(), Outils(), Gestion(), ModerationAvancee(), Recherche(), Suggestions(), Antiraid()):
            await bot.add_cog(cog)
        start_web_server()
        await bot.start(TOKEN)


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
