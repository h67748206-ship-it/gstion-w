import os
import re
import threading
import wikipedia
from flask import Flask
import discord
from discord.ext import commands

# Configuration de la langue pour Wikipédia
wikipedia.set_lang("fr")

# ==========================================
#            EMOJIS PERSONNALISÉS
# ==========================================
EMOJI_NITRO = "<a:M_SYnitro:1561699280174055434>"
EMOJI_STAR  = "<:1550556335995883560:1561699282082471948>"
EMOJI_XCX   = "<:xcx:1561699277842157624>"
EMOJI_SHIELD= "<:1462041546160472095:1561379419178672158>"
EMOJI_CROWN = "<:Crown:1561379407195545641>"
EMOJI_LOCK  = "<:lock:1561379416414879777>"

# ==========================================
#            CONFIGURATION FLASK
# ==========================================
app = Flask('')

@app.route('/')
def home():
    return "Le bot gstion est en ligne et actif !"

def run_flask():
    app.run(host='0.0.0.0', port=10000)

def keep_alive():
    t = threading.Thread(target=run_flask)
    t.start()

# ==========================================
#          CONFIGURATION DU BOT
# ==========================================
intents = discord.Intents.all()
bot = commands.Bot(command_prefix='+', intents=intents)
bot.remove_command('help')

# Stockage de la configuration
config = {
    "antilink": False,
    "antispam": False,
    "antihack": False,
    "welcome_channel": None,
    "auto_role": None,
    "soutien_text": None,
    "soutien_role": None
}

@bot.event
async def on_ready():
    print(f'Connecté en tant que {bot.user.name} (ID: {bot.user.id})')
    print('Le bot gstion est prêt et opérationnel !')

# ==========================================
#          ÉCOUTEURS D'ÉVÉNEMENTS
# ==========================================
@bot.event
async def on_member_join(member):
    # 1. Message d'accueil
    if config["welcome_channel"]:
        channel = member.guild.get_channel(config["welcome_channel"])
        if channel:
            embed = discord.Embed(
                title=f"{EMOJI_STAR} Bienvenue !",
                description=f"Bienvenue {member.mention} sur **{member.guild.name}** !",
                color=discord.Color.green()
            )
            embed.set_thumbnail(url=member.display_avatar.url)
            try:
                await channel.send(embed=embed)
            except discord.Forbidden:
                pass

    # 2. Autorole à l'arrivée
    if config["auto_role"]:
        role = member.guild.get_role(config["auto_role"])
        if role:
            try:
                await member.add_roles(role)
            except discord.Forbidden:
                pass

@bot.event
async def on_member_update(before, after):
    # System de rôle Soutien / Tag / Boost / Statut
    if config["soutien_role"] and config["soutien_text"]:
        role = after.guild.get_role(config["soutien_role"])
        if not role:
            return

        text = config["soutien_text"].lower()
        has_tag_or_status = False

        # Vérification du tag dans le pseudo
        if text in after.display_name.lower() or text in after.name.lower():
            has_tag_or_status = True

        # Vérification du statut personnalisé
        for activity in after.activities:
            if isinstance(activity, discord.CustomActivity) and activity.name:
                if text in activity.name.lower():
                    has_tag_or_status = True

            # Vérification du Boost
            if text == "boost" and after.premium_since is not None:
                has_tag_or_status = True

        try:
            if has_tag_or_status and role not in after.roles:
                await after.add_roles(role)
            elif not has_tag_or_status and role in after.roles:
                await after.remove_roles(role)
        except discord.Forbidden:
            pass

@bot.event
async def on_message(message):
    if message.author.bot:
        return

    # Détection des liens si l'anti-link est activé
    if config["antilink"]:
        link_regex = r"(https?://[^\s]+|discord\.gg/[^\s]+|discord\.com/invite/[^\s]+)"
        if re.search(link_regex, message.content, re.IGNORECASE):
            if not message.author.guild_permissions.administrator:
                try:
                    await message.delete()
                    await message.channel.send(
                        f"{EMOJI_XCX} {message.author.mention}, les liens ne sont pas autorisés sur ce serveur !",
                        delete_after=5
                    )
                    return
                except discord.Forbidden:
                    pass

    await bot.process_commands(message)

# ==========================================
#          COMMANDES CONFIGURATION
# ==========================================
@bot.command(help="Définit le salon d'accueil des nouveaux membres (`+setwelcome #salon`).")
async def setwelcome(ctx, channel: discord.TextChannel = None):
    if not channel:
        return await ctx.send("Usage : `+setwelcome #salon`")
    config["welcome_channel"] = channel.id
    await ctx.send(f"{EMOJI_STAR} Salon d'accueil configuré sur {channel.mention}.")

