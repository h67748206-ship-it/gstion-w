# Bot de gestion de serveur (modération, logs, bienvenue, tickets) + mini site web
# Fichier unique. Lancer : python gestion_bot.py
import asyncio
import datetime as dt
import os
import re
import sqlite3
import subprocess
import sys

try:
    import discord
except ImportError:  # installe discord.py tout seul
    subprocess.check_call([sys.executable, "-m", "pip", "install", "-U", "discord.py"])
    import discord

from aiohttp import web
from discord import app_commands
from discord.ext import commands

# ===================== CONFIG =====================
_brut = os.getenv("DISCORD_TOKEN")
TOKEN = (_brut or "COLLE_TON_TOKEN_ICI").strip().strip('"').strip("'").strip()
DB_PATH = os.getenv("DB_PATH", "gestion.db")
COULEUR = 0x5865F2
MAX_WARNS = 3          # nombre de warns avant sanction auto
SANCTION_MIN = 60      # durée du timeout auto (minutes)
# ==================================================

# ===================== BASE DE DONNÉES =====================
COLS = {"log_channel", "welcome_channel", "welcome_msg", "autorole", "staff_role", "antilink"}


def run(sql, args=(), one=False, many=False):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        cur = conn.execute(sql, args)
        conn.commit()
        if one:
            r = cur.fetchone()
            return dict(r) if r else None
        if many:
            return [dict(r) for r in cur.fetchall()]
    finally:
        conn.close()


def init_db():
    run(
        "CREATE TABLE IF NOT EXISTS config ("
        "guild_id INTEGER PRIMARY KEY, log_channel INTEGER, welcome_channel INTEGER, "
        "welcome_msg TEXT, autorole INTEGER, staff_role INTEGER, antilink INTEGER DEFAULT 0)"
    )
    run(
        "CREATE TABLE IF NOT EXISTS warns ("
        "id INTEGER PRIMARY KEY AUTOINCREMENT, guild_id INTEGER, user_id INTEGER, "
        "mod_id INTEGER, reason TEXT, ts TEXT)"
    )


def get_conf(gid: int) -> dict:
    run("INSERT OR IGNORE INTO config(guild_id) VALUES(?)", (gid,))
    return run("SELECT * FROM config WHERE guild_id=?", (gid,), one=True)


def set_conf(gid: int, **kw):
    get_conf(gid)
    for k, v in kw.items():
        if k in COLS:
            run(f"UPDATE config SET {k}=? WHERE guild_id=?", (v, gid))


# ===================== OUTILS =====================
def emb(titre: str, desc: str = "", couleur: int = COULEUR) -> discord.Embed:
    return discord.Embed(title=titre, description=desc, color=couleur, timestamp=discord.utils.utcnow())


async def log(guild: discord.Guild, embed: discord.Embed):
    ch_id = get_conf(guild.id)["log_channel"]
    ch = guild.get_channel(ch_id) if ch_id else None
    if ch:
        try:
            await ch.send(embed=embed)
        except discord.HTTPException:
            pass


def peut_agir(inter: discord.Interaction, cible: discord.Member) -> bool:
    if cible.id == inter.user.id or cible.id == inter.guild.owner_id:
        return False
    if inter.user.id == inter.guild.owner_id:
        return True
    return cible.top_role < inter.user.top_role


async def refus(inter: discord.Interaction, texte: str):
    if inter.response.is_done():
        await inter.followup.send(texte, ephemeral=True)
    else:
        await inter.response.send_message(texte, ephemeral=True)


def perm(**p):
    """Empile : serveur uniquement + permission requise (cachée aux autres)."""
    def deco(f):
        f = app_commands.checks.has_permissions(**p)(f)
        f = app_commands.default_permissions(**p)(f)
        f = app_commands.guild_only()(f)
        return f
    return deco


# ===================== MINI SITE WEB =====================
PAGE = """<!doctype html>
<html lang="fr"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{nom}</title>
<style>
body{{margin:0;min-height:100vh;display:flex;align-items:center;justify-content:center;
background:#1e1f22;color:#dbdee1;font-family:system-ui,sans-serif}}
.card{{background:#2b2d31;border-radius:14px;padding:28px;max-width:380px;width:90%;text-align:center}}
h1{{margin:0 0 6px;font-size:22px;color:#fff}}
p{{margin:0 0 18px;color:#b5bac1;font-size:14px}}
.row{{display:flex;gap:10px;margin-bottom:18px}}
.stat{{flex:1;background:#1e1f22;border-radius:10px;padding:12px}}
.stat b{{display:block;font-size:20px;color:#fff}}
.stat span{{font-size:12px;color:#949ba4}}
.ok{{display:inline-block;padding:4px 12px;border-radius:99px;background:#23a55a33;color:#3ba55d;font-size:13px}}
</style></head><body><div class="card">
<h1>{nom}</h1>
<p>Gestion de serveur : modération, logs, bienvenue et tickets.</p>
<div class="row">
<div class="stat"><b>{serveurs}</b><span>serveurs</span></div>
<div class="stat"><b>{membres}</b><span>membres</span></div>
<div class="stat"><b>{ping} ms</b><span>ping</span></div>
</div><span class="ok">● En ligne</span></div></body></html>"""


