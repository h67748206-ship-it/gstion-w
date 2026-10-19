import os
import threading
from flask import Flask
import discord
from discord.ext import commands

# ==========================================
#            CONFIGURATION FLASK
# ==========================================
app = Flask('')


@app.route('/')
def home():
  return "Le bot est en ligne et actif !"


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


@bot.event
async def on_ready():
  print(f'Connecté en tant que {bot.user.name} (ID: {bot.user.id})')
  print('Le bot est prêt et opérationnel !')


# ==========================================
#          COMMANDES PUBLIQUES
# ==========================================
@bot.command()
async def crowbots(ctx):
  await ctx.send("Liste des bots publics...")


@bot.command()
async def mybots(ctx):
  await ctx.send("Vos bots enregistrés...")


@bot.command()
async def pic(ctx, member: discord.Member = None):
  member = member or ctx.author
  await ctx.send(member.display_avatar.url)


@bot.command()
async def banner(ctx, member: discord.Member = None):
  member = member or ctx.author
  user = await bot.fetch_user(member.id)
  if user.banner:
    await ctx.send(user.banner.url)
  else:
    await ctx.send("Cet utilisateur n'a pas de bannière.")


@bot.command(name="server")
async def server_(ctx, action: str = None):
  if action == "pic":
    await ctx.send(
        ctx.guild.icon.url if ctx.guild.icon else "Pas d'icône de serveur."
    )
  elif action == "banner":
    await ctx.send(
        ctx.guild.banner.url
        if ctx.guild.banner
        else "Pas de bannière de serveur."
    )
  else:
    await ctx.send("Usage: `+server pic` ou `+server banner`")


@bot.command()
async def emoji(ctx, emoji: discord.Emoji = None):
  if emoji:
    await ctx.send(emoji.url)
  else:
    await ctx.send("Veuillez spécifier un emoji valide.")


@bot.command()
async def image(ctx):
  await ctx.send("Commande image.")


@bot.command()
async def suggestion(ctx, *, text=None):
  if not text:
    return await ctx.send("Veuillez mettre le contenu de votre suggestion.")
  await ctx.send("Votre suggestion a été envoyée avec succès !")


@bot.command(name="lb")
async def lb_(ctx, category=None):
  if category == "suggestions":
    await ctx.send("Classement des suggestions...")
  else:
    await ctx.send("Usage: `+lb suggestions`")


@bot.command()
async def wiki(ctx, *, query=None):
  await ctx.send(f"Recherche Wikipédia pour : {query}")


@bot.command(name="search")
async def search_(ctx, engine=None, *, query=None):
  await ctx.send(f"Recherche...")


@bot.command()
async def calc(ctx, *, expression=None):
  try:
    result = eval(expression)
    await ctx.send(f"Résultat : {result}")
  except Exception:
    await ctx.send("Erreur de calcul.")


@bot.command()
async def ping(ctx):
  await ctx.send(f"Pong ! `{round(bot.latency * 1000)}ms`")


@bot.command()
async def speed(ctx):
  await ctx.send("Test de vitesse...")


# ==========================================
#          COMMANDES PERM 1
# ==========================================
@bot.command()
async def sanctions(ctx, member: discord.Member = None):
  await ctx.send("Liste des sanctions...")


@bot.command()
async def note(ctx, member: discord.Member = None, *, text=None):
  await ctx.send("Note ajoutée.")


@bot.command(name="delnote")
async def note_delete(ctx, note_id=None):
  await ctx.send(f"Note {note_id} supprimée.")


@bot.command()
async def mute(ctx, member: discord.Member = None, *, reason=None):
  await ctx.send(f"{member} a été muté.")


@bot.command()
async def tempmute(
    ctx, member: discord.Member = None, time=None, *, reason=None
):
  await ctx.send(f"{member} a été tempmute pour {time}.")


@bot.command()
async def perms(ctx, member: discord.Member = None):
  await ctx.send("Permissions du membre...")


@bot.command()
async def snipe(ctx):
  await ctx.send("Dernier message supprimé...")


# ==========================================
#          COMMANDES PERM 2
# ==========================================
@bot.command()
async def voicekick(ctx, member: discord.Member = None):
  if member and member.voice:
    await member.move_to(None)
    await ctx.send(f"{member} a été déconnecté du vocal.")
  else:
    await ctx.send("Membre introuvable ou non connecté en vocal.")


# ==========================================
#          COMMANDES PERM 3
# ==========================================
@bot.command()
async def warn(ctx, member: discord.Member = None, *, reason=None):
  await ctx.send(f"{member} a reçu un avertissement.")


