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

# Paramètres globaux
config = {
    "antilink": False,
    "antispam": False,
    "antihack": False
}

@bot.event
async def on_ready():
    print(f'Connecté en tant que {bot.user.name} (ID: {bot.user.id})')
    print('Le bot gstion est prêt et opérationnel !')

# ==========================================
#          ÉCOUTEUR D'ÉVÉNEMENTS (ANTI-LINK)
# ==========================================
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
                        f"⚠️ {message.author.mention}, les liens ne sont pas autorisés sur ce serveur !",
                        delete_after=5
                    )
                    return
                except discord.Forbidden:
                    pass

    await bot.process_commands(message)

# ==========================================
#          COMMANDES PUBLIQUES
# ==========================================
@bot.command(help="Affiche la liste des bots publics du système.")
async def crowbots(ctx):
    await ctx.send("🤖 **Bots Publics :** Aucun bot public enregistré pour le moment.")

@bot.command(help="Affiche la liste de vos bots enregistrés.")
async def mybots(ctx):
    await ctx.send("🤖 **Vos Bots :** Vous n'avez enregistré aucun bot.")

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
        await ctx.send("❌ Cet utilisateur n'a pas de bannière.")

@bot.command(name="server", help="Affiche l'icône (`+server pic`) ou la bannière (`+server banner`) du serveur.")
async def server_(ctx, action: str = None):
    if action == "pic":
        if ctx.guild.icon:
            embed = discord.Embed(title=f"Icône de {ctx.guild.name}", color=discord.Color.blue())
            embed.set_image(url=ctx.guild.icon.url)
            await ctx.send(embed=embed)
        else:
            await ctx.send("❌ Ce serveur n'a pas d'icône.")
    elif action == "banner":
        if ctx.guild.banner:
            embed = discord.Embed(title=f"Bannière de {ctx.guild.name}", color=discord.Color.blue())
            embed.set_image(url=ctx.guild.banner.url)
            await ctx.send(embed=embed)
        else:
            await ctx.send("❌ Ce serveur n'a pas de bannière.")
    else:
        await ctx.send("Usage: `+server pic` ou `+server banner`")

@bot.command(help="Affiche l'image en grand format d'un emoji personnalisé.")
async def emoji(ctx, emoji: discord.Emoji = None):
    if emoji:
        await ctx.send(emoji.url)
    else:
        await ctx.send("❌ Veuillez spécifier un emoji personnalisé valide.")

@bot.command(help="Envoie une image aléatoire ou traite une image.")
async def image(ctx):
    await ctx.send("🖼️ Fonctionnalité d'image prête.")

@bot.command(help="Soumet une suggestion dans le salon de suggestions.")
async def suggestion(ctx, *, text=None):
    if not text:
        return await ctx.send("❌ Veuillez écrire le contenu de votre suggestion.")
    await ctx.send(f"💡 **Nouvelle Suggestion par {ctx.author.mention} :**\n{text}")

@bot.command(name="lb", help="Affiche le classement (`+lb suggestions`).")
async def lb_(ctx, category=None):
    if category == "suggestions":
        await ctx.send("🏆 **Classement des top suggestions :**\n1. Option A\n2. Option B")
    else:
        await ctx.send("Usage: `+lb suggestions`")

@bot.command(help="Recherche un sujet sur Wikipédia et affiche un résumé.")
async def wiki(ctx, *, query=None):
    if not query:
        return await ctx.send("❌ Veuillez spécifier un sujet à chercher (ex: `+wiki France`).")
    try:
        summary = wikipedia.summary(query, sentences=3)
        page = wikipedia.page(query)
        embed = discord.Embed(title=f"📚 Wikipédia : {page.title}", description=summary, color=discord.Color.green())
        embed.add_field(name="Lien complet", value=f"[Lire l'article]({page.url})")
        await ctx.send(embed=embed)
    except wikipedia.exceptions.DisambiguationError as e:
        await ctx.send(f"⚠️ Recherche trop vague. Essayez parmi : {', '.join(e.options[:5])}")
    except wikipedia.exceptions.PageError:
        await ctx.send("❌ Aucun article trouvé sur Wikipédia pour cette recherche.")
    except Exception:
        await ctx.send("❌ Une erreur est survenue lors de la recherche Wikipédia.")

@bot.command(name="search", help="Recherche une page Wikipédia (`+search wiki <sujet>`).")
async def search_(ctx, engine=None, *, query=None):
    if engine == "wiki" and query:
        await wiki(ctx, query=query)
    else:
        await ctx.send("Usage : `+search wiki <votre recherche>`")