async def page_accueil(request: web.Request):
    b = request.app["bot"]
    html = PAGE.format(
        nom=b.user.name if b.user else "Gestion",
        serveurs=len(b.guilds),
        membres=sum(g.member_count or 0 for g in b.guilds),
        ping=round(b.latency * 1000) if b.latency == b.latency else 0,
    )
    return web.Response(text=html, content_type="text/html")


async def health(request: web.Request):
    return web.json_response({"status": "ok"})


async def lancer_site(b: commands.Bot):
    app = web.Application()
    app["bot"] = b
    app.router.add_get("/", page_accueil)
    app.router.add_get("/health", health)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.getenv("PORT", 8080))
    await web.TCPSite(runner, "0.0.0.0", port).start()
    print(f"Site web lancé sur le port {port}")


# ===================== TICKETS =====================
TICKET_COULEUR = 0x1F4FFF


def ticket_info(ch):
    """Retourne (id_proprio, id_claim ou None) si le salon est un ticket, sinon None."""
    t = getattr(ch, "topic", None) or ""
    if not t.startswith("ticket:"):
        return None
    try:
        parts = t.split("|")
        owner = int(parts[0].split(":")[1])
        claim = int(parts[1].split(":")[1]) if len(parts) > 1 else None
    except (ValueError, IndexError):
        return None
    return owner, claim


def est_staff(inter: discord.Interaction) -> bool:
    p = inter.user.guild_permissions
    if p.manage_channels or p.administrator:
        return True
    role_id = get_conf(inter.guild.id)["staff_role"]
    return bool(role_id) and any(r.id == role_id for r in inter.user.roles)


class ChoixMembre(discord.ui.View):
    """Menu éphémère pour choisir le membre à ajouter / retirer."""

    def __init__(self, ajout: bool):
        super().__init__(timeout=60)
        self.ajout = ajout

    @discord.ui.select(cls=discord.ui.UserSelect, placeholder="Choisis un membre", min_values=1, max_values=1)
    async def choisir(self, inter: discord.Interaction, select: discord.ui.UserSelect):
        cible = select.values[0]
        membre = inter.guild.get_member(cible.id)
        if membre is None:
            return await inter.response.edit_message(content="❌ Membre introuvable.", view=None)
        ch = inter.channel
        info = ticket_info(ch)
        try:
            if self.ajout:
                await ch.set_permissions(
                    membre, view_channel=True, send_messages=True,
                    read_message_history=True, attach_files=True,
                )
                await inter.response.edit_message(content="✅ Fait.", view=None)
                await ch.send(f"➕ {membre.mention} a été ajouté au ticket par {inter.user.mention}.")
            else:
                if membre.bot or (info and membre.id == info[0]):
                    return await inter.response.edit_message(content="❌ Impossible de retirer ce membre.", view=None)
                await ch.set_permissions(membre, overwrite=None)
                await inter.response.edit_message(content="✅ Fait.", view=None)
                await ch.send(f"➖ {membre.mention} a été retiré du ticket par {inter.user.mention}.")
        except discord.Forbidden:
            await inter.response.edit_message(content="❌ Il me manque la permission « Gérer les salons ».", view=None)


class RenameModal(discord.ui.Modal, title="Renommer le ticket"):
    nom = discord.ui.TextInput(label="Nouveau nom", placeholder="ex : problème-paiement", max_length=90)

    async def on_submit(self, inter: discord.Interaction):
        try:
            await inter.channel.edit(name=str(self.nom), reason=f"Renommé par {inter.user}")
        except discord.Forbidden:
            return await refus(inter, "❌ Il me manque la permission « Gérer les salons ».")
        await inter.response.send_message(f"✏️ Ticket renommé en **{self.nom}** par {inter.user.mention}.")


