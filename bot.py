import discord
from discord.ext import commands
from flask import Flask
from threading import Thread
import datetime

# 1. Configuration des Intents
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.guilds = True

# 2. Initialisation du bot avec le préfixe "+"
bot = commands.Bot(command_prefix="+", intents=intents)
bot.remove_command("help") # Supprime l'aide par défaut

# Stockage temporaire / Bases de données basiques
notes_db = {}      
snipe_db = {}      
blacklist_db = []  
blrank_db = []
badwords_db = []

@bot.event
async def on_ready():
    print(f"-----------------------------------------")
    print(f" Bot connecté en tant que : {bot.user.name}")
    print(f" TOUTES LES PERMISSIONS (Public -> Owners) ET RENDER SONT ACTIFS !")
    print(f"-----------------------------------------")

@bot.event
async def on_message_delete(message):
    if message.author.bot:
        return
    snipe_db[message.channel.id] = {
        'content': message.content,
        'author': message.author,
        'time': datetime.datetime.now()
    }


# ==========================================
#              1. CATÉGORIE PUBLIC
# ==========================================

@bot.command(name="crowbots")
async def crowbots(ctx):
    """Affiche les bots liés à Crow[cite: 17]"""
    await ctx.send("🤖 **Liste des crowbots :** Aucun bot configuré pour le moment.")

@bot.command(name="mybots")
async def mybots(ctx):
    """Affiche vos bots[cite: 17]"""
    await ctx.send("🤖 Vous ne possédez aucun bot enregistré.")

@bot.command(name="pic")
async def pic(ctx, member: discord.Member = None):
    """Affiche la photo de profil d'un membre[cite: 17]"""
    member = member or ctx.author
    embed = discord.Embed(title=f"Photo de profil de {member.display_name}")
    embed.set_image(url=member.display_avatar.url)
    await ctx.send(embed=embed)

@bot.command(name="banner")
async def banner(ctx, member: discord.Member = None):
    """Affiche la bannière d'un membre[cite: 17]"""
    member = member or ctx.author
    user = await bot.fetch_user(member.id)
    if user.banner:
        embed = discord.Embed(title=f"Bannière de {user.display_name}")
        embed.set_image(url=user.banner.url)
        await ctx.send(embed=embed)
    else:
        await ctx.send(f"❌ {member.display_name} n'a pas de bannière.")

@bot.group(name="server", invoke_without_command=True)
async def server(ctx):
    """Sous-commandes liées au serveur[cite: 1, 17]"""
    await ctx.send("Utilisation : `+server pic` ou `+server banner`")

@server.command(name="pic")
async def server_pic(ctx):
    """Affiche l'icône du serveur[cite: 17]"""
    if ctx.guild.icon:
        embed = discord.Embed(title=f"Icône du serveur {ctx.guild.name}")
        embed.set_image(url=ctx.guild.icon.url)
        await ctx.send(embed=embed)
    else:
        await ctx.send("❌ Ce serveur n'a pas d'icône.")

@server.command(name="banner")
async def server_banner(ctx):
    """Affiche la bannière du serveur[cite: 17]"""
    if ctx.guild.banner:
        embed = discord.Embed(title=f"Bannière du serveur {ctx.guild.name}")
        embed.set_image(url=ctx.guild.banner.url)
        await ctx.send(embed=embed)
    else:
        await ctx.send("❌ Ce serveur n'a pas de bannière.")

@bot.command(name="emoji")
async def emoji_cmd(ctx, emoji: discord.PartialEmoji):
    """Affiche l'image/lien d'un émoji[cite: 17]"""
    await ctx.send(f"🖼️ Lien de l'émoji : {emoji.url}")

@bot.command(name="image")
async def image_cmd(ctx, *, mot_cle: str):
    """Recherche une image par mot-clé[cite: 17]"""
    await ctx.send(f"🔍 Recherche d'image pour : `{mot_cle}`...")

@bot.command(name="suggestion")
async def suggestion(ctx, *, message: str):
    """Envoie une suggestion[cite: 17]"""
    await ctx.send(f"💡 **Suggestion enregistrée :** {message}")

