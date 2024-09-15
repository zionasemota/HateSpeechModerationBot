# bot.py
import discord
from discord.ext import commands
import os
import json
import logging
import re
import requests
from report import Report
import pdb
from openai import OpenAI
from report import reports_to_moderate, users_reported, user_history

# Set up logging to the console
logger = logging.getLogger('discord')
logger.setLevel(logging.DEBUG)
handler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w')
handler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
logger.addHandler(handler)

# There should be a file called 'tokens.json' inside the same folder as this file
token_path = 'tokens.json'
if not os.path.isfile(token_path):
    raise Exception(f"{token_path} not found!")
with open(token_path) as f:
    # If you get an error here, it means your token is formatted incorrectly. Did you put it in quotes?
    tokens = json.load(f)
    discord_token = tokens['discord']
    openai_token = tokens['openai']

openai_client = OpenAI(api_key=openai_token)

class ModBot(discord.Client):
    def __init__(self): 
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(command_prefix='.', intents=intents)
        self.group_num = None
        self.mod_channels = {} # Map from guild to the mod channel id for that guild
        self.reports = {} # Map from user IDs to the state of their report

    async def on_ready(self):
        print(f'{self.user.name} has connected to Discord! It is these guilds:')
        for guild in self.guilds:
            print(f' - {guild.name}')
        print('Press Ctrl-C to quit.')

        # Parse the group number out of the bot's name
        match = re.search('[gG]roup (\d+) [bB]ot', self.user.name)
        if match:
            self.group_num = match.group(1)
        else:
            raise Exception("Group number not found in bot's name. Name format should be \"Group # Bot\".")

        # Find the mod channel in each guild that this bot should report to
        for guild in self.guilds:
            for channel in guild.text_channels:
                if channel.name == f'group-{self.group_num}-mod':
                    self.mod_channels[guild.id] = channel
                         

    async def on_message(self, message):
        '''
        This function is called whenever a message is sent in a channel that the bot can see (including DMs). 
        Currently the bot is configured to only handle messages that are sent over DMs or in your group's "group-#" channel. 
        '''
        # Ignore messages from the bot 
        if message.author.id == self.user.id:
            return

        # Check if this message was sent in a server ("guild") or if it's a DM
        if message.guild:
            await self.handle_channel_message(message)
        else:
            await self.handle_dm(message)

    async def handle_dm(self, message):
        # Handle a help message
        if message.content == Report.HELP_KEYWORD:
            reply =  "Use the `report` command to begin the reporting process.\n"
            reply += "Use the `cancel` command to cancel the report/moderation process.\n"
            reply += "Use the `moderator` command to begin the moderation process.\n"

            await message.channel.send(reply)
            return

        author_id = message.author.id
        responses = []

        # Only respond to messages if they're part of a reporting flow
        if author_id not in self.reports and not (message.content.startswith(Report.START_KEYWORD) or message.content.startswith(Report.MOD_KEYWORD)):
            return

        # If we don't currently have an active report for this user, add one
        if author_id not in self.reports:
            self.reports[author_id] = Report(self)

        # Let the report class handle this message; forward all the messages it returns to uss
        responses = await self.reports[author_id].handle_message(message)
        for r in responses:
            await message.channel.send(r)

        # If the report is complete or cancelled, remove it from our map
        if self.reports[author_id].report_complete():
            self.reports.pop(author_id)

    async def handle_channel_message(self, message):
        # Only handle messages sent in the "group-#" channel
        if not message.channel.name == f'group-{self.group_num}':
            return

        hate_percentage, type = await self.moderate_message(message.content)
        mod_channel = self.mod_channels[message.guild.id]
        if int(hate_percentage) > 50:
            mod_channel = self.mod_channels[message.guild.id]
            await mod_channel.send(f"**Moderation Alert**:\n`{message.author.name}: {message.content}`\nOffensive content liklihood score of: `{hate_percentage}`%\nType: `{type}`\n"
                                   f"**This message has been automatically sent for moderation**\n"
                                   f"-------------------------------------------------------------------------------------------------------------------\n")
            
            original_message = f"{message.author.name}: {message.content}"

            if message.author.name not in user_history:
                user_history[message.author.name] = [1, 0]
            else:
                user_history[message.author.name][0] += 1

            report_message = (
                f", flagged by moderation system\n\n"
                f"Flagged Message:\n```{original_message}```\n"
                f"Flagged message abuse type: `{type}`\n"
                f"Flagged message offensive liklihood score: `{hate_percentage}%`\n\n"
                f"`End report summary.`\n\n"
                f"Moderator, please classify above flagged message (Spam, Hateful Content, Harassment, Imminent Danger, Invalid Report)"
            )

            if type.lower() == "imminent danger":
                reports_to_moderate.insert(0, report_message)
                users_reported.insert(0, message.author.name)
            else:
                users_reported.append(message.author.name)
                reports_to_moderate.append(report_message)
        else:
            message_link = f"https://discord.com/channels/{message.guild.id}/{message.channel.id}/{message.id}"
            await mod_channel.send(f"The message: `{message.content}` from user `{message.author.name}` was not automatically"
                                   f" flagged\n\nIt has a calculated offensive content likelihood score of: `{hate_percentage}%`\n"
                                   f"In case this message should have been flagged and requires moderation, here is the message link to commence the report process:\n`{message_link}`\n"
                                   f"-------------------------------------------------------------------------------------------------------------------\n")
      
        # Forward the message to the mod channel
        # mod_channel = self.mod_channels[message.guild.id]
        # await mod_channel.send(f'Forwarded message:\n{message.author.name}: "{message.content}"')
        # scores = self.eval_text(message.content)
        # await mod_channel.send(self.code_format(scores))
    
    async def moderate_message(self, message_content):
        response = openai_client.chat.completions.create(
            messages=[
                {"role": "system", "content": "You will assist me in content moderation. To do this, I will provide unreviewed"
                 " messages from a chat and your only responses from here on out will be in the form of two strings with a space in between. "
                 "The first string will be a percentage based on how likely the inout message is to actually being problematic "
                 "in the sense that it requires further human moderation (with 0% meaning does not require any moderation and "
                 "is fine all the way to 100% meaning this is very problematic and requires immediate moderation). "
                 "The second string will be the type of harmful behavior which has to be one of: "
                 "Spam, Hateful Content, Harassment, or Imminent Danger. You must follow this exact specified format "
                 "for each output"},
                {"role": "user", "content": f"Message: {message_content}\nClassification:"}
            ],
            model="gpt-4o",
            max_tokens=10,
            n=1,
            stop=None,
            temperature=0.7
        )
        
        ans = response.choices[0].message.content.strip()
        space_idx = ans.find(" ")
        first = ans[: space_idx]
        sec = ans[space_idx + 1:]
        return first[: len(first) - 1], sec

    
    def eval_text(self, message):
        ''''
        TODO: Once you know how you want to evaluate messages in your channel, 
        insert your code here! This will primarily be used in Milestone 3. 
        '''
        return message

    
    def code_format(self, text):
        ''''
        TODO: Once you know how you want to show that a message has been 
        evaluated, insert your code here for formatting the string to be 
        shown in the mod channel. 
        '''
        return "Evaluated: '" + text+ "'"


client = ModBot()
client.run(discord_token)