class TicketControl(discord.ui.View):
    def __init__(self, claimed: bool = False):
        super().__init__(timeout=None)
        if claimed:
            self.claim.disabled = True
            self.claim.label = "Pris en charge"

    @discord.ui.button(label="Claim", emoji="👋", style=discord.ButtonStyle.primary, custom_id="ticket:claim")
    async def claim(self, inter: discord.Interaction, bouton: discord.ui.Button):
        info = ticket_info(inter.channel)
        if not info:
            return await refus(inter, "❌ Ce n'est pas un ticket.")
        if not est_staff(inter):
            return await refus(inter, "❌ Réservé au staff.")
        owner, claim = info
        if claim:
            return await refus(inter, f"❌ Déjà pris en charge par <@{claim}>.")
        await inter.response.edit_message(view=TicketControl(claimed=True))
        try:
            await inter.channel.edit(topic=f"ticket:{owner}|claim:{inter.user.id}")
        except discord.HTTPException:
            pass
        await inter.channel.send(embed=emb("Ticket pris en charge", f"{inter.user.mention} s'occupe de ce ticket.", 0x57F287))
        await log(inter.guild, emb("Ticket claim", f"{inter.channel.mention} pris par {inter.user.mention}", 0x57F287))

    @discord.ui.button(label="Fermer", emoji="🔒", style=discord.ButtonStyle.danger, custom_id="ticket:close")
    async def fermer(self, inter: discord.Interaction, bouton: discord.ui.Button):
        ch = inter.channel
        info = ticket_info(ch)
        if not info:
            return await refus(inter, "❌ Ce n'est pas un ticket.")
        if not (info[0] == inter.user.id or est_staff(inter)):
            return await refus(inter, "❌ Tu ne peux pas fermer ce ticket.")
        await inter.response.send_message("🔒 Ticket fermé, suppression dans 5 secondes…")
        await log(inter.guild, emb("Ticket fermé", f"{ch.name} fermé par {inter.user.mention}", 0xFEE75C))
        await asyncio.sleep(5)
        try:
            await ch.delete(reason=f"Ticket fermé par {inter.user}")
        except discord.HTTPException:
            pass

    @discord.ui.button(label="Ajouter", emoji="➕", style=discord.ButtonStyle.secondary, custom_id="ticket:add")
    async def ajouter(self, inter: discord.Interaction, bouton: discord.ui.Button):
        if not ticket_info(inter.channel):
            return await refus(inter, "❌ Ce n'est pas un ticket.")
        if not est_staff(inter):
            return await refus(inter, "❌ Réservé au staff.")
        await inter.response.send_message("Choisis le membre à ajouter :", view=ChoixMembre(True), ephemeral=True)

    @discord.ui.button(label="Retirer", emoji="➖", style=discord.ButtonStyle.secondary, custom_id="ticket:remove")
    async def retirer(self, inter: discord.Interaction, bouton: discord.ui.Button):
        if not ticket_info(inter.channel):
            return await refus(inter, "❌ Ce n'est pas un ticket.")
        if not est_staff(inter):
            return await refus(inter, "❌ Réservé au staff.")
        await inter.response.send_message("Choisis le membre à retirer :", view=ChoixMembre(False), ephemeral=True)

    @discord.ui.button(label="Renommer", emoji="✏️", style=discord.ButtonStyle.secondary, custom_id="ticket:rename")
    async def renommer(self, inter: discord.Interaction, bouton: discord.ui.Button):
        if not ticket_info(inter.channel):
            return await refus(inter, "❌ Ce n'est pas un ticket.")
        if not est_staff(inter):
            return await refus(inter, "❌ Réservé au staff.")
        await inter.response.send_modal(RenameModal())