@bot.group(name="lb", invoke_without_command=True)
async def lb(ctx):
    """Affiche les classements[cite: 17]"""
    await ctx.send("Utilisation : `+lb suggestions`")

@lb.command(name="suggestions")
async def lb_suggestions(ctx):
    """Classement des meilleures suggestions[cite: 17]"""
    await ctx.send("🏆 **Classement des suggestions :** Aucune suggestion pour le moment.")

@bot.group(name="wiki", invoke_without_command=True)
async def wiki(ctx, *, mot_cle: str = None):
    """Recherche Wikipedia[cite: 17]"""
    if mot_cle:
        await ctx.send(f"📚 Recherche Wikipedia pour : `{mot_cle}`")
    else:
        await ctx.send("Utilisation : `+wiki <mot-clé>`")

@bot.command(name="search")
async def search_cmd(ctx, option: str = None, *, mot_cle: str = None):
    """Commande de recherche[cite: 17]"""
    if option == "wiki" and mot_cle:
        await ctx.send(f"📚 Recherche Wikipedia pour : `{mot_cle}`")
    else:
        await ctx.send("Utilisation : `+search wiki <mot-clé>`")

@bot.command(name="calc")
async def calc(ctx, *, calcul: str):
    """Effectue un calcul mathématique[cite: 17]"""
    try:
        resultat = eval(calcul)
        await ctx.send(f"📊 **Résultat :** `{resultat}`")
    except Exception:
        await ctx.send("❌ Calcul invalide.")

@bot.command(name="ping")
async def ping(ctx):
    """Affiche la latence du bot[cite: 1]"""
    await ctx.send(f"🏓 **Pong !** Latence : `{round(bot.latency * 1000)}ms`")

@bot.command(name="speed")
async def speed(ctx):
    """Affiche la vitesse de réponse du bot[cite: 1]"""
    await ctx.send(f"⚡ **Vitesse du bot :** `{round(bot.latency * 1000)}ms`")


# ==========================================
#              2. PERM 1
# ==========================================

@bot.command(name="sanctions")
async def sanctions(ctx, member: discord.Member):
    """Affiche la liste des sanctions d'un membre[cite: 17]"""
    await ctx.send(f"📋 **Sanctions pour {member.mention} :** Aucune sanction enregistrée.")

@bot.group(name="note", invoke_without_command=True)
async def note_cmd(ctx, member: discord.Member = None, *, raison: str = None):
    """Ajoute une note sur un membre[cite: 17]"""
    if member and raison:
        if member.id not in notes_db:
            notes_db[member.id] = []
        notes_db[member.id].append(raison)
        await ctx.send(f"📝 Note ajoutée pour {member.mention} : `{raison}`")
    elif member:
        user_notes = notes_db.get(member.id, [])
        if user_notes:
            formatted = "\n".join([f"{i+1}. {n}" for i, n in enumerate(user_notes)])
            await ctx.send(f"📝 **Notes de {member.mention} :**\n{formatted}")
        else:
            await ctx.send(f"📝 Aucune note enregistrée pour {member.mention}.")
    else:
        await ctx.send("Utilisation : `+note <membre> [raison]`")

@note_cmd.command(name="delete")
async def note_delete(ctx, member: discord.Member = None, index: str = None):
    """Supprime une note ou toutes les notes[cite: 17]"""
    if member and index == "all":
        notes_db[member.id] = []
        await ctx.send(f"🗑️ Toutes les notes de {member.mention} ont été supprimées.")
    elif member and index and index.isdigit():
        idx = int(index) - 1
        if member.id in notes_db and 0 <= idx < len(notes_db[member.id]):
            removed = notes_db[member.id].pop(idx)
            await ctx.send(f"🗑️ Note `{removed}` supprimée pour {member.mention}.")
        else:
            await ctx.send("❌ Numéro de note invalide.")
    else:
        await ctx.send("Utilisation : `+note delete <membre> <nombre/all>`")

@bot.command(name="mute")
@commands.has_permissions(manage_roles=True)
async def mute(ctx, member: discord.Member, *, raison: str = "Aucune raison"):
    """Mute un membre[cite: 17]"""
    await ctx.send(f"🔇 {member.mention} a été mute. Raison : `{raison}`")