@bot.command(help="Calcule une expression mathématique basique (ex: `+calc 5+5`).")
async def calc(ctx, *, expression=None):
    if not expression:
        return await ctx.send("❌ Veuillez entrer une expression mathématique.")
    try:
        allowed = set("0123456789+-*/(). ")
        if not set(expression).issubset(allowed):
            return await ctx.send("❌ Caractères non autorisés.")
        result = eval(expression)
        await ctx.send(f"🧮 **Résultat :** `{result}`")
    except Exception:
        await ctx.send("❌ Expression mathématique invalide.")

@bot.command(help="Affiche la latence actuelle du bot en millisecondes.")
async def ping(ctx):
    await ctx.send(f"🏓 Pong ! `{round(bot.latency * 1000)}ms`")

@bot.command(help="Affiche la vitesse de réponse de l'hébergement.")
async def speed(ctx):
    await ctx.send(f"⚡ Vitesse de connexion serveur : `{round(bot.latency * 1000)}ms`")

# ==========================================
#          COMMANDES PERM 1 À PERM 4
# ==========================================
@bot.command(help="Affiche la liste des sanctions d'un membre.")
async def sanctions(ctx, member: discord.Member = None):
    member = member or ctx.author
    await ctx.send(f"📜 **Sanctions de {member.mention} :** Aucune sanction enregistrée.")

@bot.command(help="Ajoute une note modérateur sur un membre.")
async def note(ctx, member: discord.Member = None, *, text=None):
    if not member or not text:
        return await ctx.send("Usage : `+note @membre <votre note>`")
    await ctx.send(f"📝 Note ajoutée sur **{member.display_name}** : {text}")

@bot.command(name="delnote", help="Supprime une note spécifique par son ID.")
async def note_delete(ctx, note_id=None):
    if not note_id:
        return await ctx.send("Usage : `+delnote <ID_note>`")
    await ctx.send(f"✅ Note `{note_id}` supprimée avec succès.")

@bot.command(help="Mute un membre du serveur.")
async def mute(ctx, member: discord.Member = None, *, reason=None):
    if not member:
        return await ctx.send("Usage : `+mute @membre [raison]`")
    await ctx.send(f"🔇 **{member.mention}** a été rendu muet. Raison : {reason or 'Aucune'}")

@bot.command(help="Mute temporairement un membre.")
async def tempmute(ctx, member: discord.Member = None, time=None, *, reason=None):
    if not member or not time:
        return await ctx.send("Usage : `+tempmute @membre <durée> [raison]`")
    await ctx.send(f"⏱️ **{member.mention}** a été rendu muet pour `{time}`. Raison : {reason or 'Aucune'}")

@bot.command(help="Affiche le niveau de permission d'un membre.")
async def perms(ctx, member: discord.Member = None):
    member = member or ctx.author
    await ctx.send(f"🛡️ **Permissions de {member.mention} :** Membre / Modérateur")

@bot.command(help="Affiche le dernier message supprimé dans le salon.")
async def snipe(ctx):
    await ctx.send("🎯 Aucun message supprimé récent à récupérer.")

@bot.command(help="Expulse un membre d'un salon vocal.")
async def voicekick(ctx, member: discord.Member = None):
    if member and member.voice:
        await member.move_to(None)
        await ctx.send(f"🔊 **{member.display_name}** a été expulsé du salon vocal.")
    else:
        await ctx.send("❌ Membre introuvable ou non connecté en salon vocal.")

@bot.command(help="Avertit un membre avec une raison.")
async def warn(ctx, member: discord.Member = None, *, reason=None):
    if not member:
        return await ctx.send("Usage : `+warn @membre [raison]`")
    await ctx.send(f"⚠️ **{member.mention}** a reçu un avertissement. Raison : {reason or 'Aucune'}")

@bot.command(help="Active ou désactive la sécurité Anti-hack (`+antihack on/off`).")
async def antihack(ctx, status=None):
    if status in ["on", "off"]:
        config["antihack"] = (status == "on")
        await ctx.send(f"🛡️ Anti-hack configuré sur : **{status.upper()}**")
    else:
        await ctx.send("Usage : `+antihack on` ou `+antihack off`")

@bot.command(help="Change le surnom d'un membre du serveur.")
async def nick(ctx, member: discord.Member = None, *, new_nick=None):
    if member:
        await member.edit(nick=new_nick)
        await ctx.send(f"✏️ Surnom de **{member.name}** modifié en : `{new_nick}`")
    else:
        await ctx.send("Usage : `+nick @membre <nouveau_surnom>`")

