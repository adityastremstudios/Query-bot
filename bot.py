import discord
from discord.ext import commands
import json
import os
import difflib
import time
from collections import defaultdict, deque

# ==========================
#    CONFIG
# ==========================

DISCORD_TOKEN = "MTQyMTkxOTYxMzc5MjI4ODg2OQ.GREqDw.n7xFOajmsNOvSlzqA5y6Wu8_DCpOmfYufsuWaY"

# Channels where bot responds (leave [] to allow all)
ALLOWED_CHANNELS = [
    # 1192428442780696617, # 1428235007843106846, # 1381196391728156742,   # <-- replace with your Channel ID if you want
]

# Admin-like roles (for Q&A edit, etc. baseline)
ADMIN_ROLES = ["Admin", "Owner"]

KNOWLEDGE_FILE = "knowledge.json"
CONFIG_FILE = "bot_config.json"

PREFIX = "!"

# Moderation
BAD_WORDS = ["fuck", "shit", "bitch"]      # simple moderation
AUTO_DELETE_BAD_WORDS = True               # toggle ON/OFF

# Anti-spam settings
SPAM_WINDOW_SECONDS = 10      # time window length
SPAM_MAX_MESSAGES = 7         # max messages allowed in window
REPEAT_MAX_SAME = 3           # max times user can send same message

WELCOME_ENABLED = True        # toggle welcoming

# ==========================


def load_config():
    """Load or create bot configuration (who can manage the bot)."""
    default = {
        "bot_managers_roles": [],  # list of role IDs
        "bot_managers_users": []   # list of user IDs
    }
    if os.path.exists(CONFIG_FILE) and os.path.getsize(CONFIG_FILE) > 0:
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                # ensure keys
                for k in default:
                    if k not in data:
                        data[k] = default[k]
                return data
        except Exception as e:
            print("Config invalid, using default:", e)
            return default
    else:
        return default


def save_config():
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)


config = load_config()


def is_admin_role(member: discord.Member):
    return any(role.name in ADMIN_ROLES for role in member.roles)


def can_manage_bot(member: discord.Member):
    """Who can manage bot permissions and high-level config."""
    if member.guild is None:
        return False
    # Server owner
    if member == member.guild.owner:
        return True
    # Has Administrator permission
    if member.guild_permissions.administrator:
        return True
    # In config as manager user
    if member.id in config.get("bot_managers_users", []):
        return True
    # Has a manager role
    manager_roles = config.get("bot_managers_roles", [])
    if any(role.id in manager_roles for role in member.roles):
        return True
    return False