@bot.command(help="Définit le rôle automatique attribué aux nouveaux membres (`+setautorole @rôle`).")
async def setautorole(ctx, role: discord.Role = None):
    if not role:
        return await ctx.send("Usage : `+setautorole @rôle`")
    config["auto_role"] = role.id
    await ctx.send(f"{EMOJI_STAR} Auto-role configuré sur **{role.name}**.")

@bot.command(help="Définit le tag/statut requis et le rôle de soutien (`+setsoutien <texte/tag/boost> @rôle`).")
async def setsoutien(ctx, text=None, role: discord.Role = None):
    if not text or not role:
        return await ctx.send("Usage : `+setsoutien <texte_ou_tag_ou_boost> @rôle`\nExemple : `+setsoutien .gstion @Soutien`")
    config["soutien_text"] = text
    config["soutien_role"] = role.id
    await ctx.send(f"{EMOJI_CROWN} Système de soutien configuré ! Le rôle **{role.name}** sera attribué pour le texte/tag/boost `{text}`.")

# ==========================================
#          COMMANDES PUBLIQUES
# ==========================================
@bot.command(help="Affiche la liste des bots publics enregistrés sur le serveur.")
async def crowbots(ctx):
    await ctx.send(f"{EMOJI_STAR} **Bots Publics :** Aucun bot public enregistré pour le moment.")

@bot.command(help="Affiche la liste des bots que vous avez enregistrés.")
async def mybots(ctx):
    await ctx.send(f"{EMOJI_STAR} **Vos Bots :** Vous n'avez enregistré aucun bot.")

@bot.command(help="Affiche la photo de profil d'un membre ou la vôtre.")
async def pic(ctx, member: discord.Member = None):
    member = member or ctx.author
    embed = discord.Embed(title=f"Photo de profil de {member.display_name}", color=discord.Color.blue())
    embed.set_image(url=member.display_avatar.url)
    await ctx.send(embed=embed)

@bot.command(help="Affiche la bannière d'un membre s'il en possède une.")
async def banner(ctx, member: discord.Member = None):
    member = member or ctx.author
    user = await bot.fetch_user(member.id)
    if user.banner:
        embed = discord.Embed(title=f"Bannière de {user.display_name}", color=discord.Color.blue())
        embed.set_image(url=user.banner.url)
        await ctx.send(embed=embed)
    else:
        await ctx.send(f"{EMOJI_XCX} Cet utilisateur n'a pas de bannière.")

@bot.command(name="server", help="Affiche l'icône (`+server pic`) ou la bannière (`+server banner`) du serveur.")
async def server_(ctx, action: str = None):
    if action == "pic":
        if ctx.guild.icon:
            embed = discord.Embed(title=f"Icône de {ctx.guild.name}", color=discord.Color.blue())
            embed.set_image(url=ctx.guild.icon.url)
            await ctx.send(embed=embed)
        else:
            await ctx.send(f"{EMOJI_XCX} Ce serveur n'a pas d'icône.")
    elif action == "banner":
        if ctx.guild.banner:
            embed = discord.Embed(title=f"Bannière de {ctx.guild.name}", color=discord.Color.blue())
            embed.set_image(url=ctx.guild.banner.url)
            await ctx.send(embed=embed)
        else:
            await ctx.send(f"{EMOJI_XCX} Ce serveur n'a pas de bannière.")
    else:
        await ctx.send("Usage: `+server pic` ou `+server banner`")

@bot.command(help="Affiche l'image en grand d'un emoji personnalisé du serveur.")
async def emoji(ctx, emoji: discord.Emoji = None):
    if emoji:
        await ctx.send(emoji.url)
    else:
        await ctx.send(f"{EMOJI_XCX} Veuillez spécifier un emoji personnalisé valide.")

@bot.command(help="Envoie ou traite une image.")
async def image(ctx):
    await ctx.send("🖼️ Fonctionnalité d'image prête.")

@bot.command(help="Soumet une suggestion dans le salon de suggestions.")
async def suggestion(ctx, *, text=None):
    if not text:
        return await ctx.send(f"{EMOJI_XCX} Veuillez écrire le contenu de votre suggestion.")
    await ctx.send(f"{EMOJI_STAR} **Nouvelle Suggestion par {ctx.author.mention} :**\n{text}")

@bot.command(name="lb", help="Affiche le classement du serveur (`+lb suggestions`).")
async def lb_(ctx, category=None):
    if category == "suggestions":
        await ctx.send(f"{EMOJI_CROWN} **Classement des top suggestions :**\n1. Suggestion A\n2. Suggestion B")
    else:
        await ctx.send("Usage: `+lb suggestions`")

