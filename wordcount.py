# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import errno
import os
import sys
import tempfile
from argparse import ArgumentParser
import re
import math
import unicodedata
import string
from langdetect import detect

from flask import Flask, request, abort

from linebot import (
    LineBotApi, WebhookHandler
)
from linebot.exceptions import (
    InvalidSignatureError
)
from linebot.models import (
    MessageEvent, TextMessage, TextSendMessage,
    SourceUser, SourceGroup, SourceRoom,
    TemplateSendMessage, ConfirmTemplate, MessageTemplateAction,
    ButtonsTemplate, URITemplateAction, PostbackTemplateAction,
    CarouselTemplate, CarouselColumn, PostbackEvent,
    StickerMessage, StickerSendMessage, LocationMessage, LocationSendMessage,
    ImageMessage, VideoMessage, AudioMessage,
    UnfollowEvent, FollowEvent, JoinEvent, LeaveEvent, BeaconEvent
)

app = Flask(__name__)

# get channel_secret and channel_access_token from your environment variable
channel_secret = "LINE_BOT_CHANNEL_SECRET"
channel_access_token = "LINE_BOT_ACCESS_TOKEN"
if channel_secret is None:
    print('Specify LINE_CHANNEL_SECRET as environment variable.')
    sys.exit(1)
if channel_access_token is None:
    print('Specify LINE_CHANNEL_ACCESS_TOKEN as environment variable.')
    sys.exit(1)

line_bot_api = LineBotApi(channel_access_token)
handler = WebhookHandler(channel_secret)

static_tmp_path = os.path.join(os.path.dirname(__file__), 'static', 'tmp')


def make_static_tmp_dir():
    try:
        os.makedirs(static_tmp_path)
    except OSError as exc:
        if exc.errno == errno.EEXIST and os.path.isdir(static_tmp_path):
            pass
        else:
            raise


@app.route("/callback", methods=['POST'])
def callback():
    # get X-Line-Signature header value
    signature = request.headers['X-Line-Signature']

    # get request body as text
    body = request.get_data(as_text=True)
    app.logger.info("Request body: " + body)

    # handle webhook body
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)

    return 'OK'


@handler.add(MessageEvent, message=TextMessage)
def handle_text_message(event):
    text = event.message.text.lstrip()
    match = "使い方使いかたつかいかたhelpHelpへるぷヘルプルールるーる"

    if match.count(text) > 0:
        text = "使い方表示します。\nこのチャット欄へ文字を送信すると、その文字数をカウントし返信します。\nまた同時に原稿用紙へ単純に記述した場合とおおよそのルールに従って書いた場合の、枚数と行数を返信します。\n\n（ルールとは）\nプログラムの判定により、改行と行の始めに 」』）>。、 の記号がある場合（本来は前行の終わりに記述する）の書き方のこと。\n\n（注意）\nプログラムの自動判定のため、枚数、行数などが正確でない場合があります。目安としてご使用いただければ幸いです。"
        line_bot_api.reply_message(
            event.reply_token,
            TextMessage(text=text))

    if isinstance(event.source, SourceUser):
        if not(is_japanese(text)):
            profile = line_bot_api.get_profile(event.source.user_id)
            line_bot_api.reply_message(
                event.reply_token,
                TextMessage(text=profile.display_name + en_complete(text)))

        else:
            profile = line_bot_api.get_profile(event.source.user_id)
            line_bot_api.reply_message(
                event.reply_token,
                TextMessage(text=profile.display_name + jp_complete(text)))

    else:

        if not(is_japanese(text)):
            line_bot_api.reply_message(
                event.reply_token,
                TextMessage(text="みな" + en_complete(text)))

        else:
            line_bot_api.reply_message(
                event.reply_token,
                TextMessage(text="みな" + jp_complete(text)))


@handler.add(FollowEvent)
def handle_follow(event):
    line_bot_api.reply_message(
        event.reply_token, TextMessage(
            text="こんにちは、あなたから送られてきたメッセージの文字数をカウントします！\n"))


@handler.add(JoinEvent)
def handle_join(event):
    line_bot_api.reply_message(
        event.reply_token, TextMessage(
            text="こんにちは、みなさんから送られてきたメッセージの文字数をカウントします！\n"))

def jp_complete(words):
    wordsCount = jp_simple_counter(words)
    return "さんから送られた文章の文字数は\n" + str(wordsCount) + "文字です。\n400字詰め原稿用紙に単純に書いた場合は、\n約 " + jp_counter(wordsCount / 20) + "になります。\nルールに則って書いた場合は、\n約 " + jp_counter_op(words) + "になります。"

def jp_simple_counter(words):
    return len(words) - len(re.findall("\n|\s|\t",words))

def jp_counter(line):
    reply = ""
    if line / 20 < 1:
        reply = str(math.ceil(line % 20)) + "行"
    elif (line % 20) > 0:
        reply = str(math.floor(line / 20)) + "枚と " + str(math.ceil(line % 20)) + "行"
    else:
        reply = str(line) + "枚"

    return reply

def jp_counter_op(words):
    match = "」』）>。、"
    words += "\0"
    w = 0
    c = 1
    line = 0
    while (words[w] != "\0"):
        if words[w] == "\n":
            line += 1
            c = 0
        elif match.count(words[w]) > 0 and c == 0:
            pass
        elif c == 20:
            line += 1
            c = 0
        else:
            c += 1

        w += 1

    if c > 0:
        line += 1

    return jp_counter(line)

def en_complete(words):
    return "さんから送られた英文章のワード数は\n" + str(en_counter(words)) + "word(s)です。"

def en_counter(words):
    text = list(filter(lambda w: len(w) > 0, re.split(r'\s|"|,|\.', words)))
    return len(text)

def is_japanese(words):
    if detect(words) == "ja" or detect(words) == "ko":
        return True
    else:
        return False


if __name__ == "__main__":
    arg_parser = ArgumentParser(
        usage='Usage: python ' + __file__ + ' [--port <port>] [--help]'
    )
    arg_parser.add_argument('-p', '--port', default=5001, help='port')
    arg_parser.add_argument('-d', '--debug', default=False, help='debug')
    options = arg_parser.parse_args()

    # create tmp dir for download content
    make_static_tmp_dir()

    context = ("/path/to/fullchain.pem",
               "/path/to/privkey.pem")
    app.run(host="IP_ADDRESS", debug=options.debug,
            port=options.port, ssl_context=context)
