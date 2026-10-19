import discord
from discord.ext import commands
from flask import Flask
from threading import Thread

# 1. Configuration des Intents
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.guilds = True

# 2. Initialisation du bot avec le préfixe "+"
bot = commands.Bot(command_prefix="+", intents=intents)
bot.remove_command("help") # Supprime l'aide par défaut

@bot.event
async def on_ready():
    print(f"-----------------------------------------")
    print(f" Bot connecté en tant que : {bot.user.name}")
    print(f" Morceau 1 (PUBLIC) & Mini site web actifs !")
    print(f"-----------------------------------------")


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
async def image_cmd(ctx, *, mot_clé: str):
    """Recherche une image par mot-clé[cite: 17]"""
    await ctx.send(f"🔍 Recherche d'image pour : `{mot_clé}`...")

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
async def wiki(ctx, *, mot_clé: str = None):
    """Recherche Wikipedia[cite: 17]"""
    if mot_clé:
        await ctx.send(f"📚 Recherche Wikipedia pour : `{mot_clé}`")
    else:
        await ctx.send("Utilisation : `+wiki <mot-clé>`")

@bot.command(name="search")
async def search_cmd(ctx, option: str = None, *, mot_clé: str = None):
    """Commande de recherche (ex: +search wiki <mot-clé>)[cite: 17]"""
    if option == "wiki" and mot_clé:
        await ctx.send(f"📚 Recherche Wikipedia pour : `{mot_clé}`")
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

@bot.command(name="help")
async def help_cmd(ctx, *, mot_clé: str = None):
    """Affiche l'aide globale du bot[cite: 17]"""
    if mot_clé:
        await ctx.send(f"📖 Aide pour : `{mot_clé}`")
    else:
        await ctx.send("📜 **Aide Public :** `+crowbots`, `+mybots`, `+pic`, `+banner`, `+server pic`, `+server banner`, `+emoji`, `+image`, `+suggestion`, `+lb suggestions`, `+wiki`, `+calc`, `+ping`, `+speed`")


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
    # Lance le mini site web en arrière-plan
    keep_alive()
    # Lance le bot Discord (Remplacez par votre vrai token)
    bot.run("VOTRE_TOKEN_DISCORD") 