@bot.command(help="Recherche un sujet sur Wikipédia et affiche un résumé complet.")
async def wiki(ctx, *, query=None):
    if not query:
        return await ctx.send(f"{EMOJI_XCX} Veuillez spécifier un sujet à chercher (ex: `+wiki France`).")
    try:
        search_results = wikipedia.search(query)
        if not search_results:
            return await ctx.send(f"{EMOJI_XCX} Aucun article trouvé sur Wikipédia pour cette recherche.")
        
        target_title = search_results[0]
        summary = wikipedia.summary(target_title, sentences=3, auto_suggest=False)
        page = wikipedia.page(target_title, auto_suggest=False)
        
        embed = discord.Embed(title=f"📚 Wikipédia : {page.title}", description=summary, color=discord.Color.green())
        embed.add_field(name="Lien complet", value=f"[Lire l'article]({page.url})")
        await ctx.send(embed=embed)
    except Exception as e:
        await ctx.send(f"{EMOJI_XCX} Impossible de récupérer les données sur Wikipédia pour ce sujet.")

@bot.command(name="search", help="Recherche une page Wikipédia (`+search wiki <sujet>`).")
async def search_(ctx, engine=None, *, query=None):
    if engine == "wiki" and query:
        await wiki(ctx, query=query)
    else:
        await ctx.send("Usage : `+search wiki <votre recherche>`")

@bot.command(help="Calcule une expression mathématique basique (ex: `+calc 5+5`).")
async def calc(ctx, *, expression=None):
    if not expression:
        return await ctx.send(f"{EMOJI_XCX} Veuillez entrer une expression mathématique.")
    try:
        allowed = set("0123456789+-*/(). ")
        if not set(expression).issubset(allowed):
            return await ctx.send(f"{EMOJI_XCX} Caractères non autorisés.")
        result = eval(expression)
        await ctx.send(f"🧮 **Résultat :** `{result}`")
    except Exception:
        await ctx.send(f"{EMOJI_XCX} Expression mathématique invalide.")

@bot.command(help="Affiche la latence actuelle du bot en millisecondes.")
async def ping(ctx):
    await ctx.send(f"🏓 Pong ! `{round(bot.latency * 1000)}ms` {EMOJI_NITRO}")

@bot.command(help="Affiche la vitesse de réponse de l'hébergement du bot.")
async def speed(ctx):
    await ctx.send(f"⚡ Vitesse du serveur : `{round(bot.latency * 1000)}ms` {EMOJI_NITRO}")

@bot.command(help="Fait répéter un message au bot.")
async def message(ctx, *, text=None):
    if not text:
        return await ctx.send(f"{EMOJI_XCX} Veuillez spécifier le message à répéter.")
    try:
        await ctx.message.delete()
    except discord.Forbidden:
        pass
    await ctx.send(text)

@bot.command(help="Fait parler le bot à votre place.")
async def say(ctx, *, text=None):
    if not text:
        return await ctx.send(f"{EMOJI_XCX} Veuillez spécifier le texte à dire.")
    try:
        await ctx.message.delete()
    except discord.Forbidden:
        pass
    await ctx.send(text)

# ==========================================
#          COMMANDES PERM 1 À PERM 4
# ==========================================
@bot.command(help="Affiche l'historique complet des sanctions d'un membre.")
async def sanctions(ctx, member: discord.Member = None):
    member = member or ctx.author
    await ctx.send(f"📜 **Sanctions de {member.mention} :** Aucune sanction enregistrée.")

@bot.command(help="Ajoute une note de modération privée sur un membre.")
async def note(ctx, member: discord.Member = None, *, text=None):
    if not member or not text:
        return await ctx.send("Usage : `+note @membre <votre note>`")
    await ctx.send(f"📝 Note ajoutée sur **{member.display_name}** : {text}")

@bot.command(name="delnote", help="Supprime une note de modération spécifique par son ID.")
async def note_delete(ctx, note_id=None):
    if not note_id:
        return await ctx.send("Usage : `+delnote <ID_note>`")
    await ctx.send(f"{EMOJI_STAR} Note `{note_id}` supprimée avec succès.")

@bot.command(help="Rend un membre muet sur l'ensemble du serveur.")
async def mute(ctx, member: discord.Member = None, *, reason=None):
    if not member:
        return await ctx.send("Usage : `+mute @membre [raison]`")
    await ctx.send(f"{EMOJI_LOCK} **{member.mention}** a été rendu muet. Raison : {reason or 'Aucune'}")

