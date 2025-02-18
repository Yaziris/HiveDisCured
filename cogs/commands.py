import asyncio
import base64
import json
from datetime import datetime, timedelta
from typing import Union

import discord
from discord.ext import commands, tasks
from discord import app_commands

from beem import Hive
from beem.account import Account
from beem.comment import Comment
from beem.transactionbuilder import TransactionBuilder
from beembase.operations import Vote



async def HiveAcc(name) -> object:
    try:
        acc = Account(name, blockchain_instance=Hive())
    except Exception:
        acc = {}
    return acc


class Button(discord.ui.Button):
    def __init__(
        self, ctx: Union[commands.Context, discord.Interaction],
        command, label: str, style: discord.ButtonStyle, emoji=None,
        disabled=False, custom_id=None, row: int=None
    ):
        super().__init__(
            label=label, style=style, disabled=disabled,
            emoji=emoji, row=row, custom_id=custom_id
        )
        self.invoker, self.command = ctx.author, command

    async def callback(self, interaction: discord.Interaction):
        if self.invoker == interaction.user:
            await self.command(interaction)
        else:
            await interaction.response.send_message("❌ Start your own session by calling one of the commands!", ephemeral=True)



class BotView(discord.ui.View):
    def __init__(self, ctx: Union[commands.Context, discord.Interaction], acc: HiveAcc, timeout=666):
        super().__init__(timeout=timeout)
        self.ctx = ctx
        self.acc = acc
        self.message = None
        self.embed = self.gen_embed()
        self.gen_buttons()



    def gen_embed(self) -> discord.Embed:
        embed = discord.Embed(color=self.ctx.bot.color, timestamp=discord.utils.utcnow())
        try:
            profurl = self.acc.posting_json_metadata.get("profile", {}).get("profile_image", self.ctx.guild.icon)
        except Exception:
            profurl = self.ctx.guild.icon
        embed.set_thumbnail(url=profurl)
        embed.set_footer(text=f"{self.ctx.bot.user.name} - Developed by @yaziris", icon_url=self.ctx.bot.user.display_avatar.url)
        embed.set_author(name=f"@{self.ctx.bot.user.name}", icon_url=profurl or self.ctx.guild.icon)
        return embed


    def gen_buttons(self) -> None:
        self.verifyB = Button(
            label="Verify ✅", command=self.verify, ctx=self.ctx,
            style=discord.ButtonStyle.blurple, disabled=False
        )
        self.verifiedB = Button(
            label="🔐 Verified", command=self.quit, ctx=self.ctx,
            style=discord.ButtonStyle.green, disabled=True
        )
        self.unverifiedB = Button(
            label="✖ Un-Verified", command=self.quit, ctx=self.ctx,
            style=discord.ButtonStyle.gray, disabled=True
        )
        self.cancelB = Button(
            label="Cancel ✖", command=self.quit, ctx=self.ctx,
            style=discord.ButtonStyle.red, disabled=False
        )


    async def on_timeout(self) -> None:
        for item in self.children:
            item.disabled = True
        if self.message:
            try:
                await self.message.edit(view=self)
            except Exception:
                pass


    async def quit(self, interaction: discord.Interaction):
        await interaction.response.defer()
        await interaction.delete_original_response()
        self.stop()


    async def verify_acc(self, memo: str) -> bool:
        stop_time = discord.utils.utcnow() - timedelta(minutes=10)
        for op in self.acc.history_reverse(stop=stop_time, use_block_num=False, only_ops=['transfer']):
            if op['to'] == self.ctx.bot.config['ACC_NAME'] and op['memo'] == memo:
                return True
        return False


    async def verify_tokens(self) -> bool:
        url = f"https://ac-validator.genesisleaguesports.com/players/{self.acc.name}/balances"
        resp = await self.ctx.bot.web_client.request("GET", url)
        if resp.status != 200:
            return False
        data = await resp.json()
        return any(
            tkn.get('token', ' ') == self.ctx.bot.config['TOKEN_NAME'] and
            float(tkn.get('balance', 0)) >= self.ctx.bot.config['MIN_TOKENS']
            for tkn in data
        )


    async def verify(self, interaction: discord.Interaction):
        self.verifyB.disabled = True
        self.cancelB.disabled = True
        self.embed.clear_fields()
        self.embed.title = ":hourglass: Verifying! Please wait..."
        await interaction.response.edit_message(embed=self.embed, view=self)
        self.clear_items()
        if await self.verify_acc(base64.b64encode(str(interaction.user.id).encode()).decode()):
            self.ctx.bot.db[str(interaction.user.id)] = self.acc.name
            with open("db.json", "w") as f:
                json.dump(self.ctx.bot.db, f, indent=4)
            self.embed.title = "✅ Verified!"
            self.embed.description = f"> **@{self.acc.name}** has been succesfully linked!\n\n"
            self.add_item(self.verifiedB)
            # check token amount to grant or remove the role
            role = interaction.guild.get_role(self.ctx.bot.role_id)
            if await self.verify_tokens():
                if role not in interaction.user.roles:
                    await interaction.user.add_roles(role)
                    self.embed.description += f"\n>>> You hold sufficient tokens amount of **{self.ctx.bot.config['TOKEN_NAME']}** and have been granted access to the <#{self.ctx.bot.chan_id}> channel!"
            else:
                if role in interaction.user.roles:
                    await interaction.user.remove_roles(role)
        else:
            self.embed.title = "\n\n ❌❌⛔ Unverified ⛔❌❌"
            self.embed.description = f"Couldn't link Hive account **@{self.acc.name}**. Make sure you already sent the transaction with the provided memo from it to **[@{self.ctx.bot.config['ACC_NAME']}](https://peakd.com/@{self.ctx.bot.config['ACC_NAME']})** then try registering again!"
            self.add_item(self.unverifiedB)
        await interaction.edit_original_response(embed=self.embed, view=self)
        return self.stop()


    async def link_acc(self, interaction: discord.Interaction):
        self.add_item(self.verifyB)
        self.add_item(self.cancelB)
        self.embed.add_field(
                name=f"🔐 To link @{self.acc.name} with your discord user:",
                value=f">>> Send a tiny amount of hive or hbd from @{self.acc.name}, to **[@{self.ctx.bot.config['ACC_NAME']}](https://peakd.com/@{self.ctx.bot.config['ACC_NAME']})** WITH ONLY the following in the memo:", inline=False)
        self.embed.add_field(
                name=base64.b64encode(str(interaction.user.id).encode()).decode(),
                value="\n>>> This is important to verify your authority over that Hive account.\n\nOnce you've sent the transaction, click the __**Verify**__ ✅ button, and your account will be linked.", inline=False)
        await interaction.response.send_message(embed=self.embed, view=self, ephemeral=True)
        self.message = await interaction.original_response()