# Load knowledge file
def load_knowledge():
    if os.path.exists(KNOWLEDGE_FILE) and os.path.getsize(KNOWLEDGE_FILE) > 0:
        try:
            with open(KNOWLEDGE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            print("knowledge.json invalid, starting empty")
    return []


knowledge = load_knowledge()


def save_knowledge():
    with open(KNOWLEDGE_FILE, "w", encoding="utf-8") as f:
        json.dump(knowledge, f, indent=2, ensure_ascii=False)


# Intelligent Matching System with basic "ranking" by usage
def find_best_answer(msg: str):
    msg = msg.lower()
    msg_words = set(msg.split())

    best_score = 0
    best_idx = None

    for idx, entry in enumerate(knowledge):
        q = entry["question"].lower()

        # 1. Direct substring bonus
        score = 2 if q in msg or msg in q else 0

        # 2. Word overlap bonus
        q_words = set(q.split())
        score += len(msg_words & q_words)

        # 3. Fuzzy match bonus
        similarity = difflib.SequenceMatcher(None, msg, q).ratio()
        if similarity > 0.5:
            score += int(similarity * 5)

        # 4. Usage bonus (knowledge ranking)
        uses = entry.get("uses", 0)
        score += min(uses, 10)  # cap bonus

        if score > best_score:
            best_score = score
            best_idx = idx

    if best_idx is not None and best_score >= 3:
        # increase usage count
        knowledge[best_idx]["uses"] = knowledge[best_idx].get("uses", 0) + 1
        save_knowledge()
        return knowledge[best_idx]["answer"]
    else:
        return None


# Anti-spam tracking
user_messages_times = defaultdict(lambda: deque())
user_last_contents = defaultdict(lambda: deque(maxlen=REPEAT_MAX_SAME))

intents = discord.Intents.default()
intents.members = True
intents.message_content = True

bot = commands.Bot(command_prefix=PREFIX, intents=intents)


# ==========================
#     EVENTS
# ==========================

@bot.event
@bot.event
async def on_ready():
    try:
        synced = await bot.tree.sync()
        print(f"🌍 Global slash commands synced: {[cmd.name for cmd in synced]}")
    except Exception as e:
        print("❌ Slash command sync error:", e)

    print(f"✅ Logged in as {bot.user}")


@bot.event
async def on_member_join(member):
    if WELCOME_ENABLED:
        try:
            await member.send(f"🎉 Welcome to **{member.guild.name}**!")
        except:
            pass


async def handle_spam(message: discord.Message) -> bool:
    """
    Returns True if message is handled as spam (deleted/warned).
    """
    now = time.time()
    user_id = message.author.id

    # Track timestamps
    times = user_messages_times[user_id]
    times.append(now)

    # Remove old timestamps
    while times and now - times[0] > SPAM_WINDOW_SECONDS:
        times.popleft()

    # Check spam by frequency
    if len(times) > SPAM_MAX_MESSAGES:
        try:
            await message.delete()
        except:
            pass
        await message.channel.send(
            f"{message.author.mention}, please slow down, you're sending messages too fast."
        )
        return True

    # Check repeated content
    content_norm = message.content.strip().lower()
    if content_norm:
        contents = user_last_contents[user_id]
        contents.append(content_norm)
        if len(contents) >= REPEAT_MAX_SAME and all(c == content_norm for c in contents):
            try:
                await message.delete()
            except:
                pass
            await message.channel.send(
                f"{message.author.mention}, please don't repeat the same message."
            )
            return True

    return False


@bot.event
async def on_message(message: discord.Message):
    await bot.process_commands(message)

    if message.author == bot.user:
        return

    # Filter by channel
    if ALLOWED_CHANNELS and message.channel.id not in ALLOWED_CHANNELS:
        return

    # Bad word moderation
    if AUTO_DELETE_BAD_WORDS:
        lower_content = message.content.lower()
        for bad in BAD_WORDS:
            if bad in lower_content:
                try:
                    await message.delete()
                except:
                    pass
                await message.channel.send(
                    f"{message.author.mention}, please avoid using that language."
                )
                return

    # Anti-spam
    if await handle_spam(message):
        return

    # Skip commands
    if message.content.startswith(PREFIX):
        return

    # Try to answer using knowledge
    answer = find_best_answer(message.content)
    if answer:
        await message.reply(answer)


# ==========================
#  PREFIX COMMANDS (Q&A)
# ==========================

@bot.command(name="addqa")
async def addqa(ctx, *, text: str):
    if not is_admin_role(ctx.author) and not can_manage_bot(ctx.author):
        return await ctx.send("❌ You do not have permission.")

    if "||" not in text:
        return await ctx.send("Format:\n`!addqa question || answer`")

    question, answer = map(str.strip, text.split("||", 1))

    knowledge.append({"question": question, "answer": answer, "uses": 0})
    save_knowledge()

    await ctx.send(f"✅ Added Q&A:\n**Q:** {question}\n**A:** {answer}")


@bot.command(name="listqa")
async def listqa(ctx):
    if not knowledge:
        return await ctx.send("No Q&A saved yet.")

    msg = ""
    for i, entry in enumerate(knowledge, start=1):
        uses = entry.get("uses", 0)
        msg += f"**{i}. Q:** {entry['question']} (used {uses} times)\n**A:** {entry['answer']}\n\n"

    await ctx.send(msg[:1900])


@bot.command(name="delqa")
async def delqa(ctx, index: int):
    if not is_admin_role(ctx.author) and not can_manage_bot(ctx.author):
        return await ctx.send("❌ You do not have permission.")

    if index < 1 or index > len(knowledge):
        return await ctx.send("Invalid index.")

    removed = knowledge.pop(index - 1)
    save_knowledge()

    await ctx.send(f"🗑️ Deleted:\n**Q:** {removed['question']}")


@bot.command(name="editqa")
async def editqa(ctx, *, text: str):
    if not is_admin_role(ctx.author) and not can_manage_bot(ctx.author):
        return await ctx.send("❌ You do not have permission.")

    if "||" not in text:
        return await ctx.send("Format:\n`!editqa index || new question || new answer`")

    parts = text.split("||")
    if len(parts) != 3:
        return await ctx.send("Use format:\n`!editqa index || new question || new answer`")

    try:
        index = int(parts[0].strip())
    except ValueError:
        return await ctx.send("Index must be a number.")

    new_q = parts[1].strip()
    new_a = parts[2].strip()

    if index < 1 or index > len(knowledge):
        return await ctx.send("Invalid index.")

    # keep usage count but update Q/A
    old_uses = knowledge[index - 1].get("uses", 0)
    knowledge[index - 1] = {"question": new_q, "answer": new_a, "uses": old_uses}
    save_knowledge()

    await ctx.send("✏️ Updated successfully!")


@bot.command(name="searchqa")
async def searchqa(ctx, *, keyword: str):
    results = [
        f"**Q:** {entry['question']} (used {entry.get('uses', 0)} times)\n**A:** {entry['answer']}"
        for entry in knowledge
        if keyword.lower() in entry["question"].lower()
    ]

    if results:
        await ctx.send("\n\n".join(results[:10]))
    else:
        await ctx.send("No matches found.")


# ==========================
#   SLASH COMMANDS (Q&A)
# ==========================

@bot.tree.command(name="ask", description="Ask the knowledge bot a question")
async def slash_ask(interaction: discord.Interaction, question: str):
    answer = find_best_answer(question)
    if answer:
        await interaction.response.send_message(answer)
    else:
        await interaction.response.send_message(
            "I don't know that yet. Ask an admin to teach me with /addqa or !addqa.",
            ephemeral=True
        )


@bot.tree.command(name="qa_add", description="Teach the bot a new Q&A (admin/manager only)")
async def slash_addqa(interaction: discord.Interaction, data: str):
    user = interaction.user
    if not isinstance(user, discord.Member):
        return await interaction.response.send_message(
            "This command can only be used in a server.",
            ephemeral=True
        )

    if not is_admin_role(user) and not can_manage_bot(user):
        return await interaction.response.send_message(
            "❌ You do not have permission.", ephemeral=True
        )

    if "||" not in data:
        return await interaction.response.send_message(
            "Format:\n`/qa_add data: question || answer`",
            ephemeral=True
        )

    question, answer = map(str.strip, data.split("||", 1))
    knowledge.append({"question": question, "answer": answer, "uses": 0})
    save_knowledge()

    await interaction.response.send_message(
        f"✅ Added Q&A:\n**Q:** {question}\n**A:** {answer}"
    )


@bot.tree.command(name="qa_list", description="List known Q&A")
async def slash_listqa(interaction: discord.Interaction):
    if not knowledge:
        return await interaction.response.send_message(
            "No Q&A saved yet.",
            ephemeral=True
        )

    msg = ""
    for i, entry in enumerate(knowledge, start=1):
        uses = entry.get("uses", 0)
        msg += f"**{i}. Q:** {entry['question']} (used {uses} times)\n**A:** {entry['answer']}\n\n"

    await interaction.response.send_message(msg[:1900])


@bot.tree.command(name="qa_search", description="Search Q&A by keyword")
async def slash_searchqa(interaction: discord.Interaction, keyword: str):
    results = [
        f"**Q:** {entry['question']} (used {entry.get('uses', 0)} times)\n**A:** {entry['answer']}"
        for entry in knowledge
        if keyword.lower() in entry["question"].lower()
    ]

    if results:
        await interaction.response.send_message("\n\n".join(results[:10]))
    else:
        await interaction.response.send_message("No matches found.")


# ==========================
#   SLASH COMMANDS (BOT MANAGER CONTROL)
# ==========================

@bot.tree.command(name="botaddrole", description="Add a role that can manage the bot")
async def slash_botaddrole(interaction: discord.Interaction, role: discord.Role):
    user = interaction.user
    if not isinstance(user, discord.Member) or not can_manage_bot(user):
        return await interaction.response.send_message(
            "❌ You are not allowed to change bot permissions.",
            ephemeral=True
        )

    if role.id not in config["bot_managers_roles"]:
        config["bot_managers_roles"].append(role.id)
        save_config()

    await interaction.response.send_message(
        f"✅ Role {role.mention} can now manage the bot."
    )


@bot.tree.command(name="botremoverole", description="Remove a role from bot managers")
async def slash_botremoverole(interaction: discord.Interaction, role: discord.Role):
    user = interaction.user
    if not isinstance(user, discord.Member) or not can_manage_bot(user):
        return await interaction.response.send_message(
            "❌ You are not allowed to change bot permissions.",
            ephemeral=True
        )

    if role.id in config["bot_managers_roles"]:
        config["bot_managers_roles"].remove(role.id)
        save_config()

    await interaction.response.send_message(
        f"🗑️ Role {role.mention} is no longer a bot manager."
    )


@bot.tree.command(name="botadduser", description="Add a user who can manage the bot")
async def slash_botadduser(interaction: discord.Interaction, user: discord.Member):
    author = interaction.user
    if not isinstance(author, discord.Member) or not can_manage_bot(author):
        return await interaction.response.send_message(
            "❌ You are not allowed to change bot permissions.",
            ephemeral=True
        )

    if user.id not in config["bot_managers_users"]:
        config["bot_managers_users"].append(user.id)
        save_config()

    await interaction.response.send_message(
        f"✅ {user.mention} can now manage the bot."
    )


@bot.tree.command(name="botremoveuser", description="Remove a user from bot managers")
async def slash_botremoveuser(interaction: discord.Interaction, user: discord.Member):
    author = interaction.user
    if not isinstance(author, discord.Member) or not can_manage_bot(author):
        return await interaction.response.send_message(
            "❌ You are not allowed to change bot permissions.",
            ephemeral=True
        )

    if user.id in config["bot_managers_users"]:
        config["bot_managers_users"].remove(user.id)
        save_config()

    await interaction.response.send_message(
        f"🗑️ {user.mention} is no longer a bot manager."
    )


@bot.tree.command(name="botmanagers", description="Show who can manage the bot")
async def slash_botmanagers(interaction: discord.Interaction):
    if not isinstance(interaction.user, discord.Member) or not can_manage_bot(interaction.user):
        return await interaction.response.send_message(
            "❌ You are not allowed to view this.",
            ephemeral=True
        )

    guild = interaction.guild
    role_mentions = []
    user_mentions = []

    if guild:
        for role_id in config.get("bot_managers_roles", []):
            role = guild.get_role(role_id)
            if role:
                role_mentions.append(role.mention)

        for user_id in config.get("bot_managers_users", []):
            member = guild.get_member(user_id)
            if member:
                user_mentions.append(member.mention)

    text = "**Bot managers:**\n"
    text += f"**Roles:** {', '.join(role_mentions) if role_mentions else 'None'}\n"
    text += f"**Users:** {', '.join(user_mentions) if user_mentions else 'None'}\n"
    text += "\n(Server owner and admins always can manage the bot.)"

    await interaction.response.send_message(text, ephemeral=True)

# ==========================
#   HELP EMBED + /help
# ==========================

@bot.tree.command(name="help", description="Show the full help menu with categories")
async def slash_help(interaction: discord.Interaction):

    embed = discord.Embed(
        title="📘 Bot Help Menu",
        description="Here are all available commands categorized for easy use.",
        color=discord.Color.blue()
    )

    # --- General Commands ---
    embed.add_field(
        name="🔵 General",
        value=(
            "`/help` — Show this help menu\n"
            "`/info server` — Show server info\n"
            "`/info user @user` — Show user info\n"
            "`/info bot` — Show bot details\n"
            "`/rules` — Show server rules\n"
        ),
        inline=False
    )

    # --- Knowledge Commands ---
    embed.add_field(
        name="🧠 Knowledge System",
        value=(
            "`/ask question` — Ask the bot a question\n"
            "`/qa_list` — List all knowledge\n"
            "`/qa_search keyword` — Search Q&A\n"
            "**Admins/Managers Only:**\n"
            "`/qa_add question || answer` — Add new Q&A\n"
            "`!addqa question || answer` — Prefix version\n"
            "`!editqa index || new Q || new A` — Edit Q&A\n"
            "`!delqa index` — Delete Q&A\n"
        ),
        inline=False
    )

    # --- Moderation Commands ---
    embed.add_field(
        name="🛠 Moderation (Mod/Admin Only)",
        value=(
            "`/mod warn @user reason` — Warn user\n"
            "`/mod warnings @user` — Show warnings\n"
            "`/mod mute @user duration` — Mute user\n"
            "`/mod unmute @user` — Unmute user\n"
            "`/mod clear amount` — Bulk delete messages\n"
            "`/mod kick @user reason` — Kick user\n"
            "`/mod ban @user reason` — Ban user\n"
        ),
        inline=False
    )

    # --- Bot Manager Commands ---
    embed.add_field(
        name="🏛 Bot Manager Commands",
        value=(
            "`/botaddrole @role` — Allow role to manage the bot\n"
            "`/botremoverole @role` — Remove role manager power\n"
            "`/botadduser @user` — Make user bot manager\n"
            "`/botremoveuser @user` — Remove user manager power\n"
            "`/botmanagers` — Show bot managers\n"
        ),
        inline=False
    )

    # --- Info Commands ---
    embed.add_field(
        name="📊 Info Commands",
        value=(
            "`/info server` — Detailed server info\n"
            "`/info user @user` — User info panel\n"
            "`/info bot` — Bot uptime, ping, version\n"
        ),
        inline=False
    )

    # --- Automod Info ---
    embed.add_field(
        name="🛡 Auto-Mod / Anti-Spam (Automatic)",
        value=(
            "⚠ Bad words auto-deleted\n"
            "⚠ Message spam detection\n"
            "⚠ Repeated message blocking\n"
            "⚙ Configurable in settings section of bot\n"
        ),
        inline=False
    )

    # --- Settings / Config ---
    embed.add_field(
        name="⚙ Settings & Configuration",
        value=(
            "• Bot respects **Allowed Channels**\n"
            "• Bad words and spam settings configurable\n"
            "• Knowledge ranking increases accuracy over time\n"
            "• Bot managers selected with `/botaddrole` or `/botadduser`\n"
        ),
        inline=False
    )

    embed.set_footer(text="Bot Help Menu • Fully Automated System")

    await interaction.response.send_message(embed=embed, ephemeral=False)



# ==========================
#    START BOT
# ==========================


bot.run(DISCORD_TOKEN)