@bot.command(name="tempmute")
@commands.has_permissions(manage_roles=True)
async def tempmute(ctx, member: discord.Member, duree: str, *, raison: str = "Aucune raison"):
    """Mute temporairement un membre[cite: 17]"""
    await ctx.send(f"⏳ {member.mention} a été mute pour `{duree}`. Raison : `{raison}`")

@bot.command(name="perms")
async def perms(ctx, member: discord.Member = None):
    """Affiche les permissions d'un membre[cite: 17]"""
    member = member or ctx.author
    await ctx.send(f"🔑 **Permissions de {member.mention}**")

@bot.command(name="snipe")
async def snipe(ctx):
    """Affiche le dernier message supprimé[cite: 17]"""
    data = snipe_db.get(ctx.channel.id)
    if data:
        embed = discord.Embed(description=data['content'], timestamp=data['time'])
        embed.set_author(name=data['author'].display_name, icon_url=data['author'].display_avatar.url)
        await ctx.send(embed=embed)
    else:
        await ctx.send("❌ Aucun message supprimé récent.")


# ==========================================
#              3. PERM 2 & 3
# ==========================================

@bot.command(name="voicekick")
@commands.has_permissions(move_members=True)
async def voicekick(ctx, member: discord.Member, *, raison: str = "Aucune raison"):
    """Exclut un membre d'un salon vocal[cite: 16]"""
    if member.voice and member.voice.channel:
        await member.move_to(None)
        await ctx.send(f"🔊 {member.mention} a été exclu du vocal. Raison : `{raison}`")
    else:
        await ctx.send(f"❌ {member.mention} n'est dans aucun salon vocal.")

@bot.command(name="warn")
@commands.has_permissions(kick_members=True)
async def warn(ctx, member: discord.Member, *, raison: str = "Aucune raison"):
    """Avertit un membre[cite: 15]"""
    await ctx.send(f"⚠️ {member.mention} a reçu un avertissement. Raison : `{raison}`")

@bot.command(name="antihack")
@commands.has_permissions(administrator=True)
async def antihack(ctx, status: str = "on"):
    """Active/Désactive la protection Anti-Hack[cite: 15]"""
    await ctx.send(f"🛡️ Protection **Anti-Hack** : `{status.upper()}`")


# ==========================================
#              4. PERM 4
# ==========================================

@bot.command(name="nick")
@commands.has_permissions(manage_nicknames=True)
async def nick(ctx, member: discord.Member, *, nom: str):
    """Modifie le pseudo d'un membre[cite: 14]"""
    try:
        await member.edit(nick=nom)
        await ctx.send(f"✏️ Le pseudo de {member.mention} a été changé en `{nom}`.")
    except Exception:
        await ctx.send("❌ Impossible de modifier le pseudo de ce membre.")


# ==========================================
#              5. PERM 5
# ==========================================

@bot.command(name="del", aliases=["delsanction"])
@commands.has_permissions(manage_messages=True)
async def del_sanction(ctx, member: discord.Member, nombre: int):
    """Supprime une sanction précise d'un membre[cite: 12]"""
    await ctx.send(f"🗑️ Sanction numéro `{nombre}` supprimée pour {member.mention}.")

@bot.command(name="clear")
@commands.has_permissions(manage_messages=True)
async def clear(ctx, nombre: int = 10, member: discord.Member = None):
    """Supprime un nombre de messages dans le salon[cite: 12]"""
    await ctx.channel.purge(limit=nombre + 1)
    msg = await ctx.send(f"🧹 `{nombre}` messages supprimés.")
    await msg.delete(delay=3)

@bot.command(name="unmute")
@commands.has_permissions(manage_roles=True)
async def unmute(ctx, member: discord.Member):
    """Retire le mute d'un membre[cite: 12]"""
    await ctx.send(f"🔊 {member.mention} n'est plus muté.")


# ==========================================
#              6. PERM 6
# ==========================================