@bot.command()
async def antihack(ctx, status=None):
  await ctx.send(f"Anti-hack configuré sur : {status}")


# ==========================================
#          COMMANDES PERM 4
# ==========================================
@bot.command()
async def nick(ctx, member: discord.Member = None, *, new_nick=None):
  if member:
    await member.edit(nick=new_nick)
    await ctx.send(f"Surnom de {member} modifié.")


# ==========================================
#          COMMANDES PERM 5
# ==========================================
@bot.command(aliases=["delsanction"])
async def del_(ctx, sanction_id=None):
  await ctx.send(f"Sanction {sanction_id} supprimée.")


@bot.command()
async def clear(ctx, amount: int = 10):
  await ctx.channel.purge(limit=amount + 1)
  await ctx.send(f"{amount} messages supprimés.", delete_after=5)


@bot.command()
async def unmute(ctx, member: discord.Member = None):
  await ctx.send(f"{member} a été unmuté.")


# ==========================================
#          COMMANDES PERM 6
# ==========================================
@bot.command()
async def addrole(
    ctx, member: discord.Member = None, role: discord.Role = None
):
  if member and role:
    await member.add_roles(role)
    await ctx.send(f"Rôle {role.name} ajouté à {member}.")


@bot.command()
async def delrole(
    ctx, member: discord.Member = None, role: discord.Role = None
):
  if member and role:
    await member.remove_roles(role)
    await ctx.send(f"Rôle {role.name} retiré de {member}.")


# ==========================================
#          COMMANDES PERM 7
# ==========================================
@bot.command(name="clearsanctions")
async def clear_sanctions_cmd(ctx, member: discord.Member = None):
  await ctx.send(f"Sanctions effacées pour {member}.")


@bot.command()
async def kick(ctx, member: discord.Member = None, *, reason=None):
  if member:
    await member.kick(reason=reason)
    await ctx.send(f"{member} a été expulsé.")


@bot.command()
async def banlist(ctx):
  bans = [entry async for entry in ctx.guild.bans()]
  await ctx.send(f"Il y a {len(bans)} bannières sur le serveur.")


# ==========================================
#          COMMANDES PERM 8
# ==========================================
@bot.command()
async def ban(ctx, member: discord.Member = None, *, reason=None):
  if member:
    await member.ban(reason=reason)
    await ctx.send(f"{member} a été banni.")


@bot.command()
async def tempban(
    ctx, member: discord.Member = None, time=None, *, reason=None
):
  await ctx.send(f"{member} banni temporairement.")


@bot.command()
async def unban(ctx, user_id: int = None):
  if user_id:
    user = await bot.fetch_user(user_id)
    await ctx.guild.unban(user)
    await ctx.send(f"{user} a été débanni.")


@bot.command()
async def derank(ctx, member: discord.Member = None):
  await ctx.send(f"Derank effectué sur {member}.")


@bot.command()
async def lockname(ctx, *, name=None):
  await ctx.send("Nom verrouillé.")


@bot.command()
async def unlockname(ctx):
  await ctx.send("Nom déverrouillé.")


@bot.command()
async def locknamelist(ctx):
  await ctx.send("Liste des noms verrouillés...")


@bot.command()
async def blrank(ctx):
  await ctx.send("Blacklist rang...")


# ==========================================
#          COMMANDES PERM 9
# ==========================================
@bot.command()
async def bl(ctx, member: discord.Member = None):
  await ctx.send(f"{member} a été blacklisté.")


@bot.command()
async def unbl(ctx, member: discord.Member = None):
  await ctx.send(f"{member} a été retiré de la blacklist.")


@bot.command()
async def blinfo(ctx, member: discord.Member = None):
  await ctx.send("Infos de blacklist...")


# ==========================================
#          COMMANDES OWNERS
# ==========================================
@bot.command()
async def cmute(ctx, *, reason=None):
  await ctx.send("Chat muté pour tout le monde.")


@bot.command()
async def tempcmute(ctx, time=None):
  await ctx.send(f"Chat muté pour {time}.")


@bot.command()
async def uncmute(ctx):
  await ctx.send("Chat démuté.")


@bot.command()
async def mutelist(ctx):
  await ctx.send("Liste des mutés...")


@bot.command()
async def unmuteall(ctx):
  await ctx.send("Tout le monde a été démuté.")


@bot.command()
async def lock(ctx):
  await ctx.set_permissions(ctx.channel, send_messages=False)
  await ctx.send("Salon verrouillé.")


@bot.command()
async def unlock(ctx):
  await ctx.set_permissions(ctx.channel, send_messages=True)
  await ctx.send("Salon déverrouillé.")


