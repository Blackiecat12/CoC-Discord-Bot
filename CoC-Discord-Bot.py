# CoC Discord Bot. 
# Mainly created to improve API/Discord Bot knowledge. Improving python alongside.

# imports for coc scripts
import coc
import os

# imports for discord bot
from discord.ext import commands

# imports for data handling and gathering
import pandas as pd
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Login to CoC and init bot
load_dotenv()
client = coc.login(
    os.getenv("EMAIL"),
    os.getenv("PASS"),
    client=coc.EventsClient
)
bot = commands.Bot(command_prefix="?")

# Load Variables and Data Structures
save_file = os.path.dirname(os.path.realpath(__file__)) + "\PlayerData.xlsx"
# Dataframe Structure: Columns = PlayerTag. Index 0-23 = 24hr time. 24 = last update time
data = pd.read_excel(save_file)
clanTag = '#J9R8RR20'
memberTag = []
channel_id = 865440614643269644


# This function is called once when starting the program and updates the dataframe with members that
# have left or been added. It backs up the saved data before performing operations.
async def updateData():
    # backup
    backupData()
    # get member tags in clan
    for member in await client.get_members(clanTag):
        memberTag.append(member.tag)
    # remove left members
    for tag in data.columns:
        if tag not in memberTag:
            print(f'Need to Remove {tag}')
            data.drop([tag], axis=1, inplace=True)
    # add new members
    for tag in memberTag:
        if tag not in data.columns:
            data[tag] = [None] * 26
            print(f'Added {tag}')
    # prep clan and player updates
    client.add_clan_updates(clanTag)
    mem_list = await client.get_members(clanTag)
    for m in mem_list:
        client.add_player_updates(m.tag)
    # signal done
    print("Loaded PlayerTag updates")


# When pinged with a tag, it will check data to see when last updated. If not within 15min it will reupdate the tag
def ping(name):
    global data
    if isRecentlyUpdated(name):
        return
    time = datetime.now()
    # if not init
    if data.isnull().at[time.hour, name]:
        data.at[time.hour, name] = 0
    data.at[time.hour, name] += 1
    await saveData()


# When given name checks if update happened in last 15 min (true) or not (false)
def isRecentlyUpdated(name):
    time = datetime.now()
    # if null then never updated, update time and return true
    if data.isnull().at[24, name]:
        data.at[24, name] = time
        return False
    # parse time
    last_update = datetime.strptime(str(data.at[24, name]), '%Y-%m-%d %H:%M:%S.%f')
    # check if in last 15 min
    if last_update + timedelta(minutes=15) > time:
        return True
    # if not then set new update return false
    data.at[24, name] = time
    return False


# Saves Dataframe to file
async def saveData():
    data.to_excel(save_file, sheet_name='Player Ping Online')
    await bot.get_channel(channel_id).send("Saved Data")


# Backs data up
def backupData():
    data.to_excel(os.path.dirname(os.path.realpath(__file__)) + "\PlayerDataBackup.xlsx", sheet_name='yep')
    print("Backed up")


# This event handler detects when a player donates and pings tag
@client.event
@coc.PlayerEvents.donations()
async def playerDonated(oldMem, newMem):
    await bot.get_channel(channel_id).send(f'{newMem.tag}({newMem}) donated at {datetime.now()}')
    ping(newMem.tag)


# This event handler detects when player attacks and pings tag
@client.event
@coc.PlayerEvents.versus_trophies()
async def playerVersusAttack(oldMem, newMem):
    await bot.get_channel(channel_id).send(f'{newMem.tag}({newMem}) versus battle at {datetime.now()}')
    ping(newMem.tag)


# Removes tag and data when player leaves
@client.event
@coc.ClanEvents.member_leave()
async def playerLeave(member, clan):
    data.drop([member.tag], axis=1, inplace=True)
    client.remove_player_updates(member)
    await bot.get_channel(channel_id).send(f'Removed {member.tag}({member})')


# When player joins while running
@client.event
@coc.ClanEvents.member_join()
async def playerJoin(member, clan):
    data[member.tag] = []
    client.add_player_updates(member)
    await bot.get_channel(channel_id).send(f'Added {member.tag}({member})')


# Bot commands 

@bot.command(name="listp", help='Lists updating player tags')
async def list_tags(ctx):
    await ctx.send(memberTag)


@bot.command(name='data', help="Returns data of given tag")
async def print_data(ctx, tag):
    await ctx.send(data[tag])


@bot.command(name='save', help='Saves current data')
async def savecmd():
    await saveData()


@bot.command(name='pinfo', help='Returns player info from tag')
async def pinfo(ctx, tag):
    await bot.get_channel(channel_id).send(await client.get_player(tag))


@bot.command(name='tagof', help='Gets tag of name from clan')
async def ptag(ctx, input_name):
    for member in await client.get_members(clanTag):
        if member.name == input_name:
            await bot.get_channel(channel_id).send(member.tag)


# Run scripts and bot
# client.loop.run_forever()
client.loop.run_until_complete(updateData())
bot.run(os.getenv("DISCORD_TOKEN"))