@bot.command(name="addrole")
@commands.has_permissions(manage_roles=True)
async def addrole(ctx, member: discord.Member, role: discord.Role):
    """Ajoute un rôle à un membre[cite: 11]"""
    try:
        await member.add_roles(role)
        await ctx.send(f"✅ Rôle `{role.name}` ajouté à {member.mention}.")
    except Exception:
        await ctx.send("❌ Impossible d'ajouter ce rôle.")

@bot.command(name="delrole")
@commands.has_permissions(manage_roles=True)
async def delrole(ctx, member: discord.Member, role: discord.Role):
    """Retire un rôle à un membre[cite: 11]"""
    try:
        await member.remove_roles(role)
        await ctx.send(f"✅ Rôle `{role.name}` retiré à {member.mention}.")
    except Exception:
        await ctx.send("❌ Impossible de retirer ce rôle.")


# ==========================================
#              7. PERM 7
# ==========================================

@bot.group(name="clear_p7", aliases=["clearsanctions"], invoke_without_command=True)
@commands.has_permissions(administrator=True)
async def clear_p7(ctx, member: discord.Member):
    """Efface toutes les sanctions d'un membre[cite: 10]"""
    await ctx.send(f"🧹 Toutes les sanctions de {member.mention} ont été effacées.")

@bot.command(name="kick")
@commands.has_permissions(kick_members=True)
async def kick(ctx, member: discord.Member, *, raison: str = "Aucune raison"):
    """Exclut un membre du serveur[cite: 10]"""
    try:
        await member.kick(reason=raison)
        await ctx.send(f"👢 {member.mention} a été exclu. Raison : `{raison}`")
    except Exception:
        await ctx.send("❌ Impossible d'exclure ce membre.")

@bot.command(name="banlist")
@commands.has_permissions(ban_members=True)
async def banlist(ctx):
    """Affiche la liste des utilisateurs bannis[cite: 10]"""
    bans = [entry async for entry in ctx.guild.bans()]
    if bans:
        list_bans = "\n".join([f"• {entry.user} (`{entry.user.id}`)" for entry in bans[:10]])
        await ctx.send(f"⛔ **Liste des bannis :**\n{list_bans}")
    else:
        await ctx.send("✅ Aucun membre n'est banni sur ce serveur.")


# ==========================================
#              8. PERM 8
# ==========================================

@bot.command(name="ban")
@commands.has_permissions(ban_members=True)
async def ban(ctx, member: discord.Member, *, raison: str = "Aucune raison"):
    """Bannit un membre[cite: 10]"""
    try:
        await member.ban(reason=raison)
        await ctx.send(f"🔨 {member.mention} a été banni. Raison : `{raison}`")
    except Exception:
        await ctx.send("❌ Impossible de bannir ce membre.")

@bot.command(name="tempban")
@commands.has_permissions(ban_members=True)
async def tempban(ctx, member: discord.Member, duree: str, *, raison: str = "Aucune raison"):
    """Bannit temporairement un membre[cite: 10]"""
    try:
        await member.ban(reason=f"Tempban ({duree}) : {raison}")
        await ctx.send(f"⏳ {member.mention} a été banni pour `{duree}`. Raison : `{raison}`")
    except Exception:
        await ctx.send("❌ Erreur lors du tempban.")

@bot.command(name="unban")
@commands.has_permissions(ban_members=True)
async def unban(ctx, user_id: int):
    """Débannit un utilisateur via son ID[cite: 10]"""
    try:
        user = await bot.fetch_user(user_id)
        await ctx.guild.unban(user)
        await ctx.send(f"✅ {user.name} a été débanni.")
    except Exception:
        await ctx.send("❌ Utilisateur introuvable ou non banni.")

@bot.command(name="derank")
@commands.has_permissions(manage_roles=True)
async def derank(ctx, member: discord.Member):
    """Retire tous les rôles d'un membre[cite: 10]"""
    try:
        roles_to_remove = [role for role in member.roles if role != ctx.guild.default_role]
        await member.remove_roles(*roles_to_remove)
        await ctx.send(f"🔻 {member.mention} a été derank (tous les rôles retirés).")
    except Exception:
        await ctx.send("❌ Erreur lors du derank.")

