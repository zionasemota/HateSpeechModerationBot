from enum import Enum, auto
import discord
import re

report_flow = []
reports_to_moderate = []
users_reported = []
user_history = {}
curr_user = ""
user_comm = ""
# user name to total reports, total confirmed reports

class State(Enum):
    REPORT_START = auto()
    AWAITING_MESSAGE = auto()
    MESSAGE_IDENTIFIED = auto()
    AWAITING_SPAM_TYPE = auto()
    AWAITING_OFF_TYPE = auto()
    AWAITING_HATE_TYPE = auto()
    AWAITING_HAR_TYPE = auto()
    AWAITING_IMM_TYPE = auto()
    REPORT_COMPLETE = auto()
    AWAITING_MOD_PASS = auto()
    AWAITING_MOD_RESPONSE = auto()
    AWAITING_MOD_ABUSE_TYPE = auto()
    MOD_VIOLATION = auto()
    MOD_OFF_TYPE = auto()
    MOD_ASK_VIOLATION = auto()
    MOD_HATE_TYPE = auto()
    MOD_OPTIONS = auto()
    MOD_VIOLATION2 = auto()
    MOD_INVALID = auto()
    USER_ASK_COMM = auto()
    USER_INPUT_COMM = auto()
    ASK_BLOCK = auto()
    THANK_MOD = auto()