class TicketPanel(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Ouvrir un ticket", style=discord.ButtonStyle.primary, custom_id="ticket:open")
    async def ouvrir(self, inter: discord.Interaction, bouton: discord.ui.Button):
        guild, user = inter.guild, inter.user
        for ch in guild.text_channels:
            info = ticket_info(ch)
            if info and info[0] == user.id:
                return await refus(inter, f"Tu as déjà un ticket ouvert : {ch.mention}")

        conf = get_conf(guild.id)
        staff = guild.get_role(conf["staff_role"]) if conf["staff_role"] else None
        ow = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            user: discord.PermissionOverwrite(
                view_channel=True, send_messages=True, attach_files=True, read_message_history=True
            ),
            guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True, manage_channels=True),
        }
        if staff:
            ow[staff] = discord.PermissionOverwrite(
                view_channel=True, send_messages=True, read_message_history=True, manage_messages=True
            )

        await inter.response.defer(ephemeral=True)
        try:
            ch = await guild.create_text_channel(
                name=f"ticket-{user.name}"[:90],
                category=inter.channel.category,
                overwrites=ow,
                topic=f"ticket:{user.id}",
                reason=f"Ticket de {user}",
            )
        except discord.Forbidden:
            return await refus(inter, "❌ Il me manque la permission « Gérer les salons ».")

        e = discord.Embed(
            title=f"Ticket ouvert par {user.display_name}",
            description="Merci d'avoir contacté le support\nDécrivez votre problème puis attendez de recevoir une réponse",
            color=TICKET_COULEUR,
        )
        e.set_thumbnail(url=user.display_avatar.url)
        # Ping uniquement le membre (pas le staff)
        await ch.send(content=user.mention, embed=e, view=TicketControl())
        await inter.followup.send(f"✅ Ticket créé : {ch.mention}", ephemeral=True)
        await log(guild, emb("Ticket ouvert", f"{ch.mention} par {user.mention}", 0x57F287))


# ===================== BOT =====================
intents = discord.Intents.default()
intents.members = True          # Server Members Intent (portail développeur)
intents.message_content = True  # Message Content Intent (portail développeur)


class Gestion(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix=commands.when_mentioned_or("."), intents=intents, help_command=None)
        self.synced = False

    async def setup_hook(self):
        init_db()
        self.add_view(TicketPanel())
        self.add_view(TicketControl())
        await lancer_site(self)

    async def sync_guild(self, guild: discord.Guild):
        # Sync par serveur = les commandes apparaissent tout de suite
        self.tree.copy_global_to(guild=guild)
        await self.tree.sync(guild=guild)


bot = Gestion()


@bot.event
async def on_ready():
    print(f"Connecté en tant que {bot.user} ({bot.user.id})")
    if not bot.synced:
        for g in bot.guilds:
            try:
                await bot.sync_guild(g)
            except discord.HTTPException as e:
                print(f"Sync impossible sur {g.name} : {e}")
        bot.synced = True
        print("Commandes synchronisées.")


@bot.event
async def on_guild_join(guild: discord.Guild):
    await bot.sync_guild(guild)


@bot.tree.error
async def on_app_error(inter: discord.Interaction, error: app_commands.AppCommandError):
    if isinstance(error, app_commands.MissingPermissions):
        return await refus(inter, "❌ Tu n'as pas la permission pour ça.")
    print(f"Erreur commande : {error!r}")
    await refus(inter, "❌ Une erreur est survenue.")


# ===================== ÉVÉNEMENTS =====================
@bot.event
async def on_member_join(m: discord.Member):
    conf = get_conf(m.guild.id)
    if conf["autorole"]:
        role = m.guild.get_role(conf["autorole"])
        if role:
            try:
                await m.add_roles(role, reason="Autorole")
            except discord.HTTPException:
                pass
    if conf["welcome_channel"]:
        ch = m.guild.get_channel(conf["welcome_channel"])
        if ch:
            msg = conf["welcome_msg"] or "Bienvenue {user} sur **{server}** ! Nous sommes {count}."
            msg = (
                msg.replace("{user}", m.mention)
                .replace("{server}", m.guild.name)
                .replace("{count}", str(m.guild.member_count))
            )
            try:
                await ch.send(msg)
            except discord.HTTPException:
                pass
    await log(m.guild, emb("Arrivée", f"{m.mention} ({m}) a rejoint.", 0x57F287))


@bot.event
async def on_member_remove(m: discord.Member):
    await log(m.guild, emb("Départ", f"{m} a quitté le serveur.", 0xED4245))


@bot.event
async def on_message_delete(msg: discord.Message):
    if msg.guild and not msg.author.bot:
        txt = (msg.content or "(vide)")[:1000]
        await log(msg.guild, emb("Message supprimé", f"**{msg.author}** dans {msg.channel.mention}\n{txt}", 0xFEE75C))


@bot.event
async def on_message_edit(avant: discord.Message, apres: discord.Message):
    if avant.guild and not avant.author.bot and avant.content != apres.content:
        await log(
            avant.guild,
            emb(
                "Message modifié",
                f"**{avant.author}** dans {avant.channel.mention}\n"
                f"Avant : {(avant.content or '(vide)')[:500]}\nAprès : {(apres.content or '(vide)')[:500]}",
                0xFEE75C,
            ),
        )


LIEN = re.compile(r"(https?://|discord\.gg/|discord\.com/invite/)", re.I)