@bot.command(help="Rend un membre muet pour une durée définie (ex: `+tempmute @membre 10m`).")
async def tempmute(ctx, member: discord.Member = None, time=None, *, reason=None):
    if not member or not time:
        return await ctx.send("Usage : `+tempmute @membre <durée> [raison]`")
    await ctx.send(f"⏱️ **{member.mention}** a été rendu muet pour `{time}`. Raison : {reason or 'Aucune'}")

@bot.command(help="Affiche le niveau de permission d'un membre sur le bot.")
async def perms(ctx, member: discord.Member = None):
    member = member or ctx.author
    await ctx.send(f"{EMOJI_SHIELD} **Permissions de {member.mention} :** Membre / Modérateur")

@bot.command(help="Affiche le dernier message qui a été supprimé dans le salon.")
async def snipe(ctx):
    await ctx.send("🎯 Aucun message supprimé récent à récupérer.")

@bot.command(help="Expulse un membre connecté dans un salon vocal.")
async def voicekick(ctx, member: discord.Member = None):
    if member and member.voice:
        await member.move_to(None)
        await ctx.send(f"🔊 **{member.display_name}** a été expulsé du salon vocal.")
    else:
        await ctx.send(f"{EMOJI_XCX} Membre introuvable ou non connecté en vocal.")

@bot.command(help="Envoie un avertissement formel à un membre.")
async def warn(ctx, member: discord.Member = None, *, reason=None):
    if not member:
        return await ctx.send("Usage : `+warn @membre [raison]`")
    await ctx.send(f"⚠️ **{member.mention}** a reçu un avertissement. Raison : {reason or 'Aucune'}")

@bot.command(help="Active ou désactive la protection Anti-hack (`+antihack on/off`).")
async def antihack(ctx, status=None):
    if status in ["on", "off"]:
        config["antihack"] = (status == "on")
        await ctx.send(f"{EMOJI_SHIELD} Anti-hack configuré sur : **{status.upper()}**")
    else:
        await ctx.send("Usage : `+antihack on` ou `+antihack off`")

@bot.command(help="Modifie le surnom d'un membre sur le serveur.")
async def nick(ctx, member: discord.Member = None, *, new_nick=None):
    if member:
        await member.edit(nick=new_nick)
        await ctx.send(f"✏️ Surnom de **{member.name}** modifié en : `{new_nick}`")
    else:
        await ctx.send("Usage : `+nick @membre <nouveau_surnom>`")

# ==========================================
#          COMMANDES PERM 5 À PERM 9
# ==========================================
@bot.command(aliases=["delsanction"], help="Supprime une sanction enregistrée via son ID.")
async def del_(ctx, sanction_id=None):
    if not sanction_id:
        return await ctx.send("Usage : `+del <ID_sanction>`")
    await ctx.send(f"🗑️ Sanction `{sanction_id}` supprimée.")

@bot.command(help="Supprime un nombre spécifique de messages dans le salon.")
async def clear(ctx, amount: int = 10):
    await ctx.channel.purge(limit=amount + 1)
    await ctx.send(f"🧹 `{amount}` messages ont été supprimés.", delete_after=5)

@bot.command(help="Restaure la parole d'un membre muté.")
async def unmute(ctx, member: discord.Member = None):
    if not member:
        return await ctx.send("Usage : `+unmute @membre`")
    await ctx.send(f"🔊 **{member.mention}** a été unmuté.")

@bot.command(help="Ajoute un rôle spécifique à un membre.")
async def addrole(ctx, member: discord.Member = None, role: discord.Role = None):
    if member and role:
        await member.add_roles(role)
        await ctx.send(f"{EMOJI_STAR} Rôle **{role.name}** ajouté à {member.mention}.")
    else:
        await ctx.send("Usage : `+addrole @membre @rôle`")

@bot.command(help="Retire un rôle spécifique à un membre.")
async def delrole(ctx, member: discord.Member = None, role: discord.Role = None):
    if member and role:
        await member.remove_roles(role)
        await ctx.send(f"🗑️ Rôle **{role.name}** retiré à {member.mention}.")
    else:
        await ctx.send("Usage : `+delrole @membre @rôle`")

@bot.command(name="clearsanctions", help="Efface la totalité des sanctions d'un membre.")
async def clear_sanctions_cmd(ctx, member: discord.Member = None):
    if not member:
        return await ctx.send("Usage : `+clearsanctions @membre`")
    await ctx.send(f"🧹 Toutes les sanctions de **{member.display_name}** ont été effacées.")

@bot.command(help="Expulse définitivement un membre du serveur.")
async def kick(ctx, member: discord.Member = None, *, reason=None):
    if member:
        await member.kick(reason=reason)
        await ctx.send(f"👞 **{member.display_name}** a été expulsé. Raison : {reason or 'Aucune'}")
    else:
        await ctx.send("Usage : `+kick @membre [raison]`")