class Commands(commands.Cog, name="Commands"):
    """The bot's commands"""
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.hive = Hive()


    async def cog_unload(self):
        self.token_holders.cancel()



    async def gen_embed(self) -> discord.Embed:
        embed = discord.Embed(color=self.bot.color, timestamp=discord.utils.utcnow())
        profurl = self.bot.get_guild(self.bot.guild_id).icon
        embed.set_thumbnail(url=profurl)
        embed.set_footer(text=f"{self.bot.user.name} - Developed by @yaziris", icon_url=self.bot.user.display_avatar.url)
        embed.set_author(name=self.bot.user.name, icon_url=self.bot.user.display_avatar.url)
        embed.title = "🟡"
        return embed



    async def curate(self, message: discord.Message):
        acc = self.bot.db.get(str(message.author.id), None)
        if not acc:
            return
        link = message.content.split()[0]
        embed = await self.gen_embed()
        try:
            author, permlink = link.split('@', 1)[1].split('/', 1)
            if '#@' in permlink:
                author, permlink = permlink.split('#@', 1)[1].split('/', 1)
            permlink = permlink.split('?', 1)[0]
            cmt = Comment(f"@{author}/{permlink}")
        except Exception:
            embed.title = "❌ Make sure it's a valid link to a post or comment!"
            embed.description = f"{link}"
            return await message.reply(embed=embed)
        if self.bot.config['POST_TAG'] != 'None' and self.bot.config['POST_TAG'] not in cmt.json_metadata.get('tags', []):
            embed.title = f"❌ The post doesn't have the #{self.bot.config['POST_TAG']} tag!"
            embed.description = f"{link}"
            return await message.reply(embed=embed)
        if cmt.get_vote_with_curation(voter=self.bot.config['ACC_NAME'], raw_data=True):
            embed.title = f"❌ The post has already been voted by {self.bot.config['ACC_NAME']}!"
            embed.description = f"{link}"
            return await message.reply(embed=embed)
        if not cmt.is_main_post() and not self.bot.config['VOTE_COMMENTS']:
            embed.title = "❌ **You're not allowed to vote comments per this server's curation settings!**"
            embed.description = f"{link}"
            return await message.reply(embed=embed)
        if cmt.time_elapsed() > timedelta(hours=self.bot.config['CUR_WINDOW']):
            embed.title = f"❌ **The post/comment is older than the __{self.bot.config['CUR_WINDOW']} Hours__ curation window allowed for voting per this server's curation settings!**"
            embed.description = f"{link}"
            return await message.reply(embed=embed)
        age = round(datetime.timestamp(cmt['created']))
        weight = await self.get_weight(acc)
        if weight <= 0:
            return
        # Vote the post
        tx = TransactionBuilder(blockchain_instance=self.hive)
        tx.appendOps(
            Vote(**{
                "voter": self.bot.config['ACC_NAME'],
                "author": author,
                "permlink": permlink,
                "weight": int(float(weight) * 100)
            })
        )
        if await self._broadcast_tx(tx):
            embed.title = ""
            embed.description = f":green_circle: **Voted __[{cmt.title}]({link})__** By: **__[@{author}](https://peakd.com/@{author})__** With **__{weight}__%**\n\n>>> Created On: <t:{age}:F> ~ <t:{age}:R>\nPending Reward Payout: **{cmt.reward}**\nPost URL: **{link}**"
            try:
                embed.set_thumbnail(url=cmt.json_metadata.get('image', cmt.json_metadata.get('images', [self.bot.get_guild(self.bot.guild_id).icon]))[0])
            except Exception:
                pass
        else:
            embed.title = "❌ Could not vote:"
            embed.description = f">>> {link}\n\nThis could be due to Hive nodes being down, or an invalid account/posting key. Maybe try again in a bit."
        await message.reply(embed=embed, mention_author=False)


    async def get_weight(self, acc: str) -> float:
        url = f"https://ac-validator.genesisleaguesports.com/players/{acc}/balances"
        resp = await self.bot.web_client.request("GET", url)
        if resp.status != 200:
            print(f"Failed to fetch balance data for {acc}, HTTP {resp.status}")
            return 0
        data = await resp.json()
        for tkn in data:
            if tkn.get('token', ' ') == self.bot.config['TOKEN_NAME']:
                balance = float(tkn.get('balance', 0))
                if balance >= self.bot.config['MIN_TOKENS']:
                    return max(min(round(balance / self.bot.config['VOTE_PCT'], 2), 100), 0)
        return 0


    async def _broadcast_tx(self, tx: TransactionBuilder | None=None) -> bool:
        if not tx:
            return False
        try:
            tx.appendWif(self.bot.config['ACC_WIF'])
            tx.sign()
            tx.broadcast()
        except Exception as e:
            print(e)
            return False
        return True



    async def get_holders(self) -> dict:
        holders = {}
        resp = await self.bot.web_client.request("GET", f"https://ac-validator.genesisleaguesports.com/tokens/{self.bot.config['TOKEN_NAME']}")
        async with resp:
            assert resp.status == 200
            holders.update({x['player']: float(x['balance']) for x in await resp.json() if float(x['balance']) >= self.bot.config['MIN_TOKENS']})
        return holders



    async def update_roles(self):
        permitted = await self.get_holders()
        guild = self.bot.get_guild(self.bot.guild_id)
        role = guild.get_role(self.bot.role_id)
        for k, v in self.bot.db.items():
            user = await guild.fetch_member(int(k))
            if v in permitted:
                if role not in user.roles:
                    await user.add_roles(role)
            else:
                if role in user.roles:
                    await user.remove_roles(role)
            await asyncio.sleep(2)


    @tasks.loop(hours=24.0)
    async def token_holders(self):
        try:
            await self.update_roles()
        except Exception as e:
            print(e)



    @app_commands.guild_only()
    @app_commands.command(name="register", description="Link a Hive account.")
    @app_commands.describe(account="The Hive account to link with your Discord user")
    async def register(self, interaction: discord.Interaction, account: str):
        acc = account.strip(" @").lower()
        if self.bot.db.get(str(interaction.user.id), '') == acc:
            return await interaction.response.send_message(f"**Your Discord user is already linked to the Hive account __@{acc}__! Enter a different account name and verify it if you want to re-link your Discord user with a different Hive account.**", ephemeral=True)
        if acc in self.bot.db.values():
            return await interaction.response.send_message(f"**The Hive account __@{acc}__ is already linked to a different user!**", ephemeral=True)
        hacc = await HiveAcc(account.strip(" @").lower())
        if not hacc:
            return await interaction.response.send_message(f"**The Hive account __@{acc}__ doesn't exist! Make sure you entered the correct account name.**", ephemeral=True)
        view = BotView(await commands.Context.from_interaction(interaction), hacc)
        return await view.link_acc(interaction)










async def setup(bot: commands.Bot):
    await bot.add_cog(Commands(bot))