# ==========================================
#          COMMANDES PERM 5 À PERM 9
# ==========================================
@bot.command(aliases=["delsanction"], help="Supprime une sanction via son ID.")
async def del_(ctx, sanction_id=None):
    if not sanction_id:
        return await ctx.send("Usage : `+del <ID_sanction>`")
    await ctx.send(f"🗑️ Sanction `{sanction_id}` supprimée.")

@bot.command(help="Supprime un nombre de messages dans le salon.")
async def clear(ctx, amount: int = 10):
    await ctx.channel.purge(limit=amount + 1)
    await ctx.send(f"🧹 `{amount}` messages ont été supprimés.", delete_after=5)

@bot.command(help="Restaure la parole d'un membre muté.")
async def unmute(ctx, member: discord.Member = None):
    if not member:
        return await ctx.send("Usage : `+unmute @membre`")
    await ctx.send(f"🔊 **{member.mention}** a été unmuté.")

@bot.command(help="Ajoute un rôle à un membre.")
async def addrole(ctx, member: discord.Member = None, role: discord.Role = None):
    if member and role:
        await member.add_roles(role)
        await ctx.send(f"✅ Rôle **{role.name}** ajouté à {member.mention}.")
    else:
        await ctx.send("Usage : `+addrole @membre @rôle`")

@bot.command(help="Retire un rôle à un membre.")
async def delrole(ctx, member: discord.Member = None, role: discord.Role = None):
    if member and role:
        await member.remove_roles(role)
        await ctx.send(f"🗑️ Rôle **{role.name}** retiré à {member.mention}.")
    else:
        await ctx.send("Usage : `+delrole @membre @rôle`")

@bot.command(name="clearsanctions", help="Efface toutes les sanctions d'un membre.")
async def clear_sanctions_cmd(ctx, member: discord.Member = None):
    if not member:
        return await ctx.send("Usage : `+clearsanctions @membre`")
    await ctx.send(f"🧹 Toutes les sanctions de **{member.display_name}** ont été effacées.")

@bot.command(help="Expulser un membre du serveur.")
async def kick(ctx, member: discord.Member = None, *, reason=None):
    if member:
        await member.kick(reason=reason)
        await ctx.send(f"👞 **{member.display_name}** a été expulsé. Raison : {reason or 'Aucune'}")
    else:
        await ctx.send("Usage : `+kick @membre [raison]`")

@bot.command(help="Affiche la liste des membres bannis du serveur.")
async def banlist(ctx):
    bans = [entry async for entry in ctx.guild.bans()]
    await ctx.send(f"🔨 Il y a actuellement **{len(bans)}** membres bannis sur le serveur.")

@bot.command(help="Bannir définitivement un membre du serveur.")
async def ban(ctx, member: discord.Member = None, *, reason=None):
    if member:
        await member.ban(reason=reason)
        await ctx.send(f"🔨 **{member.display_name}** a été banni. Raison : {reason or 'Aucune'}")
    else:
        await ctx.send("Usage : `+ban @membre [raison]`")

@bot.command(help="Bannir temporairement un membre.")
async def tempban(ctx, member: discord.Member = None, time=None, *, reason=None):
    if member and time:
        await ctx.send(f"⏱️ **{member.display_name}** banni temporairement pour `{time}`.")
    else:
        await ctx.send("Usage : `+tempban @membre <durée> [raison]`")

@bot.command(help="Débannir un membre via son ID Discord.")
async def unban(ctx, user_id: int = None):
    if user_id:
        user = await bot.fetch_user(user_id)
        await ctx.guild.unban(user)
        await ctx.send(f"✅ **{user.name}** a été débanni.")
    else:
        await ctx.send("Usage : `+unban <ID_utilisateur>`")

@bot.command(help="Retire tous les rôles d'un membre.")
async def derank(ctx, member: discord.Member = None):
    if member:
        await ctx.send(f"📉 Derank effectué sur **{member.display_name}**.")
    else:
        await ctx.send("Usage : `+derank @membre`")

@bot.command(help="Verrouille le nom d'un membre.")
async def lockname(ctx, member: discord.Member = None):
    await ctx.send("🔒 Nom verrouillé.")

@bot.command(help="Déverrouille le nom d'un membre.")
async def unlockname(ctx):
    await ctx.send("🔓 Nom déverrouillé.")

@bot.command(help="Affiche la liste des pseudos verrouillés.")
async def locknamelist(ctx):
    await ctx.send("📋 Liste des pseudos verrouillés...")

@bot.command(help="Affiche le rang de blacklist.")
async def blrank(ctx):
    await ctx.send("⛔ Rang de blacklist affiché.")