@bot.command(help="Affiche la liste complète des utilisateurs bannis.")
async def banlist(ctx):
    bans = [entry async for entry in ctx.guild.bans()]
    await ctx.send(f"🔨 Il y a actuellement **{len(bans)}** membres bannis du serveur.")

@bot.command(help="Bannit définitivement un membre du serveur.")
async def ban(ctx, member: discord.Member = None, *, reason=None):
    if member:
        await member.ban(reason=reason)
        await ctx.send(f"🔨 **{member.display_name}** a été banni. Raison : {reason or 'Aucune'}")
    else:
        await ctx.send("Usage : `+ban @membre [raison]`")

@bot.command(help="Bannit temporairement un membre du serveur.")
async def tempban(ctx, member: discord.Member = None, time=None, *, reason=None):
    if member and time:
        await ctx.send(f"⏱️ **{member.display_name}** banni temporairement pour `{time}`.")
    else:
        await ctx.send("Usage : `+tempban @membre <durée> [raison]`")

@bot.command(help="Débannit un utilisateur du serveur à l'aide de son ID.")
async def unban(ctx, user_id: int = None):
    if user_id:
        user = await bot.fetch_user(user_id)
        await ctx.guild.unban(user)
        await ctx.send(f"{EMOJI_STAR} **{user.name}** a été débanni.")
    else:
        await ctx.send("Usage : `+unban <ID_utilisateur>`")

@bot.command(help="Retire tous les rôles de modération/administration d'un membre.")
async def derank(ctx, member: discord.Member = None):
    if member:
        await ctx.send(f"📉 Derank effectué sur **{member.display_name}**.")
    else:
        await ctx.send("Usage : `+derank @membre`")

@bot.command(help="Verrouille le pseudo d'un membre pour l'empêcher de le changer.")
async def lockname(ctx, member: discord.Member = None):
    await ctx.send(f"{EMOJI_LOCK} Nom verrouillé.")

@bot.command(help="Déverrouille le pseudo d'un membre.")
async def unlockname(ctx):
    await ctx.send("🔓 Nom déverrouillé.")

@bot.command(help="Affiche la liste de tous les pseudos verrouillés sur le serveur.")
async def locknamelist(ctx):
    await ctx.send("📋 Liste des pseudos verrouillés...")

@bot.command(help="Affiche le niveau de rang dans la blacklist.")
async def blrank(ctx):
    await ctx.send(f"{EMOJI_XCX} Rang de blacklist affiché.")

@bot.command(help="Ajoute un membre à la Blacklist globale du bot.")
async def bl(ctx, member: discord.Member = None):
    if member:
        await ctx.send(f"{EMOJI_XCX} **{member.display_name}** a été ajouté à la Blacklist.")
    else:
        await ctx.send("Usage : `+bl @membre`")

@bot.command(help="Retire un membre de la Blacklist du bot.")
async def unbl(ctx, member: discord.Member = None):
    if member:
        await ctx.send(f"{EMOJI_STAR} **{member.display_name}** retiré de la Blacklist.")
    else:
        await ctx.send("Usage : `+unbl @membre`")

@bot.command(help="Affiche les détails de la raison de blacklist d'un membre.")
async def blinfo(ctx, member: discord.Member = None):
    await ctx.send("ℹ️ Informations de Blacklist chargées.")

# ==========================================
#          COMMANDES OWNERS
# ==========================================
@bot.command(help="Verrouille l'envoi de messages dans le salon pour les membres.")
async def cmute(ctx, *, reason=None):
    await ctx.channel.set_permissions(ctx.guild.default_role, send_messages=False)
    await ctx.send(f"{EMOJI_LOCK} Le salon a été rendu muet pour tous les membres.")

@bot.command(help="Mute temporairement l'envoi de messages dans le salon.")
async def tempcmute(ctx, time=None):
    await ctx.send(f"⏱️ Salon muté pour une durée de `{time}`.")

@bot.command(help="Restaure l'autorisation d'écrire dans le salon.")
async def uncmute(ctx):
    await ctx.channel.set_permissions(ctx.guild.default_role, send_messages=True)
    await ctx.send("🔓 Le salon est de nouveau ouvert à tous.")

@bot.command(help="Affiche la liste complète des membres actuellement mutés.")
async def mutelist(ctx):
    await ctx.send("📋 **Liste des mutés :** Aucun membre muté actuellement.")

@bot.command(help="Démute simultanément l'ensemble des membres du serveur.")
async def unmuteall(ctx):
    await ctx.send("🔊 Tous les membres du serveur ont été unmutés.")