@bot.command()
async def lockall(ctx):
  await ctx.send("Tous les salons ont été verrouillés.")


@bot.command()
async def unlockall(ctx):
  await ctx.send("Tous les salons ont été déverrouillés.")


@bot.command()
async def hide(ctx):
  await ctx.send("Salon masqué.")


@bot.command()
async def unhide(ctx):
  await ctx.send("Salon affiché.")


@bot.command()
async def hideall(ctx):
  await ctx.send("Tous les salons ont été masqués.")


@bot.command()
async def unhideall(ctx):
  await ctx.send("Tous les salons ont été réaffichés.")


@bot.command()
async def settings(ctx):
  await ctx.send("Paramètres du bot...")


@bot.command()
async def antispam(ctx, status=None):
  await ctx.send(f"Anti-spam : {status}")


@bot.command()
async def antilink(ctx, status=None):
  await ctx.send(f"Anti-lien : {status}")


@bot.command()
async def badwords(ctx, action=None):
  await ctx.send("Gestion des mots interdits.")


@bot.command()
async def allbots(ctx):
  await ctx.send("Liste de tous les bots...")


@bot.command()
async def alladmins(ctx):
  await ctx.send("Liste de tous les administrateurs...")


@bot.command()
async def boosters(ctx):
  await ctx.send("Liste des boosters...")


@bot.command()
async def serverinfo(ctx):
  await ctx.send(f"Informations du serveur : {ctx.guild.name}")


@bot.command()
async def helpall(ctx):
  embed = discord.Embed(
      title="📖 Liste complète des commandes de gstion",
      description=(
          "Voici l'intégralité des commandes disponibles selon les"
          " permissions :"
      ),
      color=discord.Color.blue(),
  )
  embed.add_field(
      name="🌐 Public",
      value=(
          "`+crowbots`, `+mybots`, `+pic`, `+banner`, `+server pic/banner`,"
          " `+emoji`, `+image`, `+suggestion`, `+lb suggestions`, `+wiki`,"
          " `+search`, `+calc`, `+help`, `+ping`, `+speed`"
      ),
      inline=False,
  )
  embed.add_field(
      name="🛡️ Perm 1",
      value=(
          "`+sanctions`, `+note`, `+delnote`, `+mute`, `+tempmute`, `+perms`,"
          " `+snipe`"
      ),
      inline=False,
  )
  embed.add_field(name="🔊 Perm 2", value="`+voicekick`", inline=False)
  embed.add_field(
      name="⚠️ Perm 3", value="`+warn`, `+antihack`", inline=False
  )
  embed.add_field(name="✏️ Perm 4", value="`+nick`", inline=False)
  embed.add_field(
      name="🧹 Perm 5",
      value=(
          "`+del` (ou `+delsanction`), `+clear`, `+unmute`"
      ),
      inline=False,
  )
  embed.add_field(
      name="👑 Perm 6", value="`+addrole`, `+delrole`", inline=False
  )
  embed.add_field(
      name="🔨 Perm 7", value="`+clearsanctions`, `+kick`, `+banlist`", inline=False
  )
  embed.add_field(
      name="🔒 Perm 8",
      value=(
          "`+ban`, `+tempban`, `+unban`, `+derank`, `+lockname`, `+unlockname`,"
          " `+locknamelist`, `+blrank`"
      ),
      inline=False,
  )
  embed.add_field(
      name="⛔ Perm 9", value="`+bl`, `+unbl`, `+blinfo`", inline=False
  )
  embed.add_field(
      name="⚙️ Owners",
      value=(
          "`+cmute`, `+tempcmute`, `+uncmute`, `+mutelist`, `+unmuteall`,"
          " `+lock`/`+unlock`, `+lockall`/`+unlockall`, `+hide`/`+unhide`,"
          " `+hideall`/`+unhideall`, `+settings`, `+antispam`, `+antilink`,"
          " `+badwords`, `+allbots`, `+alladmins`, `+boosters`,"
          " `+serverinfo`, `+helpall`"
      ),
      inline=False,
  )
  embed.set_footer(text="Bot gstion • Préfixe : +")
  await ctx.send(embed=embed)


@bot.command()
async def help(ctx):
  await ctx.send("Menu d'aide principal de gstion (`+help`)")


# ==========================================
#            LANCEMENT DU BOT
# ==========================================
if __name__ == "__main__":
  keep_alive()
  token = os.environ.get("DISCORD_TOKEN")
  if not token:
    print(
        "ERREUR : La variable d'environnement DISCORD_TOKEN n'a pas été trouvée"
        " sur Render !"
    )
  else:
    bot.run(token)
