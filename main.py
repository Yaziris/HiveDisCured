__version__ = '1.0.0'

import asyncio
import discord
import json
import logging


from discord.ext import commands


description = """
A Discord bot for Hive blockchain tokenized curation governance projects.
"""


discord.utils.setup_logging(level=logging.INFO, root=True)
logger = logging.getLogger("Bot")



class HiveDisCured(commands.Bot):
    def __init__(self, config: dict):
        intents = discord.Intents.all()
        super().__init__(
            command_prefix="",
            description=description,
            intents=intents,
            help_command=None,
            case_insensitive=True
        )
        self.guild_id = config.get("GUILD_ID", 0)
        self.role_id = config.get("ROLE_ID", 0)
        self.chan_id = config.get("CHAN_ID", 0)
        self.blacklist = []
        self.db = {}
        self.config = config
        self.color = discord.Colour.dark_gold()



    async def startup(self):
        await self.wait_until_ready()
        logger.info("--------------------")
        for g in self.guilds:
            if g.id != self.guild_id:
                logger.error(f"Server ID mismatch! Leaving the server: {g.name}")
                await g.leave()
        guild = self.get_guild(self.guild_id)
        if guild:
            await self._setguild(guild)



    async def setup_hook(self):
        self.app_info = await self.application_info()
        # Initiate Cogs
        for extension in ("cogs.commands",):
            try:
                await self.load_extension(extension)
            except Exception as e:
                logger.exception(f'Failed to load {extension}\nError: {e}')
        # Startup Tasks
        self.loop.create_task(self.startup())



    async def on_message(self, message: discord.Message) -> None:
        if message.guild is None or message.channel.id != self.chan_id:
            return
        if message.guild.get_role(self.role_id) not in message.author.roles or not message.content.startswith("https://peakd.com/"):
            return
        self.loop.create_task(self.get_cog('Commands').curate(message))
        


    async def on_guild_join(self, guild: discord.Guild) -> None:
        await self._setguild(guild)



    async def on_guild_remove(self, guild: discord.Guild) -> None:
        if guild.id == self.guild_id:
            self.chan_id, self.role_id, self.config["CHAN_ID"], self.config["ROLE_ID"] = 0, 0, 0, 0
            with open("config.json", "w") as f:
                json.dump(self.config, f, indent=4)
            self.get_cog('Commands').token_holders.cancel()



    async def _setguild(self, guild: discord.Guild) -> None:
        if guild.id != self.guild_id:
            logger.error(f"Server ID mismatch! Leaving the server: {guild.name}")
            return await guild.leave()
        #Bot permissions check
        if not all([
            guild.me.guild_permissions.read_messages,
            guild.me.guild_permissions.send_messages,
            guild.me.guild_permissions.read_message_history,
            guild.me.guild_permissions.embed_links,
            guild.me.guild_permissions.manage_roles,
            guild.me.guild_permissions.manage_channels
        ]):
            logger.critical("Bot doesn't have the required permissions! Re-Invite the bot with the following permissions:\n- View Channels\n- Read Messages\n- Send Messages\n- Read Message History\n- Embed Links\n- Manage Roles\n- Manage Channels")
            return await guild.leave()
        #Setup role and channel to use
        if guild.get_role(self.role_id) is None:
            #create role
            role = await guild.create_role(name="Curator", color=self.color)
            self.role_id = role.id
            logger.info(f"Created role {role.name} in {guild.name}")
        else:
            logger.info(f"Using role {guild.get_role(self.role_id)}")
            
        if self.get_channel(self.chan_id) is None:
            #create private channel with permission overwrites
            permitted_role = guild.get_role(self.role_id)
            overwrites = {
                guild.default_role: discord.PermissionOverwrite(view_channel=False),
                permitted_role: discord.PermissionOverwrite(view_channel=True),
                guild.me: discord.PermissionOverwrite(view_channel=True)
            }
            chan = await guild.create_text_channel("👑curation-station", overwrites=overwrites, topic="Drop peakd links to the posts for curation!", slowmode_delay=21600)
            self.chan_id = chan.id
            logger.info(f"Created channel {chan.name} in {guild.name}")
        else:
            logger.info(f"Using Channel {self.get_channel(self.chan_id)}")
        
        if self.config.get("CHAN_ID", 0) != self.chan_id or self.config.get("ROLE_ID", 0) != self.role_id:
            self.config["CHAN_ID"] = self.chan_id
            self.config["ROLE_ID"] = self.role_id
            with open("config.json", "w") as f:
                json.dump(self.config, f, indent=4)
        # Load linked accounts
        try:
            with open("db.json", "r") as f:
                self.db = json.load(f)
        except FileNotFoundError:
            self.db = {}
        await self.tree.sync()
        self.get_cog('Commands').token_holders.start()



    async def start(self) -> None:
        await super().start(self.config["BOT_TOKEN"], reconnect=True)




            


async def configure():
    config = {}
    try:
        with open("config.json", "r") as f:
            config = json.load(f)
    except FileNotFoundError:
        logger.info("Config file not found. Creating a new one. Please fill in the required fields.")
        try:
            config = {
                "BOT_TOKEN": input("Enter your Discord bot token: "),
                "GUILD_ID": int(input("Enter your Discord server ID: ")),
                "ACC_NAME": input("Enter your Hive curation account name: ").strip(" @").lower(),
                "ACC_WIF": input("Enter your curation account's posting key: "),
                "TOKEN_NAME": input("Enter your Hive-Engine token symbol: ").upper(),
                "TOKEN_TYPE": "stake" if input("Staked or Liquid balance tokens? [S/L]: ").lower().startswith('s') else "balance",
                "MIN_TOKENS": float(input("Enter the minimum amount of tokens held for curator role: ")),
                "VOTE_PCT": float(input("Token increment held per 1% vote: ")),
                "POST_TAG": input("Enter a tag to check for on posts (Leave blank for no tag requirement): ").strip(" #").lower() or "None",
                "VOTE_COMMENTS": input("Allow voting comments? [Y/N]: ").lower().startswith('y'),
                "CUR_WINDOW": int(input("Allowed curation window in hours (Post must not be older than that many hours): ")) or 24,
                "CHAN_ID": 0,
                "ROLE_ID": 0
            }
        except ValueError:
            logger.error("Invalid input. Please try again.")
            return await configure()
        for v in config.values():
            if len(str(v)) < 1:
                logger.error("Invalid input. Please try again.")
                return await configure()
        with open("config.json", "w") as f:
            json.dump(config, f, indent=4)
        logger.info("Your configurations have been saved! You can change them later by editing the config.json file or deleting it to start over.")
    return config
    


async def main():
    # Populate config variables and run the bot
    config = await configure()
    async with HiveDisCured(config) as bot:
        await bot.start()




if __name__ == "__main__":
    asyncio.run(main())