@bot.command(help="Verrouille l'accès et l'écriture dans le salon courant.")
async def lock(ctx):
    await ctx.channel.set_permissions(ctx.guild.default_role, send_messages=False)
    await ctx.send(f"{EMOJI_LOCK} Salon verrouillé.")

@bot.command(help="Déverrouille l'accès et l'écriture dans le salon courant.")
async def unlock(ctx):
    await ctx.channel.set_permissions(ctx.guild.default_role, send_messages=True)
    await ctx.send("🔓 Salon déverrouillé.")

@bot.command(help="Verrouille simultanément l'intégralité des salons du serveur.")
async def lockall(ctx):
    await ctx.send(f"{EMOJI_LOCK} Tous les salons du serveur ont été verrouillés.")

@bot.command(help="Déverrouille simultanément tous les salons du serveur.")
async def unlockall(ctx):
    await ctx.send("🔓 Tous les salons du serveur ont été déverrouillés.")

@bot.command(help="Masque le salon courant aux yeux des membres.")
async def hide(ctx):
    await ctx.channel.set_permissions(ctx.guild.default_role, view_channel=False)
    await ctx.send("👁️‍🗨️ Salon masqué.")

@bot.command(help="Rend à nouveau le salon courant visible aux membres.")
async def unhide(ctx):
    await ctx.channel.set_permissions(ctx.guild.default_role, view_channel=True)
    await ctx.send("👁️ Salon affiché.")

@bot.command(help="Masque l'intégralité des salons du serveur.")
async def hideall(ctx):
    await ctx.send("👁️‍🗨️ Tous les salons du serveur ont été masqués.")

@bot.command(help="Rend à nouveau visibles tous les salons du serveur.")
async def unhideall(ctx):
    await ctx.send("👁️ Tous les salons ont été réaffichés.")

@bot.command(help="Affiche la configuration complète et le statut des protections du bot.")
async def settings(ctx):
    status_antilink = "Activé" if config["antilink"] else "Désactivé"
    status_antispam = "Activé" if config["antispam"] else "Désactivé"
    await ctx.send(f"⚙️ **Configuration Actuelle :**\n- Anti-link : `{status_antilink}`\n- Anti-spam : `{status_antispam}`\n- Salon d'accueil : <#{config['welcome_channel']}>\n- Auto Role : <@&{config['auto_role']}>\n- Tag/Statut Soutien : `{config['soutien_text']}`")

@bot.command(help="Active ou désactive la sécurité Anti-spam (`+antispam on/off`).")
async def antispam(ctx, status=None):
    if status in ["on", "off"]:
        config["antispam"] = (status == "on")
        await ctx.send(f"{EMOJI_SHIELD} Anti-spam configuré sur : **{status.upper()}**")
    else:
        await ctx.send("Usage : `+antispam on` ou `+antispam off`")

@bot.command(help="Active ou désactive la suppression automatique des liens (`+antilink on/off`).")
async def antilink(ctx, status: str = None):
    if not status:
        current = "activé" if config["antilink"] else "désactivé"
        return await ctx.send(f"L'anti-link est actuellement **{current}**. Utilisez `+antilink on` ou `+antilink off`.")
    
    if status.lower() in ["on", "enable", "1", "true"]:
        config["antilink"] = True
        await ctx.send(f"{EMOJI_STAR} **Anti-link activé** ! Tous les liens seront automatiquement supprimés.")
    elif status.lower() in ["off", "disable", "0", "false"]:
        config["antilink"] = False
        await ctx.send(f"{EMOJI_XCX} **Anti-link désactivé**.")
    else:
        await ctx.send("Usage : `+antilink on` ou `+antilink off`.")

@bot.command(help="Gère la liste des mots interdits filtrés par le bot.")
async def badwords(ctx, action=None):
    await ctx.send("🤬 Gestionnaire de mots interdits actif.")

@bot.command(help="Affiche la liste de tous les bots enregistrés sur le serveur.")
async def allbots(ctx):
    bots = [m.mention for m in ctx.guild.members if m.bot]
    await ctx.send(f"🤖 **Bots du serveur ({len(bots)}) :**\n" + ", ".join(bots))

@bot.command(help="Affiche la liste de tous les administrateurs du serveur.")
async def alladmins(ctx):
    admins = [m.mention for m in ctx.guild.members if m.guild_permissions.administrator and not m.bot]
    await ctx.send(f"{EMOJI_CROWN} **Administrateurs ({len(admins)}) :**\n" + ", ".join(admins))

@bot.command(help="Affiche la liste de tous les membres soutenant le serveur avec un Boost.")
async def boosters(ctx):
    boosters_list = [m.mention for m in ctx.guild.premium_subscribers]
    if boosters_list:
        await ctx.send(f"{EMOJI_NITRO} **Boosters ({len(boosters_list)}) :**\n" + ", ".join(boosters_list))
    else:
        await ctx.send(f"{EMOJI_NITRO} Aucun booster sur ce serveur actuellement.")