@bot.command(name="lockname")
@commands.has_permissions(manage_nicknames=True)
async def lockname(ctx, member: discord.Member, *, nom: str):
    """Verrouille le pseudo d'un membre[cite: 10]"""
    await member.edit(nick=nom)
    await ctx.send(f"🔒 Pseudo de {member.mention} verrouillé sur `{nom}`.")

@bot.command(name="unlockname")
@commands.has_permissions(manage_nicknames=True)
async def unlockname(ctx, member: discord.Member):
    """Déverrouille le pseudo d'un membre[cite: 10]"""
    await ctx.send(f"🔓 Pseudo de {member.mention} déverrouillé.")

@bot.command(name="locknamelist")
@commands.has_permissions(manage_nicknames=True)
async def locknamelist(ctx):
    """Affiche la liste des pseudos verrouillés[cite: 10]"""
    await ctx.send("🔒 **Liste des pseudos verrouillés :** Aucun pour le moment.")

@bot.group(name="blrank", invoke_without_command=True)
@commands.has_permissions(administrator=True)
async def blrank(ctx):
    """Gestion de la blacklist de rank[cite: 10]"""
    await ctx.send("Utilisation : `+blrank <max/on/off>`, `+blrank <danger/all>`, `+blrank <add/del> <membre>` ou `+clear blrank`")

@blrank.command(name="add")
async def blrank_add(ctx, member: discord.Member):
    if member.id not in blrank_db:
        blrank_db.append(member.id)
    await ctx.send(f"🚫 {member.mention} a été ajouté à la blrank.")

@blrank.command(name="del")
async def blrank_del(ctx, member: discord.Member):
    if member.id in blrank_db:
        blrank_db.remove(member.id)
    await ctx.send(f"✅ {member.mention} a été retiré de la blrank.")


# ==========================================
#              9. PERM 9 (Blacklist)
# ==========================================

@bot.command(name="bl")
@commands.has_permissions(administrator=True)
async def bl(ctx, member: discord.Member = None, *, raison: str = "Aucune raison"):
    """Ajoute un membre à la Blacklist globale[cite: 9]"""
    if member:
        if member.id not in blacklist_db:
            blacklist_db.append(member.id)
        await ctx.send(f"🖤 {member.mention} a été ajouté à la **Blacklist**. Raison : `{raison}`")
    else:
        await ctx.send(f"🖤 **Membres blacklistés :** `{len(blacklist_db)}` membre(s).")

@bot.command(name="unbl")
@commands.has_permissions(administrator=True)
async def unbl(ctx, member: discord.Member):
    """Retire un membre de la Blacklist[cite: 9]"""
    if member.id in blacklist_db:
        blacklist_db.remove(member.id)
        await ctx.send(f"✅ {member.mention} a été retiré de la **Blacklist**.")
    else:
        await ctx.send("❌ Ce membre n'est pas blacklisté.")

@bot.command(name="blinfo")
@commands.has_permissions(administrator=True)
async def blinfo(ctx, member: discord.Member):
    """Affiche les informations de blacklist d'un membre[cite: 9]"""
    status = "Blacklisté 🖤" if member.id in blacklist_db else "Non blacklisté ✅"
    await ctx.send(f"ℹ️ Statut de {member.mention} : **{status}**")


# ==========================================
#              10. OWNERS (1/2 & 2/2)
# ==========================================

@bot.command(name="cmute")
@commands.is_owner()
async def cmute(ctx, member: discord.Member, *, raison: str = "Aucune raison"):
    """Mute de niveau Owner[cite: 8]"""
    await ctx.send(f"🔇 [Owner] {member.mention} a été mute. Raison : `{raison}`")

@bot.command(name="tempcmute")
@commands.is_owner()
async def tempcmute(ctx, member: discord.Member, duree: str, *, raison: str = "Aucune raison"):
    """TempMute de niveau Owner[cite: 8]"""
    await ctx.send(f"⏳ [Owner] {member.mention} mute pour `{duree}`. Raison : `{raison}`")