@bot.event
async def on_message(msg: discord.Message):
    if msg.author.bot:
        return
    if msg.guild and get_conf(msg.guild.id)["antilink"] and LIEN.search(msg.content):
        if not msg.author.guild_permissions.manage_messages:
            try:
                await msg.delete()
                await msg.channel.send(f"🚫 {msg.author.mention}, les liens sont interdits ici.", delete_after=5)
                await log(msg.guild, emb("Anti-lien", f"Message de {msg.author.mention} supprimé.", 0xED4245))
            except discord.HTTPException:
                pass
            return
    await bot.process_commands(msg)


@bot.event
async def on_command_error(ctx: commands.Context, error: commands.CommandError):
    if isinstance(error, commands.CommandNotFound):
        return
    print(f"Erreur commande préfixe : {error!r}")


# ===================== MODÉRATION =====================
@bot.tree.command(name="ban", description="Bannir un membre")
@app_commands.describe(membre="Le membre à bannir", raison="Raison du ban")
@perm(ban_members=True)
async def ban(inter: discord.Interaction, membre: discord.Member, raison: str = "Aucune raison"):
    if not peut_agir(inter, membre):
        return await refus(inter, "❌ Tu ne peux pas faire ça sur ce membre.")
    try:
        await membre.ban(reason=f"{inter.user} : {raison}")
    except discord.Forbidden:
        return await refus(inter, "❌ Mon rôle est trop bas pour ce membre.")
    e = emb("Ban", f"{membre.mention} a été banni.\n**Raison :** {raison}", 0xED4245)
    await inter.response.send_message(embed=e)
    await log(inter.guild, e)


@bot.tree.command(name="unban", description="Débannir un utilisateur avec son ID")
@app_commands.describe(user_id="ID de l'utilisateur")
@perm(ban_members=True)
async def unban(inter: discord.Interaction, user_id: str):
    try:
        await inter.guild.unban(discord.Object(id=int(user_id)))
    except (ValueError, discord.NotFound):
        return await refus(inter, "❌ ID invalide ou utilisateur non banni.")
    e = emb("Unban", f"<@{user_id}> a été débanni.", 0x57F287)
    await inter.response.send_message(embed=e)
    await log(inter.guild, e)


@bot.tree.command(name="kick", description="Expulser un membre")
@app_commands.describe(membre="Le membre à expulser", raison="Raison")
@perm(kick_members=True)
async def kick(inter: discord.Interaction, membre: discord.Member, raison: str = "Aucune raison"):
    if not peut_agir(inter, membre):
        return await refus(inter, "❌ Tu ne peux pas faire ça sur ce membre.")
    try:
        await membre.kick(reason=f"{inter.user} : {raison}")
    except discord.Forbidden:
        return await refus(inter, "❌ Mon rôle est trop bas pour ce membre.")
    e = emb("Kick", f"{membre.mention} a été expulsé.\n**Raison :** {raison}", 0xFEE75C)
    await inter.response.send_message(embed=e)
    await log(inter.guild, e)


@bot.tree.command(name="mute", description="Rendre muet un membre (timeout)")
@app_commands.describe(membre="Le membre", minutes="Durée en minutes (max 40320)", raison="Raison")
@perm(moderate_members=True)
async def mute(inter: discord.Interaction, membre: discord.Member,
               minutes: app_commands.Range[int, 1, 40320] = 10, raison: str = "Aucune raison"):
    if not peut_agir(inter, membre):
        return await refus(inter, "❌ Tu ne peux pas faire ça sur ce membre.")
    try:
        await membre.timeout(dt.timedelta(minutes=minutes), reason=f"{inter.user} : {raison}")
    except discord.Forbidden:
        return await refus(inter, "❌ Mon rôle est trop bas pour ce membre.")
    e = emb("Mute", f"{membre.mention} muet pendant **{minutes} min**.\n**Raison :** {raison}", 0xFEE75C)
    await inter.response.send_message(embed=e)
    await log(inter.guild, e)


@bot.tree.command(name="unmute", description="Retirer le mute d'un membre")
@app_commands.describe(membre="Le membre")
@perm(moderate_members=True)
async def unmute(inter: discord.Interaction, membre: discord.Member):
    try:
        await membre.timeout(None, reason=f"Unmute par {inter.user}")
    except discord.Forbidden:
        return await refus(inter, "❌ Mon rôle est trop bas pour ce membre.")
    e = emb("Unmute", f"{membre.mention} n'est plus muet.", 0x57F287)
    await inter.response.send_message(embed=e)
    await log(inter.guild, e)