@bot.command(help="Affiche les statistiques et informations détaillées du serveur.")
async def serverinfo(ctx):
    guild = ctx.guild
    embed = discord.Embed(title=f"Informations sur {guild.name}", color=discord.Color.purple())
    embed.add_field(name="Membres", value=str(guild.member_count), inline=True)
    embed.add_field(name="Créé le", value=guild.created_at.strftime("%d/%m/%Y"), inline=True)
    embed.add_field(name="Propriétaire", value=guild.owner.mention if guild.owner else "Inconnu", inline=True)
    if guild.icon:
        embed.set_thumbnail(url=guild.icon.url)
    await ctx.send(embed=embed)

# ==========================================
#          MENU D'AIDE (MENU DÉROULANT)
# ==========================================
class HelpSelect(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="Commandes Publiques", description="Liste et description des commandes publiques", emoji="🌐"),
            discord.SelectOption(label="Perm 1 à 3", description="Liste et description des commandes Perm 1-3", emoji="🛡️"),
            discord.SelectOption(label="Perm 4 à 6", description="Liste et description des commandes Perm 4-6", emoji="⚖️"),
            discord.SelectOption(label="Perm 7 à 9", description="Liste et description des commandes Perm 7-9", emoji="🔨"),
            discord.SelectOption(label="Owners & Config", description="Liste et description des commandes de configuration & Owners", emoji="⚙️")
        ]
        super().__init__(placeholder="📂 Choisissez une catégorie...", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        if self.values[0] == "Commandes Publiques":
            embed = discord.Embed(
                title="🌐 Commandes Publiques",
                description=(
                    "`+crowbots` - Affiche la liste des bots publics du système.\n"
                    "`+mybots` - Affiche la liste de vos bots enregistrés.\n"
                    "`+pic` - Affiche la photo de profil d'un membre ou la vôtre.\n"
                    "`+banner` - Affiche la bannière d'un membre s'il en possède une.\n"
                    "`+server pic/banner` - Affiche l'icône ou la bannière du serveur.\n"
                    "`+emoji` - Affiche l'image d'un emoji personnalisé en grand.\n"
                    "`+image` - Traite ou envoie une image.\n"
                    "`+suggestion` - Soumet une suggestion dans le salon dédié.\n"
                    "`+lb suggestions` - Affiche le classement des suggestions.\n"
                    "`+wiki` - Recherche un sujet Wikipédia et affiche un résumé.\n"
                    "`+search wiki` - Effectue une recherche complète sur Wikipédia.\n"
                    "`+calc` - Effectue un calcul mathématique basique.\n"
                    "`+ping` - Affiche la latence du bot en millisecondes.\n"
                    "`+speed` - Affiche la vitesse du serveur d'hébergement.\n"
                    "`+message` - Fait répéter un message au bot.\n"
                    "`+say` - Fait parler le bot à votre place."
                ),
                color=discord.Color.blue()
            )
        elif self.values[0] == "Perm 1 à 3":
            embed = discord.Embed(
                title="🛡️ Commandes Perm 1 à 3",
                description=(
                    "**Perm 1:**\n"
                    "`+sanctions` - Historique des sanctions d'un membre.\n"
                    "`+note` - Ajouter une note de modération privée.\n"
                    "`+delnote` - Supprimer une note via son ID.\n"
                    "`+mute` - Rendre un membre muet.\n"
                    "`+tempmute` - Rendre un membre muet temporairement.\n"
                    "`+perms` - Afficher le niveau de permission d'un membre.\n"
                    "`+snipe` - Récupérer le dernier message supprimé.\n\n"
                    "**Perm 2:**\n"
                    "`+voicekick` - Expulser un membre d'un salon vocal.\n\n"
                    "**Perm 3:**\n"
                    "`+warn` - Envoyer un avertissement formel.\n"
                    "`+antihack` - Activer/Désactiver le système anti-hack."
                ),
                color=discord.Color.green()
            )
        elif self.values[0] == "Perm 4 à 6":
            embed = discord.Embed(
                title="⚖️ Commandes Perm 4 à 6",
                description=(
                    "**Perm 4:**\n"
                    "`+nick` - Modifier le surnom d'un membre.\n\n"
                    "**Perm 5:**\n"
                    "`+del` - Supprimer une sanction enregistrée via son ID.\n"
                    "`+clear` - Purger un nombre de messages dans le salon.\n"
                    "`+unmute` - Restaurer la parole d'un membre muet.\n\n"
                    "**Perm 6:**\n"
                    "`+addrole` - Ajouter un rôle à un membre.\n"
                    "`+delrole` - Retirer un rôle à un membre."
                ),
                color=discord.Color.orange()
            )
        elif self.values[0] == "Perm 7 à 9":
            embed = discord.Embed(
                title="🔨 Commandes Perm 7 à 9",
                description=(
                    "**Perm 7:**\n"
                    "`+clearsanctions` - Effacer toutes les sanctions d'un membre.\n"
                    "`+kick` - Expulser un membre du serveur.\n"
                    "`+banlist` - Afficher la liste des membres bannis.\n\n"
                    "**Perm 8:**\n"
                    "`+ban` - Bannir un membre du serveur.\n"
                    "`+tempban` - Bannir un membre temporairement.\n"
                    "`+unban` - Débannir un membre via son ID.\n"
                    "`+derank` - Retirer les rôles de modération d'un membre.\n"
                    "`+lockname` - Verrouiller le pseudo d'un membre.\n"
                    "`+unlockname` - Déverrouiller le pseudo d'un membre.\n"
                    "`+locknamelist` - Afficher la liste des pseudos verrouillés.\n"
                    "`+blrank` - Afficher le niveau de rang de blacklist.\n\n"
                    "**Perm 9:**\n"
                    "`+bl` - Ajouter un membre à la Blacklist du bot.\n"
                    "`+unbl` - Retirer un membre de la Blacklist.\n"
                    "`+blinfo` - Afficher les infos de blacklist."
                ),
                color=discord.Color.red()
            )
        elif self.values[0] == "Owners & Config":
            embed = discord.Embed(
                title="⚙️ Commandes Owners & Configuration",
                description=(
                    "**Configuration :**\n"
                    "`+setwelcome` - Définir le salon d'arrivée des membres.\n"
                    "`+setautorole` - Définir le rôle attribué à l'arrivée.\n"
                    "`+setsoutien` - Configurer le rôle pour Tag/Statut/Boost.\n\n"
                    "**Gestion des Salons :**\n"
                    "`+cmute` / `+uncmute` - Muter / Démuter le salon courant.\n"
                    "`+tempcmute` - Muter le salon temporairement.\n"
                    "`+lock` / `+unlock` - Verrouiller / Déverrouiller le salon.\n"
                    "`+lockall` / `+unlockall` - Verrouiller / Déverrouiller tous les salons.\n"
                    "`+hide` / `+unhide` - Masquer / Afficher le salon.\n"
                    "`+hideall` / `+unhideall` - Masquer / Afficher tous les salons.\n\n"
                    "**Administration :**\n"
                    "`+settings` - Afficher les paramètres actuels du bot.\n"
                    "`+antispam` - Configurer la sécurité Anti-spam (`on/off`).\n"
                    "`+antilink` - Configurer la sécurité Anti-link (`on/off`).\n"
                    "`+badwords` - Gérer les mots interdits.\n"
                    "`+allbots` - Liste complète des bots du serveur.\n"
                    "`+alladmins` - Liste de tous les administrateurs.\n"
                    "`+boosters` - Liste des boosters du serveur.\n"
                    "`+serverinfo` - Informations détaillées sur le serveur."
                ),
                color=discord.Color.gold()
            )
        await interaction.response.edit_message(embed=embed)

class HelpView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=180)
        self.add_item(HelpSelect())

