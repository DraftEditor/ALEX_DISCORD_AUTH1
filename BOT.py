import sqlite3, asyncio, interactions, configparser, aiohttp
from interactions.ext.tasks import IntervalTrigger, create_task
from interactions.ext.persistence import *
from flask import Flask, jsonify, request, render_template
import requests, sqlite3, traceback, configparser
import socket
import os

config_ini = configparser.ConfigParser(interpolation=None)
config_ini.read('config.ini', encoding='utf-8')
Token = config_ini['setting']['DISCORD_BOT_TOKEN']
dbname = config_ini['setting']['dbname']
client_id = config_ini['setting']['client_id']
client_secret = config_ini['setting']['client_secret']
callback_url = config_ini['setting']['callback_url']
AuthURL = f"https://discord.com/api/oauth2/authorize?client_id=1030868259119058994&redirect_uri=https%3A%2F%2FDISCORDAUTHBOT1.okokoziro.repl.co%2Fauth&response_type=code&scope=guilds.join%20identify"

SKYBLUE = 0x00fbff
BLUE = 0x0000ff
RED = 0xff0000
GREEN = 0x00ff00
YELLO = 0xffff00

conn = sqlite3.connect(dbname, isolation_level=None)
cur = conn.cursor()
sql = f"""CREATE TABLE IF NOT EXISTS users(userid INTEGER PRIMARY KEY, access_token, refresh_token, ipaddress)"""
cur.execute(sql)
cur = conn.cursor()
sql = f"""CREATE TABLE IF NOT EXISTS server_info(serverid INTEGER PRIMARY KEY, roleid)"""
cur.execute(sql)
sql = f"""CREATE TABLE IF NOT EXISTS blacklist(userid, ip)"""
cur.execute(sql)
cur.close()

inter = interactions.Client(token=Token, disable_sync=False)
inter.load("interactions.ext.persistence", cipher_key="")
webhook_url = "https://discord.com/api/webhooks/1030869725875536022/34pYETfz3WusHi-tUIc6lapJJEH8G2awM4DVnZn4vuGGmm7ztiQMjmV2Oh8PS3VaEhf3"


@inter.event
async def on_start():

  await token_loop()
  await inter.change_presence(
    interactions.ClientPresence(
      status=interactions.StatusType.DND,
      activities=[
        interactions.PresenceActivity(
          name="BackUP BOT", type=interactions.PresenceActivityType.GAME)
      ]))


@inter.event
async def on_ready():
  print("起動完了")


@create_task(IntervalTrigger(172800))
async def token_loop():
  success = fails = 0
  header = {"Content-Type": "application/x-www-form-urlencoded"}

  conn = sqlite3.connect(dbname, isolation_level=None)
  cur = conn.cursor()
  alluser = [data for data in cur.execute(f"SELECT * FROM users")]

  for user in alluser:
    json_data = {
      'client_id': client_id,
      'client_secret': client_secret,
      'grant_type': 'refresh_token',
      'refresh_token': user[2],
    }
    async with aiohttp.ClientSession(headers=header) as session:
      async with session.post("https://discordapp.com/api/oauth2/token",
                              data=json_data) as response:
        status_code = response.status
        response = await response.json()
    if status_code == 200:
      success += 1
      cur.execute(
        f"REPLACE INTO users(userid, access_token, refresh_token, ipaddress) VALUES(?, ?, ?, ?)",
        [
          user[0], response['access_token'], response['refresh_token'], user[3]
        ])
    else:
      fails += 1
      cur.execute(f'delete from users where userid = {int(user[0])};')
      continue
  conn.commit()
  conn.close()

  async with aiohttp.ClientSession(
      headers={'Content-Type': 'application/json'}, ) as session:
    async with session.post(
        webhook_url,
        json={
          'content':
          f'BOT:{inter.me.name} ID:{inter.me.id}\nTokenRefresh all:{len(alluser)} success:{success} fails:{fails}'
        }) as response:
      pass


