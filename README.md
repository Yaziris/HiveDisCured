# HiveDisCured
A Discord bot for Hive blockchain tokenized curation governance projects.


## Description:
This discord bot is for Hive blockchain curation project owners who want to allow curators to vote on posts using their curation account based on an amount of a specified token held. The higher the stake the bigger vote value they'd have access to!

The bot creates a role that auto assigns to qualified members in the server who have linked their Hive account with their Discord user, and it creates a private channel that it listens to, where eligible curators can drop the links posts they want curated by the curation project's account.

## How to setup and run the bot:
1- Create a Discord Application from https://discord.com/developers/applications/ and give it whatever name, description, and profile image you prefer.
- In the "Installation" tab, remove "user install" and add "bot" in the "guild install" "scope" dropdown menu.
- Add the following permissions in the "permissions" dropdown menu:
  - View Channels
  - Read Messages
  - Send Messages
  - Read Message History
  - Embed Links
  - Manage Roles
  - Manage Channels
- In the "Bot" tab, enable the "Privileged Gateway Intents" by toggeling all three of them on.
- Lastly, click the "Reset Token" button in that "Bot" tab, **copy and save that Bot Token for deployment later**.
- Back to the "Installation" tab, use the Discord provided installation link to invite the bot account into your Discord server. (You can do this step before or after you deploy the App, it doesn't matter)

2- Build and deploy the app on your server!<br>
   Note: If you're deploying using docker, use <code>docker run -it</code> tag as it's required to input your configurations on the first run.

## Easy Deployment Configurations Setup:
Upon running the code for first time, it will ask for few inputs:
> Enter your Discord bot token:

- This is the Bot Token you copied and saved from Step 1.

> Enter your Discord server ID:

- You can get that by right clicking on your Discord server's icon and select "Copy Guild ID".

> Enter your Hive curation account name:
 
- The Hive account that will do the voting.

> Enter your curation account's posting key:

- The POSTING key for that account.

> Enter your Hive-Engine token symbol:

- The project's curation governance token symbol.

> Enter the minimum amount of tokens held for curator role:

- This is the minimum amount of the token held by members on their linked Hive account to grant them access to the private curation channel.

> Token increment held per 1% vote:

- This is the amount of the token needed per each 1% voting weight.

> Enter a tag to check for on posts (Leave blank for no tag requirement):

- A tag that is needed to have been used on posts dropped for curation.

> Allow voting comments? [Y/N]:

- Whether to allow voting on comments or restrict votes to main posts only.

> Allowed curation window in hours (Post must not be older than that many hours):

- Default is 24 hours old posts, after which the posts won't be voted. You can input any amount of hours old.

## That's all!
Members can easily link their Hive account with their Discord user by using the bot's <code>/register</code> command.