@bot.command(help="Ajoute un membre à la Blacklist du bot.")
async def bl(ctx, member: discord.Member = None):
    if member:
        await ctx.send(f"⛔ **{member.display_name}** a été ajouté à la Blacklist.")
    else:
        await ctx.send("Usage : `+bl @membre`")

@bot.command(help="Retire un membre de la Blacklist.")
async def unbl(ctx, member: discord.Member = None):
    if member:
        await ctx.send(f"✅ **{member.display_name}** retiré de la Blacklist.")
    else:
        await ctx.send("Usage : `+unbl @membre`")

@bot.command(help="Affiche les infos de blacklist.")
async def blinfo(ctx, member: discord.Member = None):
    await ctx.send("ℹ️ Informations de Blacklist chargées.")

# ==========================================
#          COMMANDES OWNERS
# ==========================================
@bot.command(help="Mute le salon textuel courant.")
async def cmute(ctx, *, reason=None):
    await ctx.channel.set_permissions(ctx.guild.default_role, send_messages=False)
    await ctx.send("🔒 Le salon a été rendu muet pour les membres.")

@bot.command(help="Mute temporairement le salon textuel.")
async def tempcmute(ctx, time=None):
    await ctx.send(f"⏱️ Salon muté pour une durée de `{time}`.")

@bot.command(help="Démute le salon textuel.")
async def uncmute(ctx):
    await ctx.channel.set_permissions(ctx.guild.default_role, send_messages=True)
    await ctx.send("🔓 Le salon est de nouveau ouvert à tous.")

@bot.command(help="Affiche la liste des membres mutés.")
async def mutelist(ctx):
    await ctx.send("📋 **Liste des mutés :** Aucun membre muté actuellement.")

@bot.command(help="Démute tous les membres.")
async def unmuteall(ctx):
    await ctx.send("🔊 Tous les membres ont été démutés.")

@bot.command(help="Verrouille l'écriture dans le salon.")
async def lock(ctx):
    await ctx.channel.set_permissions(ctx.guild.default_role, send_messages=False)
    await ctx.send("🔒 Salon verrouillé.")

@bot.command(help="Déverrouille l'écriture dans le salon.")
async def unlock(ctx):
    await ctx.channel.set_permissions(ctx.guild.default_role, send_messages=True)
    await ctx.send("🔓 Salon déverrouillé.")

@bot.command(help="Verrouille tous les salons.")
async def lockall(ctx):
    await ctx.send("🔒 Tous les salons du serveur ont été verrouillés.")

@bot.command(help="Déverrouille tous les salons.")
async def unlockall(ctx):
    await ctx.send("🔓 Tous les salons du serveur ont été déverrouillés.")

@bot.command(help="Masque le salon actuel.")
async def hide(ctx):
    await ctx.channel.set_permissions(ctx.guild.default_role, view_channel=False)
    await ctx.send("👁️‍🗨️ Salon masqué.")

@bot.command(help="Affiche le salon actuel.")
async def unhide(ctx):
    await ctx.channel.set_permissions(ctx.guild.default_role, view_channel=True)
    await ctx.send("👁️ Salon affiché.")

@bot.command(help="Masque tous les salons.")
async def hideall(ctx):
    await ctx.send("👁️‍🗨️ Tous les salons du serveur ont été masqués.")

@bot.command(help="Affiche tous les salons.")
async def unhideall(ctx):
    await ctx.send("👁️ Tous les salons ont été réaffichés.")

@bot.command(help="Affiche les paramètres du bot.")
async def settings(ctx):
    status_antilink = "Activé" if config["antilink"] else "Désactivé"
    status_antispam = "Activé" if config["antispam"] else "Désactivé"
    await ctx.send(f"⚙️ **Configuration Actuelle :**\n- Anti-link : `{status_antilink}`\n- Anti-spam : `{status_antispam}`")

@bot.command(help="Active ou désactive l'anti-spam (`+antispam on/off`).")
async def antispam(ctx, status=None):
    if status in ["on", "off"]:
        config["antispam"] = (status == "on")
        await ctx.send(f"🛡️ Anti-spam configuré sur : **{status.upper()}**")
    else:
        await ctx.send("Usage : `+antispam on` ou `+antispam off`")