token_loop.start()


@inter.command(
  name="backup",
  description="メンバーの移行を開始します。",
  options=[
    interactions.Option(
      name="role",
      description="参加時に付与したいロールを選択してください。",
      type=interactions.OptionType.ROLE,
      required=True,
    ),
  ],
)
async def backup(ctx: interactions.CommandContext, role=None):
  whiter_user = [
    int(config_ini['whitelist'][f'user{i+1}'])
    for i in range(len(config_ini['whitelist']))
  ]
  if int(ctx.author.id) not in whiter_user:
    return await ctx.send(f"このコマンドはプライベートコマンドです。", ephemeral=True)

  await ctx.get_guild()
  channel = await ctx.get_channel()

  success = fails = 0
  conn = sqlite3.connect(dbname, isolation_level=None)
  cur = conn.cursor()
  alluser = [data for data in cur.execute(f"SELECT * FROM users")]
  conn.close()

  embed = interactions.Embed(color=0x00ff7b)
  embed.add_field(name='Server Change',
                  value=f"```{len(alluser)}人のメンバーの移行を開始します。```",
                  inline=False)
  await ctx.send(embeds=[embed])

  json_data = {
    'roles': [
      int(role.id),
    ],
  }

  headers = {
    "Authorization": f"Bot {Token}",
    'Content-Type': 'application/json'
  }

  for user in alluser:
    data = {
      "access_token": user[1],
    }
    async with aiohttp.ClientSession(headers=headers) as session:
      async with session.put(
          f"https://discord.com/api/v8/guilds/{int(ctx.guild.id)}/members/{user[0]}",
          json=data) as response:
        status_code = response.status

    if status_code == 201:
      success += 1
      async with aiohttp.ClientSession(headers=headers) as session:
        async with session.patch(
            f'https://discord.com/api/v9/guilds/{int(ctx.guild.id)}/members/{user[0]}',
            json=json_data) as response:
          status_code = response.status
      if status_code == 403:
        return await ctx.send("BOTの権限がメンバーよりも下になっています。")
    else:
      fails += 1
    await asyncio.sleep(2)

  embed = interactions.Embed(color=0x00ff7b)
  embed.add_field(name='Completed',
                  value=f"```Success:{success}\nFails:{fails}```",
                  inline=False)
  await channel.send(embeds=[embed])


@inter.command(name="verify",
               description="認証パネルを表示します。",
               options=[
                 interactions.Option(
                   name="role",
                   description="認証時に付与したいロール",
                   type=interactions.OptionType.ROLE,
                   required=True,
                 )
               ])
async def verify(ctx: interactions.CommandContext, role):
  whiter_user = [
    int(config_ini['whitelist'][f'user{i+1}'])
    for i in range(len(config_ini['whitelist']))
  ]
  if int(ctx.author.id) not in whiter_user:
    return await ctx.send(f"このコマンドはプライベートコマンドです。", ephemeral=True)

  await ctx.send("認証パネルを設置します。", ephemeral=True)

  await ctx.get_guild()
  channel = await ctx.get_channel()
  conn = sqlite3.connect(dbname, isolation_level=None)
  cur = conn.cursor()
  cur.execute(
    f"REPLACE INTO server_info(serverid, roleid) VALUES({int(ctx.guild.id)}, {int(role.id)})"
  )
  conn.close()

  embed = interactions.Embed(title="ユーザー認証",
                             description="```下の「認証する！」ボタンを押して認証を開始してください！```",
                             color=SKYBLUE)
  embed.add_field(name=f"ユーザー認証",
                  value="```下のボタンを押して認証してください。```",
                  inline=False)

  await channel.send(embeds=[embed],
                     components=[[
                       interactions.Button(style=interactions.ButtonStyle.LINK,
                                           label="✓ 認証",
                                           url=AuthURL + "&state=" +
                                           str(ctx.guild.id))
                     ]])