class Report:
    START_KEYWORD = "report"
    CANCEL_KEYWORD = "cancel"
    HELP_KEYWORD = "help"
    MOD_KEYWORD = "moderator"

    def __init__(self, client):
        self.state = State.REPORT_START
        self.client = client
        self.message = None
        self.reporter_name = None

    async def handle_message(self, message):
        global user_comm
        if message.content == self.MOD_KEYWORD:
            self.state = State.AWAITING_MOD_PASS
            return ["Please enter the moderator password to confirm you are a moderator"]
        
        if self.state == State.AWAITING_MOD_PASS:
            input_pass = message.content
            if input_pass == "Moderator1234":
                self.state = State.AWAITING_MOD_RESPONSE
                self.reporter_name = message.author.name
                return [f"Welcome moderator, there are `{len(reports_to_moderate)}` reports that require review, type `review` to review the highest priority report filed/flagged or `cancel` to cancel process"]
            else:
                self.state = State.REPORT_COMPLETE
                return ["Incorrect password, process canceled"]
        
        if self.state == State.AWAITING_MOD_RESPONSE:
            mod_response = message.content.lower()
            if mod_response == "review":
                # global curr_user
                # curr_user = users_reported.pop(0)
                self.state = State.AWAITING_MOD_ABUSE_TYPE
                return [f"`Begin report summary:`\n\n"
                        f"There are currently `{len(reports_to_moderate)}` pending reports. Here is the highest prioirity report filed/flagged of the `{len(reports_to_moderate)}` pending reports{reports_to_moderate.pop(0)}"]
            elif mod_response == "cancel":
                self.state = State.REPORT_COMPLETE
                return ["Process canceled"]
            else:
                return ["Invalid input. Please specify either `review` to review the highest priority report filed/flagged or `cancel` to cancel process"]
        
        if self.state == State.AWAITING_MOD_ABUSE_TYPE:
            mod_abuse_type = message.content.lower()
            already_popped = False
            if not already_popped:
                global curr_user
                curr_user = users_reported.pop(0)
            if mod_abuse_type == "spam":
                self.state = State.MOD_VIOLATION
                # global curr_user
                # curr_user = users_reported.pop(0)
                return [f"Here is the history of user `{curr_user}`: \n"
                        f"`{user_history[curr_user][0]}` total reports and `{user_history[curr_user][1]}` moderator confirmed reports \n\n"
                        f"Based on these numbers, does this user have a valid history of violations? (Yes or No)\nConsider that we automatically ban users after 3 violations."]
            elif mod_abuse_type == "hateful content":
                self.state = State.MOD_OFF_TYPE
                return ["What type of offense is this? (Hate Speech, Other)"]
            elif mod_abuse_type == "harassment":
                self.state = State.MOD_VIOLATION2
                return ["Explain the type of harassment indicated in the reported message"]
            elif mod_abuse_type == "imminent danger":
                self.state = State.THANK_MOD
                return ["Write message regarding report that will be sent to local authorities"]
            elif mod_abuse_type == "invalid report":
                self.state = State.MOD_INVALID
                return ["Suspend user who submitted invalid report or warn them? (Suspend, Warn)"]
            else:
                already_popped = True
                return ["Invalid input. Please classify above report (Spam, Hateful Content, Harassment, Imminent Danger, Invalid Report)"]
            
        if self.state == State.THANK_MOD:
            mod_mess = message.content.lower()
            self.state = State.REPORT_COMPLETE
            return [f"Thank you, the message `{mod_mess}` has been sent to authorities"]
        
        if self.state == State.MOD_INVALID:
            mod_inv = message.content.lower()
            if mod_inv == "suspend":
                self.state = State.REPORT_COMPLETE
                return [f"invalid reporter `{self.reporter_name}` has been suspended"]
            elif mod_inv == "warn":
                self.state = State.REPORT_COMPLETE
                return [f"invalid reporter `{self.reporter_name}` has been warned"]
            else:
                return ["Please specify valid action of either `Suspend` or `Warn`"]
       
        if self.state == State.MOD_OFF_TYPE:
            mod_off_type = message.content.lower()
            if mod_off_type == "hate speech":
                self.state = State.MOD_HATE_TYPE
                return ["Please specify type of `Hate Speech` (Racism, Homophobia, Sexism, Other)"]
            elif mod_off_type == "other":
                self.state = State.MOD_ASK_VIOLATION
                return ["Would you like to look at other violations? (Yes, No)"]
            else:
                return ["Invalid input. Either specify `Hate Speech` or `Other`"]
        
        if self.state == State.MOD_ASK_VIOLATION:
            mod_ask = message.content.lower()
            if mod_ask == "yes":
                self.state = State.MOD_VIOLATION2
                # curr_user = users_reported.pop(0)
                return [f"Here is the history of user `{curr_user}`: \n"
                        f"`{user_history[curr_user][0]}` total reports and `{user_history[curr_user][1]}` moderator confirmed reports \n\n"
                        f"Based on these numbers, does this user have a valid history of violations? (Yes or No)\nConsider that we automatically ban users after 3 violations."]
            elif mod_ask == "no":
                self.state = State.MOD_OPTIONS
                return ["Choose one of these three actions (Permanent user ban + add violator to blacklist, Warn user and temporarily suspend user, Watn user with no suspension)"]
            else: 
                return ["Invalid input. Please specify either `Yes` or `No`"]
        
        if self.state == State.MOD_HATE_TYPE:
            hate_type = message.content.lower()
            if hate_type in ["racism", "homophobia", "sexism", "other"]:
                if hate_type == "homophobia":
                    await message.channel.send(f"This article: `https://www.verywellmind.com/what-is-homophobia-5077409` has been sent to `{curr_user}` for them to reflect\n")
                self.state = State.MOD_ASK_VIOLATION
                return ["Would you like to look at other violations? (Yes, No)"]
            else:
                return ["Invalid input. Please specify valid type of `Hate Speech` (Racism, Homophobia, Sexism, Other)"]
        

        if self.state == State.MOD_VIOLATION2:
            mod_answer = message.content.lower()
            if mod_answer == "yes":
                user_history[curr_user][1] += 1
                self.state = State.REPORT_COMPLETE
                return [f"User `{curr_user}` has been permanently banned!"]
            elif mod_answer == "no":
                self.state = State.MOD_OPTIONS
                return ["Choose one of these three actions (Permanent user ban + add violator to blacklist, Warn user and temporarily suspend user, Warn user with no suspension)"]
            else:
                return ["Invalid input. Please specify either `Yes` or `No` based on if this user has a valid history of violations"]
        
        if self.state == State.MOD_OPTIONS:
            mod_choice = message.content.lower()
            if mod_choice == "permanent user ban + add violator to blacklist":
                user_history[curr_user][1] += 1
                self.state = State.REPORT_COMPLETE
                return [f"User `{curr_user}` has been permanently banned and blacklisted!"]
            elif mod_choice == "warn user and temporarily suspend user":
                user_history[curr_user][1] += 1
                self.state = State.REPORT_COMPLETE
                return [f"User `{curr_user} has been warned and temporarily suspended"]
            elif mod_choice == "warn user with no suspension":
                user_history[curr_user][1] += 1
                self.state = State.REPORT_COMPLETE
                return [f"User `{curr_user}` has been warned with no suspension"]
            else:
                return ["Invalid input. Please choose one of these three actions (Permanent user ban + add violator to blacklist, Warn user and temporarily suspend user, Warn user with no suspension)"]

        if self.state == State.MOD_VIOLATION:
            mod_answer = message.content.lower()
            if mod_answer == "yes":
                user_history[curr_user][1] += 1
                self.state = State.REPORT_COMPLETE
                return [f"User `{curr_user}` has been permanently banned!"]
            elif mod_answer == "no":
                user_history[curr_user][1] += 1
                self.state = State.REPORT_COMPLETE
                return [f"User `{curr_user}` has been temporarily banned and issued a warning"]
            else:
                return ["Invalid input. Please specify either `Yes` or `No` based on if this user has a valid history of violations"]

            

            
        if message.content == self.CANCEL_KEYWORD:
            self.state = State.REPORT_COMPLETE
            return ["Report cancelled."]

        if self.state == State.REPORT_START:
            global report_flow
            report_flow = []
            reply = ("Thank you for starting the reporting process. "
                     "Say `help` at any time for more information.\n\n"
                     "Please copy-paste the link to the message you want to report.\n"
                     "You can obtain this link by right-clicking the message and clicking `Copy Message Link`\n\n")
            self.reporter_name = message.author.name
            self.state = State.AWAITING_MESSAGE
            return [reply]

        if self.state == State.AWAITING_MESSAGE:
            # Parse the three ID strings from the message link
            m = re.search('/(\d+)/(\d+)/(\d+)', message.content)
            if not m:
                return ["I'm sorry, I couldn't read that link. Please try again or say `cancel` to cancel."]
            guild = self.client.get_guild(int(m.group(1)))
            if not guild:
                return ["I cannot accept reports of messages from guilds that I'm not in. Please have the guild owner add me to the guild and try again."]
            channel = guild.get_channel(int(m.group(2)))
            if not channel:
                return ["It seems this channel was deleted or never existed. Please try again or say `cancel` to cancel."]
            try:
                reported_message = await channel.fetch_message(int(m.group(3)))
            except discord.errors.NotFound:
                return ["It seems this message was deleted or never existed. Please try again or say `cancel` to cancel."]

            # Store the message reference and switch to MESSAGE_IDENTIFIED
            self.message = reported_message
            self.state = State.MESSAGE_IDENTIFIED
            return ["I found this message:", f"```{reported_message.author.name}: {reported_message.content}```",
                    "Please specify the abuse type (Spam, Hateful Content, Harassment, Imminent Danger)"]

        if self.state == State.MESSAGE_IDENTIFIED:
            abuse_type = message.content.lower()
            if abuse_type in ["spam", "hateful content", "harassment", "imminent danger"]:
                report_flow.append(abuse_type)
            if abuse_type == "spam":
                self.state = State.AWAITING_SPAM_TYPE  # Transition to awaiting spam type
                return ["Please specify the type of `Spam` (Fraud/Scam, Solicitation, Impersonation)"]
            elif abuse_type == "hateful content":
                self.state = State.AWAITING_OFF_TYPE
                return ["Please specify the type of `Hateful Content` (Hate Speech, Encouraging Hateful Content, Threatning Violence, Mocking Trauma)"]
            elif abuse_type == "harassment":
                self.state = State.AWAITING_HAR_TYPE
                return ["Pleas specify the type of `Harassment` (Sexually Explicit Content, Impersonation, Child Sexual Abuse Material)"]
            elif abuse_type == "imminent danger":
                self.state = State.AWAITING_IMM_TYPE
                return ["Please sepcify the type of `Imminent Danger` (Self-Harm, Suicide, Physical Abuse)"]
            else:
                return ["Invalid abuse type. Please specify a valid type (Spam, Hateful Content, Harassment, Imminent Danger)"]

        if self.state == State.AWAITING_IMM_TYPE:
            imm_type = message.content.lower()
            if imm_type in ["self-harm", "suicide", "physical abuse", "self harm"]:
                report_flow.append(imm_type)
                self.state = State.USER_ASK_COMM
                await message.channel.send("Please contact your local authorities if anybody is in immediate danger. We will also review the reported content.")
                return ["Thanks for reporting. Our team will review the messages and decide on appropriate action. Would you like to add any comments pertaining to this report? (Yes, No)"]
                #return await self.thank_user(message)
            else:
                return ["Invalid `Imminent Danger` type. Please specify a valid type (Self-Harm, Suicide, Physical Abuse)"]
            
        if self.state == State.AWAITING_HAR_TYPE:
            har_type = message.content.lower()
            if har_type in ["sexually explicit content", "impersonation", "child sexual abuse material"]:
                report_flow.append(har_type)
                self.state = State.USER_ASK_COMM
                return ["Thanks for reporting. Our team will review the messages and decide on appropriate action. Would you like to add any comments pertaining to this report? (Yes, No)"]
                #return await self.thank_user(message)
            else:
                return ["Invalid `Harassment` type. Please specify a valid type (Sexually Explicit Content, Impersonation, Child Sexual Abuse Material)"]

        if self.state == State.AWAITING_OFF_TYPE:
            off_type = message.content.lower()
            if off_type in ["encouraging hateful content", "threatening violence", "mocking trauma"]:
                report_flow.append(off_type)
                self.state = State.USER_ASK_COMM
                return ["Thanks for reporting. Our team will review the messages and decide on appropriate action. Would you like to add any comments pertaining to this report? (Yes, No)"]
                #return await self.thank_user(message)
            elif off_type == "hate speech":
                report_flow.append("hate speech")
                self.state = State.AWAITING_HATE_TYPE
                return ["Please specify the type of `Hate Speech` (Racism, Homophobia, Sexism, Other)"]
            else:
                return ["Invalid `Hateful Content` type. Please specify a valid type (Hate Speech, Sexually Explicit Content, Impersonation, Child Sexual Abuse Material, Advocating or Glorifying Violence)"]
        
        if self.state == State.AWAITING_HATE_TYPE:
            hate_type = message.content.lower()
            if hate_type in ["racism", "homophobia", "sexism", "other"]:
                report_flow.append(hate_type)
                self.state = State.USER_ASK_COMM
                return ["Thanks for reporting. Our team will review the messages and decide on appropriate action. Would you like to add any comments pertaining to this report? (Yes, No)"]
                #return await self.thank_user(message)
            else:
                return ["Please specify a valid `Hate Speech` type (Racism, Homophobia, Sexism, Other)"]
            

        if self.state == State.AWAITING_SPAM_TYPE:
            spam_type = message.content.lower()
            if spam_type in ["fraud/scam", "solicitation", "impersonation", "fraud", "scam"]:
                report_flow.append(spam_type)
                self.state = State.USER_ASK_COMM
                return ["Thanks for reporting. Our team will review the messages and decide on appropriate action. Would you like to add any comments pertaining to this report? (Yes, No)"]
                #return await self.thank_user(message)
            else:
                return ["Please specify a valid `Spam` type (Fraud/Scam, Solicitation, Impersonation)."]




        if self.state == State.USER_ASK_COMM:
            user_com_ans = message.content.lower()
            if user_com_ans == "yes":
                self.state = State.USER_INPUT_COMM
                return ["Please enter your comment below"]
            elif user_com_ans == "no":
                user_comm = ""
                self.state = State.ASK_BLOCK
                return [f"Would you like to block user `{self.message.author.name}` (Yes, No)"]
            else:
                return ["Invalid input. Please specify either `Yes` or `No` depending on if you'd like to add a comment"]
        
        if self.state == State.USER_INPUT_COMM:
            user_comm = message.content
            self.state = State.ASK_BLOCK
            return [f"Your comment has been recorded. Would you like to block user `{self.message.author.name}` (Yes, No)"]

        if self.state == State.ASK_BLOCK:
            user_block = message.content.lower()
            if user_block == "yes":
                self.state = State.REPORT_COMPLETE
                await self.send_report_to_moderator(user_comm)
                return [f"User `{self.message.author.name}` is blocked! Report process terminated"]
            elif user_block == "no":
                self.state = State.REPORT_COMPLETE
                await self.send_report_to_moderator(user_comm)
                return ["Report process terminated"]
            else:
                return [f"Invalid input. Please specify eith `Yes` if you would like user {curr_user} blocked or `No` if not"]



    async def send_report_to_moderator(self, comment):
        """
        Send the completed report to the corresponding moderator channel.
        """
        #guild_id = self.message.guild.id
        #mod_channel = self.client.mod_channels.get(guild_id)


        original_message = f"{self.message.author.name}: {self.message.content}"
        user_flow = ""
        type = ""
        for i, elem in enumerate(report_flow):
            if i == 0:
                type = elem
            if i == len(report_flow) - 1:
                user_flow += elem[0].upper() + elem[1:]
            else:
                user_flow += (elem[0].upper() + elem[1:] + " -> ")

        if self.message.author.name not in user_history:
            user_history[self.message.author.name] = [1, 0]
        else:
            user_history[self.message.author.name][0] += 1

        if len(comment) > 0:
            report_message = (
                f", initiated by user: `{self.reporter_name}`\n\n"
                f"Reported Message:\n```{original_message}```\n"
                f"User Report Flow: `{user_flow}`\n"
                f"User `{self.reporter_name}` left this comment regarding report: `{comment}`\n\n"
                f"`End report summary.`\n\n"
                f"Moderator, please classify above report (Spam, Hateful Content, Harassment, Imminent Danger, Invalid Report)"
            )
        else:
            report_message = (
                f", initiated by user: `{self.reporter_name}`\n\n"
                f"Reported Message:\n```{original_message}```\n"
                f"User Report Flow: `{user_flow}`\n"
                f"User `{self.reporter_name}` left no comments regarding report\n\n"
                f"`End report summary.`\n\n"
                f"Moderator, please classify above report (Spam, Hateful Content, Harassment, Imminent Danger, Invalid Report)"
            )
        if type.lower() == "imminent danger":
            reports_to_moderate.insert(0, report_message)
            users_reported.insert(0, self.message.author.name)
        else:
            users_reported.append(self.message.author.name)
            reports_to_moderate.append(report_message)
        #reports_to_moderate.append(report_message)
        #users_reported.append(self.message.author.name)
        #await mod_channel.send(report_message)


    # async def thank_user(self, message):
    #     if self.state == State.AWAITING_IMM_TYPE:
    #         await message.channel.send("Please contact your local authorities if anybody is in immediate danger. We will also review the reported content.")
    #     self.state = State.USER_ASK_COMM
    #     return ["Thanks for reporting. Our team will review the messages and decide on appropriate action. Would you like to add any comments pertaining to this report? (Yes, No)"]

        

    #     self.state = State.REPORT_COMPLETE

    #     await self.send_report_to_moderator()

        #return ["Thanks for reporting. Our team will review the messages and decide on appropriate action. Would you like to add any comments pertaining to this report? (Yes, No)"]


    def report_complete(self):
        return self.state == State.REPORT_COMPLETE