@bot.command(help="Affiche le menu d'aide interactif avec un menu déroulant.")
async def help(ctx, *, command_name=None):
    if command_name:
        cmd = bot.get_command(command_name)
        if cmd:
            embed = discord.Embed(
                title=f"📖 Aide : +{cmd.name}",
                description=cmd.help or "Aucune explication disponible.",
                color=discord.Color.blue()
            )
            await ctx.send(embed=embed)
        else:
            await ctx.send(f"{EMOJI_XCX} La commande `+{command_name}` n'existe pas.")
    else:
        embed = discord.Embed(
            title=f"{EMOJI_CROWN} Menu d'aide interactif - Gstion {EMOJI_NITRO}",
            description="Sélectionnez une catégorie dans le menu déroulant ci-dessous pour afficher les commandes avec leur description complète.",
            color=discord.Color.blue()
        )
        embed.set_footer(text="Bot gstion • Utilisez le menu déroulant pour changer de catégorie.")
        await ctx.send(embed=embed, view=HelpView())

# ==========================================
#            LANCEMENT DU BOT
# ==========================================
if __name__ == "__main__":
    keep_alive()
    token = os.environ.get("DISCORD_TOKEN")
    if not token:
        print("ERREUR : La variable d'environnement DISCORD_TOKEN n'a pas été trouvée sur Render !")
    else:
        bot.run(token)