@bot.tree.command(name="clear", description="Supprimer des messages du salon")
@app_commands.describe(nombre="Nombre de messages (1 à 100)")
@perm(manage_messages=True)
async def clear(inter: discord.Interaction, nombre: app_commands.Range[int, 1, 100]):
    await inter.response.defer(ephemeral=True)
    try:
        supprimes = await inter.channel.purge(limit=nombre)
    except discord.Forbidden:
        return await refus(inter, "❌ Il me manque la permission « Gérer les messages ».")
    await inter.followup.send(f"🧹 {len(supprimes)} message(s) supprimé(s).", ephemeral=True)
    await log(inter.guild, emb("Clear", f"{len(supprimes)} messages supprimés dans {inter.channel.mention} par {inter.user.mention}"))


@bot.tree.command(name="warn", description="Avertir un membre")
@app_commands.describe(membre="Le membre", raison="Raison")
@perm(moderate_members=True)
async def warn(inter: discord.Interaction, membre: discord.Member, raison: str = "Aucune raison"):
    if not peut_agir(inter, membre):
        return await refus(inter, "❌ Tu ne peux pas faire ça sur ce membre.")
    run(
        "INSERT INTO warns(guild_id,user_id,mod_id,reason,ts) VALUES(?,?,?,?,?)",
        (inter.guild.id, membre.id, inter.user.id, raison, discord.utils.utcnow().isoformat()),
    )
    n = run("SELECT COUNT(*) c FROM warns WHERE guild_id=? AND user_id=?", (inter.guild.id, membre.id), one=True)["c"]
    txt = f"{membre.mention} averti ({n}/{MAX_WARNS}).\n**Raison :** {raison}"
    if n >= MAX_WARNS:
        try:
            await membre.timeout(dt.timedelta(minutes=SANCTION_MIN), reason="Trop d'avertissements")
            txt += f"\n⚠️ Sanction auto : mute {SANCTION_MIN} min."
        except discord.HTTPException:
            pass
    e = emb("Warn", txt, 0xFEE75C)
    await inter.response.send_message(embed=e)
    await log(inter.guild, e)


@bot.tree.command(name="warns", description="Voir les avertissements d'un membre")
@app_commands.describe(membre="Le membre")
@perm(moderate_members=True)
async def warns(inter: discord.Interaction, membre: discord.Member):
    lignes = run(
        "SELECT * FROM warns WHERE guild_id=? AND user_id=? ORDER BY id DESC LIMIT 15",
        (inter.guild.id, membre.id), many=True,
    )
    if not lignes:
        return await inter.response.send_message(f"✅ {membre.mention} n'a aucun avertissement.", ephemeral=True)
    txt = "\n".join(f"`#{w['id']}` {w['reason']} — par <@{w['mod_id']}>" for w in lignes)
    await inter.response.send_message(embed=emb(f"Avertissements de {membre}", txt), ephemeral=True)


@bot.tree.command(name="clearwarns", description="Effacer les avertissements d'un membre")
@app_commands.describe(membre="Le membre")
@perm(moderate_members=True)
async def clearwarns(inter: discord.Interaction, membre: discord.Member):
    run("DELETE FROM warns WHERE guild_id=? AND user_id=?", (inter.guild.id, membre.id))
    await inter.response.send_message(f"🗑️ Avertissements de {membre.mention} effacés.")
    await log(inter.guild, emb("Clearwarns", f"{membre.mention} par {inter.user.mention}", 0x57F287))


@bot.tree.command(name="lock", description="Verrouiller le salon")
@perm(manage_channels=True)
async def lock(inter: discord.Interaction):
    ow = inter.channel.overwrites_for(inter.guild.default_role)
    ow.send_messages = False
    await inter.channel.set_permissions(inter.guild.default_role, overwrite=ow)
    await inter.response.send_message("🔒 Salon verrouillé.")
    await log(inter.guild, emb("Lock", f"{inter.channel.mention} par {inter.user.mention}", 0xED4245))


@bot.tree.command(name="unlock", description="Déverrouiller le salon")
@perm(manage_channels=True)
async def unlock(inter: discord.Interaction):
    ow = inter.channel.overwrites_for(inter.guild.default_role)
    ow.send_messages = None
    await inter.channel.set_permissions(inter.guild.default_role, overwrite=ow)
    await inter.response.send_message("🔓 Salon déverrouillé.")
    await log(inter.guild, emb("Unlock", f"{inter.channel.mention} par {inter.user.mention}", 0x57F287))