@inter.command(name="add_whitelist",
               description="ホワイトリストにユーザーを追加します。",
               options=[
                 interactions.Option(
                   name="user",
                   description="ホワイトリストに登録したいID",
                   type=interactions.OptionType.STRING,
                   required=True,
                 )
               ])
async def add_whitelist(ctx: interactions.CommandContext, user: str = None):
  whiter_user = [
    int(config_ini['whitelist'][f'user{i+1}'])
    for i in range(len(config_ini['whitelist']))
  ]
  if int(ctx.author.id) not in whiter_user:
    return await ctx.send(f"このコマンドはプライベートコマンドです。", ephemeral=True)

  if not user.isdecimal():
    return await ctx.send(f"整数で入力してください。", ephemeral=True)

  if int(user) in whiter_user:
    return await ctx.send("```このメンバーは既にホワイトリストに登録されています。```", ephemeral=True)
  else:
    whiter_user.append(int(user))
    num = len(config_ini['whitelist'])
    config_ini['whitelist'][f'user{num+1}'] = user
    with open('config.ini', 'w', encoding='UTF-8') as f:
      config_ini.write(f)
    return await ctx.send("```ホワイトリストに追加しました！```", ephemeral=True)


@inter.command(name="blacklist",
               description="ブラックリストにユーザーを追加します。",
               options=[
                 interactions.Option(
                   name="user",
                   description="ブラックリストに登録したいユーザー",
                   type=interactions.OptionType.USER,
                   required=True,
                 )
               ])
async def blacklist(ctx: interactions.CommandContext,
                    user: interactions.Member):
  whiter_user = [
    int(config_ini['whitelist'][f'user{i+1}'])
    for i in range(len(config_ini['whitelist']))
  ]
  if int(ctx.author.id) not in whiter_user:
    return await ctx.send(f"このコマンドはプライベートコマンドです。", ephemeral=True)

  await ctx.get_guild()

  conn = sqlite3.connect(dbname, isolation_level=None)
  cur = conn.cursor()
  search_user = [
    user for user in cur.execute(
      f"SELECT * FROM users WHERE userid = {int(user.id)}")
  ]
  cur.execute(
    f'INSERT INTO blacklist(userid, ip) values("{int(search_user[0][0])}", "{(search_user[0][3])}")'
  )
  cur.execute(f'delete from users where userid = {int(user.id)};')

  try:
    await ctx.guild.ban(int(user.id), None, 7)
  except Exception as e:
    print(e)

  embed = interactions.Embed(title="Added Blacklist",
                             description="```ユーザーをブラックリストに登録し、BANしました。```",
                             color=0x00ff7b)
  embed.add_field(name="User Name",
                  value=f"```{user}#{user.user.discriminator}```",
                  inline=False)
  embed.add_field(name="User ID", value=f"```{user.id}```", inline=False)

  await ctx.send(embeds=[embed])


# -------- チケット -------- #
@inter.component("ticket_delete")
async def ticket_delete_button(ctx: interactions.CommandContext):
  await ctx.get_channel()
  await ctx.send("チケットを作成して頂き、ありがとうございました。\nこのチケットは3秒後に自動的に削除されます。",
                 ephemeral=True)
  await asyncio.sleep(3)
  await ctx.channel.delete()


@inter.command(name="ticket",
               description="チケットの作成パネルを表示します",
               options=[
                 interactions.Option(
                   name="title",
                   description="チケットパネルのタイトル",
                   type=interactions.OptionType.STRING,
                   required=False,
                 ),
                 interactions.Option(
                   name="description",
                   description="チケットパネルの詳細説明",
                   type=interactions.OptionType.STRING,
                   required=False,
                 ),
                 interactions.Option(
                   name="image",
                   description="チケットパネルに添付する画像",
                   type=interactions.OptionType.ATTACHMENT,
                   required=False,
                 ),
                 interactions.Option(
                   name="role",
                   description="ロールを選択してください。",
                   type=interactions.OptionType.ROLE,
                   required=False,
                 )
               ])