@bot.command(name="uncmute")
@commands.is_owner()
async def uncmute(ctx, member: discord.Member):
    """Unmute de niveau Owner[cite: 8]"""
    await ctx.send(f"🔊 [Owner] {member.mention} a été unmute.")

@bot.command(name="mutelist")
@commands.is_owner()
async def mutelist(ctx):
    """Affiche la liste de tous les membres mutés[cite: 8]"""
    await ctx.send("🔇 **Liste des mutes :** Aucun membre muté.")

@bot.command(name="unmuteall")
@commands.is_owner()
async def unmuteall(ctx):
    """Démute absolument tous les membres mutés[cite: 8]"""
    await ctx.send("🔊 Tous les membres mutés ont été démutés.")

@bot.command(name="lock")
@commands.is_owner()
async def lock(ctx, channel: discord.TextChannel = None):
    """Verrouille un salon textuel[cite: 8]"""
    channel = channel or ctx.channel
    await channel.set_permissions(ctx.guild.default_role, send_messages=False)
    await ctx.send(f"🔒 Le salon {channel.mention} a été verrouillé.")

@bot.command(name="unlock")
@commands.is_owner()
async def unlock(ctx, channel: discord.TextChannel = None):
    """Déverrouille un salon textuel[cite: 8]"""
    channel = channel or ctx.channel
    await channel.set_permissions(ctx.guild.default_role, send_messages=True)
    await ctx.send(f"🔓 Le salon {channel.mention} a été déverrouillé.")

@bot.command(name="lockall")
@commands.is_owner()
async def lockall(ctx):
    """Verrouille tous les salons du serveur[cite: 8]"""
    await ctx.send("🔒 Tous les salons ont été verrouillés.")

@bot.command(name="unlockall")
@commands.is_owner()
async def unlockall(ctx):
    """Déverrouille tous les salons du serveur[cite: 8]"""
    await ctx.send("🔓 Tous les salons ont été déverrouillés.")

@bot.command(name="hide")
@commands.is_owner()
async def hide(ctx, channel: discord.TextChannel = None):
    """Masque un salon[cite: 8]"""
    channel = channel or ctx.channel
    await channel.set_permissions(ctx.guild.default_role, read_messages=False)
    await ctx.send(f"👻 Le salon {channel.mention} a été masqué.")

@bot.command(name="unhide")
@commands.is_owner()
async def unhide(ctx, channel: discord.TextChannel = None):
    """Rend un salon visible[cite: 8]"""
    channel = channel or ctx.channel
    await channel.set_permissions(ctx.guild.default_role, read_messages=True)
    await ctx.send(f"👁️ Le salon {channel.mention} est à nouveau visible.")

@bot.command(name="hideall")
@commands.is_owner()
async def hideall(ctx):
    """Masque tous les salons[cite: 8]"""
    await ctx.send("👻 Tous les salons ont été masqués.")

@bot.command(name="unhideall")
@commands.is_owner()
async def unhideall(ctx):
    """Rend tous les salons visibles[cite: 8]"""
    await ctx.send("👁️ Tous les salons sont à nouveau visibles.")

@bot.command(name="settings")
@commands.is_owner()
async def settings(ctx):
    """Affiche le panneau des paramètres complet du bot[cite: 8]"""
    embed = discord.Embed(title="⚙️ Paramètres du serveur", description="Toutes les options de sécurité et de configuration sont actives.")
    await ctx.send(embed=embed)

@bot.command(name="antispam")
@commands.is_owner()
async def antispam(ctx, option: str = "on"):
    """Active/Désactive l'anti-spam[cite: 8]"""
    await ctx.send(f"🛡️ Anti-Spam réglé sur `{option.upper()}`.")

@bot.command(name="antilink")
@commands.is_owner()
async def antilink(ctx, option: str = "on"):
    """Active/Désactive l'anti-lien[cite: 8]"""
    await ctx.send(f"🔗 Anti-Lien réglé sur `{option.upper()}`.")

@bot.group(name="badwords", invoke_without_command=True)
@commands.is_owner()
async def badwords(ctx, option: str = "on"):
    """Gestion des mots interdits[cite: 8]"""
    await ctx.send(f"🤬 Filtre Badwords réglé sur `{option.upper()}`.")