@bot.tree.command(name="slowmode", description="Définir le mode lent du salon")
@app_commands.describe(secondes="0 pour désactiver (max 21600)")
@perm(manage_channels=True)
async def slowmode(inter: discord.Interaction, secondes: app_commands.Range[int, 0, 21600]):
    await inter.channel.edit(slowmode_delay=secondes)
    await inter.response.send_message(f"🐌 Mode lent : **{secondes}s**.")


# ===================== CONFIGURATION =====================
@bot.tree.command(name="setlogs", description="Définir le salon des logs")
@app_commands.describe(salon="Salon des logs")
@perm(manage_guild=True)
async def setlogs(inter: discord.Interaction, salon: discord.TextChannel):
    set_conf(inter.guild.id, log_channel=salon.id)
    await inter.response.send_message(f"✅ Logs dans {salon.mention}.", ephemeral=True)


@bot.tree.command(name="setwelcome", description="Définir le salon et le message de bienvenue")
@app_commands.describe(salon="Salon de bienvenue", message="Variables : {user} {server} {count}")
@perm(manage_guild=True)
async def setwelcome(inter: discord.Interaction, salon: discord.TextChannel, message: str = None):
    set_conf(inter.guild.id, welcome_channel=salon.id, welcome_msg=message)
    await inter.response.send_message(f"✅ Bienvenue dans {salon.mention}.", ephemeral=True)


@bot.tree.command(name="setautorole", description="Rôle donné automatiquement aux nouveaux membres")
@app_commands.describe(role="Le rôle à donner")
@perm(manage_guild=True)
async def setautorole(inter: discord.Interaction, role: discord.Role):
    set_conf(inter.guild.id, autorole=role.id)
    await inter.response.send_message(f"✅ Autorole : {role.mention}.", ephemeral=True)


@bot.tree.command(name="setstaff", description="Rôle du staff (accès aux tickets)")
@app_commands.describe(role="Le rôle staff")
@perm(manage_guild=True)
async def setstaff(inter: discord.Interaction, role: discord.Role):
    set_conf(inter.guild.id, staff_role=role.id)
    await inter.response.send_message(f"✅ Rôle staff : {role.mention}.", ephemeral=True)


@bot.tree.command(name="antilink", description="Activer ou désactiver l'anti-lien")
@app_commands.describe(actif="Activer l'anti-lien ?")
@perm(manage_guild=True)
async def antilink(inter: discord.Interaction, actif: bool):
    set_conf(inter.guild.id, antilink=int(actif))
    await inter.response.send_message(f"✅ Anti-lien **{'activé' if actif else 'désactivé'}**.", ephemeral=True)


@bot.tree.command(name="ticketpanel", description="Envoyer le panneau de tickets dans ce salon")
@perm(manage_guild=True)
async def ticketpanel(inter: discord.Interaction):
    e = emb("Support", "Clique sur le bouton ci-dessous pour ouvrir un ticket privé avec le staff.")
    await inter.channel.send(embed=e, view=TicketPanel())
    await inter.response.send_message("✅ Panneau envoyé.", ephemeral=True)


# ===================== INFOS =====================
@bot.tree.command(name="serverinfo", description="Infos sur le serveur")
@app_commands.guild_only()
async def serverinfo(inter: discord.Interaction):
    g = inter.guild
    e = emb(g.name)
    e.add_field(name="Membres", value=str(g.member_count))
    e.add_field(name="Salons", value=str(len(g.channels)))
    e.add_field(name="Rôles", value=str(len(g.roles)))
    e.add_field(name="Créé le", value=discord.utils.format_dt(g.created_at, "D"))
    e.add_field(name="Propriétaire", value=f"<@{g.owner_id}>")
    if g.icon:
        e.set_thumbnail(url=g.icon.url)
    await inter.response.send_message(embed=e)


@bot.tree.command(name="userinfo", description="Infos sur un membre")
@app_commands.describe(membre="Le membre (toi par défaut)")
@app_commands.guild_only()
async def userinfo(inter: discord.Interaction, membre: discord.Member = None):
    m = membre or inter.user
    e = emb(str(m))
    e.add_field(name="ID", value=str(m.id))
    e.add_field(name="Compte créé", value=discord.utils.format_dt(m.created_at, "D"))
    e.add_field(name="A rejoint", value=discord.utils.format_dt(m.joined_at, "D") if m.joined_at else "?")
    e.add_field(name="Rôle principal", value=m.top_role.mention)
    e.set_thumbnail(url=m.display_avatar.url)
    await inter.response.send_message(embed=e)


