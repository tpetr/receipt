import os
import logging
from datetime import datetime
from escpos.printer import Usb
import requests

import re

RE_LINK = re.compile(r"<[^@].*?\|(.*?)>")
RE_MENTION = re.compile(r"<@(U[^>]+)>")

logging.basicConfig(level=logging.DEBUG)



printer = Usb(0x04b8, 0x0e28)
channels = set(os.environ.get("RECEIPT_CHANNELS", "").split(","))

from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler

app = App(token=os.environ["RECEIPT_SLACK_TOKEN"])

users = {}


def get_user(user_id):
    if user_id not in users:
        users[user_id] = app.client.users_info(user=user_id).data["user"]
    return users[user_id]


def get_user_profile_pic(user, size=192):
    user_id = user['id']
    filename = f"users/{user_id}_{size}.jpg"
    if not os.path.exists(filename):
        with open(filename, "wb") as fp:
            fp.write(requests.get(user['profile'][f"image_{size}"]).content)
    return filename



@app.event("message")
def handle_message(event, say):
    match event:
        case {"text": text, "user": user_id, "channel": channel, "ts": ts} if channel in channels:
            if event.get("thread_ts"):
                return

            user = get_user(user_id)
            pic_path = get_user_profile_pic(user)

            printer.image(pic_path)
            printer.text(f"\n{user['real_name']}")
            if user["profile"]["title"]:
                printer.text(f", \"{user['profile']['title']}\"")
            printer.text("\n\n")
            printer.text(f"{datetime.fromtimestamp(float(ts)).strftime('%c')}\n\n")

            # replace <@USERID> with Real Name
            text = RE_MENTION.sub(lambda match: get_user(match.group(1)).get("real_name", "???"), text)

            printer.text(f"{text}\n\n")
            printer.cut()


SocketModeHandler(app, os.environ["RECEIPT_SLACK_SOCKET_TOKEN"]).start()