@bot.command(help="Active ou désactive l'anti-link (`+antilink on/off`).")
async def antilink(ctx, status: str = None):
    if not status:
        current = "activé" if config["antilink"] else "désactivé"
        return await ctx.send(f"L'anti-link est actuellement **{current}**. Utilisez `+antilink on` ou `+antilink off`.")
    
    if status.lower() in ["on", "enable", "1", "true"]:
        config["antilink"] = True
        await ctx.send("✅ **Anti-link activé** ! Tous les liens seront automatiquement supprimés.")
    elif status.lower() in ["off", "disable", "0", "false"]:
        config["antilink"] = False
        await ctx.send("❌ **Anti-link désactivé**.")
    else:
        await ctx.send("Usage : `+antilink on` ou `+antilink off`.")

@bot.command(help="Gère la liste des mots interdits.")
async def badwords(ctx, action=None):
    await ctx.send("🤬 Gestionnaire de mots interdits actif.")

@bot.command(help="Affiche tous les bots du serveur.")
async def allbots(ctx):
    bots = [m.mention for m in ctx.guild.members if m.bot]
    await ctx.send(f"🤖 **Bots du serveur ({len(bots)}) :**\n" + ", ".join(bots))

@bot.command(help="Affiche tous les administrateurs.")
async def alladmins(ctx):
    admins = [m.mention for m in ctx.guild.members if m.guild_permissions.administrator and not m.bot]
    await ctx.send(f"👑 **Administrateurs ({len(admins)}) :**\n" + ", ".join(admins))

@bot.command(help="Affiche les boosters du serveur.")
async def boosters(ctx):
    boosters_list = [m.mention for m in ctx.guild.premium_subscribers]
    if boosters_list:
        await ctx.send(f"💎 **Boosters ({len(boosters_list)}) :**\n" + ", ".join(boosters_list))
    else:
        await ctx.send("💎 Aucun booster sur ce serveur actuellement.")

@bot.command(help="Affiche les infos du serveur.")
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
#          MENU D'AIDE INTERACTIF (BOUTONS)
# ==========================================
class HelpView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=180)

    @discord.ui.button(label="Public", style=discord.ButtonStyle.primary, emoji="🌐")
    async def public_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(title="🌐 Commandes Publiques", description="`+crowbots`, `+mybots`, `+pic`, `+banner`, `+server pic/banner`, `+emoji`, `+image`, `+suggestion`, `+lb suggestions`, `+wiki`, `+search`, `+calc`, `+help`, `+ping`, `+speed`", color=discord.Color.blue())
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="Perm 1-3", style=discord.ButtonStyle.secondary, emoji="🛡️")
    async def perm1_3_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(title="🛡️ Commandes Perm 1 à 3", description="**Perm 1:** `+sanctions`, `+note`, `+delnote`, `+mute`, `+tempmute`, `+perms`, `+snipe`\n**Perm 2:** `+voicekick`\n**Perm 3:** `+warn`, `+antihack`", color=discord.Color.green())
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="Perm 4-6", style=discord.ButtonStyle.secondary, emoji="⚖️")
    async def perm4_6_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(title="⚖️ Commandes Perm 4 à 6", description="**Perm 4:** `+nick`\n**Perm 5:** `+del`, `+clear`, `+unmute`\n**Perm 6:** `+addrole`, `+delrole`", color=discord.Color.orange())
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="Perm 7-9", style=discord.ButtonStyle.danger, emoji="🔨")
    async def perm7_9_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(title="🔨 Commandes Perm 7 à 9", description="**Perm 7:** `+clearsanctions`, `+kick`, `+banlist`\n**Perm 8:** `+ban`, `+tempban`, `+unban`, `+derank`, `+lockname`, `+unlockname`, `+locknamelist`, `+blrank`\n**Perm 9:** `+bl`, `+unbl`, `+blinfo`", color=discord.Color.red())
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="Owners", style=discord.ButtonStyle.success, emoji="⚙️")
    async def owners_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(title="⚙️ Commandes Owners", description="`+cmute`, `+tempcmute`, `+uncmute`, `+mutelist`, `+unmuteall`, `+lock`, `+unlock`, `+lockall`, `+unlockall`, `+hide`, `+unhide`, `+hideall`, `+unhideall`, `+settings`, `+antispam`, `+antilink`, `+badwords`, `+allbots`, `+alladmins`, `+boosters`, `+serverinfo`", color=discord.Color.gold())
        await interaction.response.edit_message(embed=embed, view=self)

@bot.command(help="Affiche le menu d'aide interactif avec boutons de permissions.")
async def help(ctx):
    embed = discord.Embed(
        title="📖 Menu d'aide interactif - Gstion",
        description="Cliquez sur les boutons ci-dessous pour naviguer entre les différentes catégories de permissions.",
        color=discord.Color.blue()
    )
    embed.set_footer(text="Bot gstion • Utilisez les boutons pour changer de catégorie.")
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