# ===================== .HELP =====================
AIDE = {
    "accueil": {
        "titre": "Accueil",
        "desc": "Présentation du bot",
        "texte": (
            "Bienvenue ! Utilise le menu ci-dessous pour parcourir les commandes.\n\n"
            "**Préfixe :** `.`\n"
            "**Commandes slash :** tape `/` pour les voir\n"
            "**Aide :** `.help`\n\n"
            "Modération, avertissements, logs, bienvenue, anti-lien et tickets."
        ),
    },
    "moderation": {
        "titre": "Modération",
        "desc": "Ban, kick, mute, clear...",
        "texte": (
            "`/ban membre raison` — Bannir un membre\n"
            "`/unban user_id` — Débannir avec l'ID\n"
            "`/kick membre raison` — Expulser un membre\n"
            "`/mute membre minutes raison` — Rendre muet (timeout)\n"
            "`/unmute membre` — Retirer le mute\n"
            "`/clear nombre` — Supprimer des messages\n"
            "`/lock` · `/unlock` — Verrouiller / déverrouiller le salon\n"
            "`/slowmode secondes` — Mode lent"
        ),
    },
    "warns": {
        "titre": "Avertissements",
        "desc": "Warn et sanction automatique",
        "texte": (
            "`/warn membre raison` — Avertir un membre\n"
            "`/warns membre` — Voir ses avertissements\n"
            "`/clearwarns membre` — Effacer ses avertissements\n\n"
            f"À **{MAX_WARNS} warns**, le membre est mute {SANCTION_MIN} min automatiquement."
        ),
    },
    "config": {
        "titre": "Configuration",
        "desc": "Logs, bienvenue, staff, anti-lien",
        "texte": (
            "`/setlogs salon` — Salon des logs\n"
            "`/setwelcome salon message` — Bienvenue (`{user}` `{server}` `{count}`)\n"
            "`/setautorole role` — Rôle donné aux nouveaux\n"
            "`/setstaff role` — Rôle staff (accès aux tickets)\n"
            "`/antilink actif` — Activer / désactiver l'anti-lien"
        ),
    },
    "tickets": {
        "titre": "Tickets",
        "desc": "Système de support",
        "texte": (
            "`/ticketpanel` — Envoie le panneau d'ouverture de tickets\n\n"
            "Dans un ticket :\n"
            "👋 **Claim** — Prendre en charge (staff)\n"
            "🔒 **Fermer** — Fermer le ticket\n"
            "➕ **Ajouter** — Ajouter un membre (staff)\n"
            "➖ **Retirer** — Retirer un membre (staff)\n"
            "✏️ **Renommer** — Renommer le salon (staff)"
        ),
    },
    "infos": {
        "titre": "Infos",
        "desc": "Infos serveur et membres",
        "texte": (
            "`/serverinfo` — Infos sur le serveur\n"
            "`/userinfo membre` — Infos sur un membre\n"
            "`.help` — Ce menu"
        ),
    },
}


def help_embed(cat: str) -> discord.Embed:
    d = AIDE[cat]
    e = discord.Embed(title=f"Aide — {d['titre']}", description=d["texte"], color=COULEUR)
    e.set_footer(text="Commandes slash : tape / | Préfixe : .")
    return e


class HelpView(discord.ui.View):
    def __init__(self, auteur_id: int):
        super().__init__(timeout=120)
        self.auteur_id = auteur_id

    @discord.ui.select(
        placeholder="Choisis une catégorie",
        options=[discord.SelectOption(label=v["titre"], value=k, description=v["desc"]) for k, v in AIDE.items()],
    )
    async def choisir(self, inter: discord.Interaction, select: discord.ui.Select):
        if inter.user.id != self.auteur_id:
            return await refus(inter, "❌ Ce menu n'est pas pour toi. Tape `.help` pour avoir le tien.")
        await inter.response.edit_message(embed=help_embed(select.values[0]), view=self)


@bot.command(name="help", aliases=["aide"])
async def help_cmd(ctx: commands.Context):
    await ctx.send(embed=help_embed("accueil"), view=HelpView(ctx.author.id))


# ===================== LANCEMENT =====================
if __name__ == "__main__":
    print(
        f"[diag] variable DISCORD_TOKEN trouvée : {_brut is not None} | "
        f"longueur : {len(TOKEN)} | points : {TOKEN.count('.')} (un vrai token a 2 points)"
    )
    if TOKEN == "COLLE_TON_TOKEN_ICI":
        print("[diag] ERREUR : la variable DISCORD_TOKEN n'existe pas (vérifie le nom exact).")
        sys.exit(1)
    bot.run(TOKEN)