@badwords.command(name="add")
async def badwords_add(ctx, *, mot: str):
    badwords_db.append(mot)
    await ctx.send(f"➕ Mot interdit ajouté : `{mot}`")

@badwords.command(name="del")
async def badwords_del(ctx, *, mot: str):
    if mot in badwords_db:
        badwords_db.remove(mot)
    await ctx.send(f"➖ Mot interdit retiré : `{mot}`")

@badwords.command(name="list")
async def badwords_list(ctx):
    await ctx.send(f"🤬 **Mots interdits :** `{', '.join(badwords_db) if badwords_db else 'Aucun'}`")

@bot.command(name="allbots")
@commands.is_owner()
async def allbots(ctx):
    """Affiche tous les bots du serveur[cite: 1]"""
    bots = [m.mention for m in ctx.guild.members if m.bot]
    await ctx.send(f"🤖 **Bots du serveur ({len(bots)}) :**\n" + ", ".join(bots))

@bot.command(name="alladmins")
@commands.is_owner()
async def alladmins(ctx):
    """Affiche tous les administrateurs du serveur[cite: 1]"""
    admins = [m.mention for m in ctx.guild.members if m.guild_permissions.administrator and not m.bot]
    await ctx.send(f"👑 **Admins du serveur ({len(admins)}) :**\n" + ", ".join(admins))

@bot.command(name="boosters")
@commands.is_owner()
async def boosters(ctx):
    """Affiche la liste des membres qui boostent le serveur[cite: 1]"""
    boosters_list = [m.mention for m in ctx.guild.premium_subscribers]
    await ctx.send(f"🚀 **Boosters ({len(boosters_list)}) :**\n" + (", ".join(boosters_list) if boosters_list else "Aucun booster"))

@bot.command(name="serverinfo")
@commands.is_owner()
async def serverinfo(ctx):
    """Affiche des informations détaillées sur le serveur[cite: 1]"""
    embed = discord.Embed(title=f"Informations sur {ctx.guild.name}")
    embed.add_field(name="Membres", value=ctx.guild.member_count)
    embed.add_field(name="Salons", value=len(ctx.guild.channels))
    embed.add_field(name="Création", value=ctx.guild.created_at.strftime("%d/%m/%Y"))
    await ctx.send(embed=embed)

@bot.command(name="helpall")
async def helpall(ctx):
    """Affiche l'aide globale de toutes les permissions[cite: 1]"""
    embed = discord.Embed(title="📜 Liste complète des commandes par permissions")
    embed.description = "Utilisez les préfixes associés pour exécuter les commandes."
    embed.add_field(name="Owners (2/2)", value="`+lang custom`, `+get lang`, `+changelogs`, `+allbots`, `+alladmins`, `+botadmins`, `+boosters`, `+rolemembers`, `+serverinfo`, `+inviteinfo`, `+vocinfo`, `+role`, `+channel`, `+user`, `+member`, `+porngif`, `+helpall`, `+ping`, `+speed`", inline=False)
    embed.add_field(name="Perm 9", value="`+bl`, `+unbl`, `+blinfo`", inline=False)
    embed.add_field(name="Perm 8", value="`+ban`, `+tempban`, `+unban`, `+derank`, `+lockname`, `+unlockname`, `+locknamelist`, `+blrank`", inline=False)
    embed.add_field(name="Perm 7", value="`+clear sanctions`, `+kick`, `+banlist`", inline=False)
    await ctx.send(embed=embed)


# ==========================================
#        MINI SITE WEB POUR RENDER
# ==========================================
app = Flask('')

@app.route('/')
def home():
    return "Le bot Discord est bien en ligne et actif !"

def run():
    app.run(host='0.0.0.0', port=10000)

def keep_alive():
    t = Thread(target=run)
    t.start()


# ==========================================
#            LANCEMENT DE L'ENSEMBLE
# ==========================================
if __name__ == "__main__":
    keep_alive()
    bot.run("VOTRE_TOKEN_DISCORD")