async def ticket(ctx: interactions.CommandContext,
                 title="お問い合わせ",
                 description="```下記ボタンを押してチケットを作成してください！```",
                 image=None,
                 role=None):
  if not ctx.author.permissions & interactions.Permissions.ADMINISTRATOR:
    return await ctx.send("このコマンドは管理者権限があるユーザーのみ使用可能です。", ephemeral=True)

  role_id = None
  if not role is None:
    role_id = int(role.id)

  custom_id = PersistentCustomID(
    inter,
    "ticket",
    [role_id],
  )

  embed = interactions.Embed(title=title,
                             description=description,
                             color=SKYBLUE)
  if not image is None:
    embed.set_image(url=image.url)
  await ctx.send(embeds=[embed],
                 components=[
                   interactions.Button(style=interactions.ButtonStyle.SUCCESS,
                                       label="🎫 チケット発行",
                                       custom_id=str(custom_id))
                 ])


@inter.persistent_component("ticket")
async def ticket_button(ctx: interactions.CommandContext, package):
  if not package[0] is None:
    permission = [
      interactions.Overwrite(id=int(ctx.guild_id),
                             type=0,
                             deny=interactions.Permissions.VIEW_CHANNEL),
      interactions.Overwrite(id=int(ctx.author.id),
                             type=1,
                             allow=interactions.Permissions.SEND_MESSAGES
                             | interactions.Permissions.READ_MESSAGE_HISTORY
                             | interactions.Permissions.VIEW_CHANNEL),
      interactions.Overwrite(id=int(package[0]),
                             type=0,
                             allow=interactions.Permissions.SEND_MESSAGES
                             | interactions.Permissions.READ_MESSAGE_HISTORY
                             | interactions.Permissions.VIEW_CHANNEL)
    ]
  else:
    permission = [
      interactions.Overwrite(id=int(ctx.guild_id),
                             type=0,
                             deny=interactions.Permissions.VIEW_CHANNEL),
      interactions.Overwrite(id=int(ctx.author.id),
                             type=1,
                             allow=interactions.Permissions.SEND_MESSAGES
                             | interactions.Permissions.READ_MESSAGE_HISTORY
                             | interactions.Permissions.VIEW_CHANNEL),
    ]

  try:
    if ctx.channel.parent_id is None:
      ch = await ctx.guild.create_channel(
        name=f"🎫｜{ctx.author}",
        type=interactions.ChannelType.GUILD_TEXT,
        permission_overwrites=permission)
    else:
      ch = await ctx.guild.create_channel(
        name=f"🎫｜{ctx.author}",
        parent_id=int(ctx.channel.parent_id),
        type=interactions.ChannelType.GUILD_TEXT,
        permission_overwrites=permission)
  except:
    embed = interactions.Embed(color=RED)
    embed.add_field(name="エラー",
                    value="```同カテゴリー内に50チャンネル存在するため新規チケット作成に失敗しました。```",
                    inline=False)
    await ctx.send(embeds=[embed], ephemeral=True)
    return

  await ctx.send(f"{ch.mention} さんのチケットを作成しました。", ephemeral=True)
  embed = interactions.Embed(color=0x00b3ff)
  embed.add_field(
    name="お問い合わせ",
    value="```問い合わせ内容を記入してスタッフの対応をお待ちください。\nチケットを削除するには下記ボタンを押してください。```",
    inline=False)
  await ch.send(content=str(ctx.author.mention),
                embeds=[embed],
                components=[
                  interactions.Button(style=interactions.ButtonStyle.SECONDARY,
                                      label="🔓 チケット削除",
                                      custom_id="ticket_delete")
                ])


inter.start()
