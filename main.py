import random
import re
import asyncio
import json
from os import environ as env
from sys import exit
import logging

import websockets
from dotenv import load_dotenv
from misskey import Misskey

# 環境変数とか
load_dotenv()
misskey_domain = "chpk.kur0den.net"

# Misskey関係
mk = Misskey(misskey_domain, i=env["MISSKEY_TOKEN"])
mk_id = mk.i()["id"]
ws_url = f'wss://{misskey_domain}/streaming?i={env["MISSKEY_TOKEN"]}'

logging.basicConfig(
    format="%(asctime)s %(name)s - %(levelname)s: %(message)s",  # 出力のフォーマット
    datefmt="[%Y-%m-%dT%H:%M:%S%z]",  # 時間(asctime)のフォーマット
    level=logging.INFO,  # ここで出力するログレベルを設定できる
)
log = logging.getLogger("main")


async def runner():  # めいんのたすく
    while True:
        try:
            async with websockets.connect(ws_url) as ws:  # type: ignore  ##websocketに接続
                await ws.send(
                    json.dumps(
                        {
                            "type": "connect",
                            "body": {
                                "channel": "main",
                                "id": "1",
                            },  # mainチャンネルに接続
                        }
                    )
                )
                while True:
                    msg = json.loads(await ws.recv())
                    log.info(
                        "Websocket message received: %s, %s",
                        msg.get("type"),
                        msg["body"].get("type"),
                    )
                    if msg["body"].get("type") == "mention":  # メンション時に反応
                        # どのユーザーからのメンションかを表示
                        log.info(
                            'Mention received from "%s"(@%s@%s)',
                            msg["body"]["body"]["user"]["name"],
                            msg["body"]["body"]["user"]["username"],
                            msg["body"]["body"]["user"]["host"],
                        )
                        # botじゃないかを確認
                        if msg["body"]["body"]["user"]["isBot"]:
                            log.info("This is a mention from the bot. Ignoring...")
                            continue
                        note_id = msg["body"]["body"]["id"]
                        content = msg["body"]["body"]["text"]
                        # 正規表現を作成
                        pattern = r"(d[1-9][0-9]{0,4}|[1-9][0-9]{0,4}d[1-9][0-9]{0,4})"  # d100, 1d100のような形式にマッチ

                        match = re.search(pattern, content)
                        if match is None:
                            log.info("No match found in the message")
                            mk.notes_reactions_create(note_id=note_id, reaction="❌")
                            continue
                        else:
                            mk.notes_reactions_create(note_id=note_id, reaction="🎲")
                        # マッチした文字列を取得
                        input_dice = re.search(pattern, content).group()
                        # マッチした文字列を表示
                        log.info("Match found in the message: %s", input_dice)
                        # 入力された値の前半と後半を分ける
                        input_list = input_dice.split("d")
                        # ダイスの数が指定されていない場合は1を挿入
                        if input_list[0] == "":
                            input_list[0] = "1"

                        # ダイスの数と面数をint型に変換
                        input_list = list(map(int, input_list))

                        # 結果用のリストを作成
                        result = []
                        for i in range(input_list[0]):
                            rand_int = random.randint(1, input_list[1])
                            result.append(rand_int)

                        # 結果を出力
                        result_cut = False
                        result_len = len(result)
                        if len(result) > 10:
                            result = result[:10]
                            result_cut = True
                        result = f"({sum(result)}) < {result}"

                        if result_cut:
                            result = result[:-1] + ", ...]"
                        result += f" <{input_list[0]}d{input_list[1]}>"

                        if result_cut:
                            result += f"\n(The {result_len - 10} roll has been cut.)"

                        # 結果を表示
                        log.info("Result: %s", result)

                        user_name = msg["body"]["body"]["user"]["username"]
                        user_host = msg["body"]["body"]["user"]["host"]
                        if user_host is None:
                            text = f"@{user_name} {result}"
                        else:
                            text = f"@{user_name}@{user_host} {result}"

                        result = await asyncio.to_thread(
                            mk.notes_create, text=text, reply_id=note_id
                        )  # 結果を返信
                        # idを表示
                        log.info(
                            "Replied to the mention: %s", result["createdNote"]["id"]
                        )
        except (
            websockets.exceptions.ConnectionClosedError,
            websockets.exceptions.ConnectionClosedOK,
        ):
            log.warning("Connection closed. Reconnecting...")
            continue
        except KeyboardInterrupt:
            exit()


log.info("ready")
try:
    asyncio.run(runner())  # runner()を実行
except (asyncio.exceptions.CancelledError, KeyboardInterrupt):
    pass
