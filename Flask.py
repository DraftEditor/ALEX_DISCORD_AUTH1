# -*- coding: utf-8 -*-
from flask import Flask, jsonify, request, render_template
import requests, sqlite3, traceback, configparser
import os

app = Flask(__name__)
port = 5000

config_ini = configparser.ConfigParser()
config_ini.read('config.ini', encoding='utf-8')

dbname = config_ini['setting']['dbname']
client_id = config_ini['setting']['client_id']
client_secret = config_ini['setting']['client_secret']
callback_url = "https://discordauthbot1.okokoziro.repl.co/auth?code=wCiIdKR3Pn4ew5UCosuGU7UxPgV5eI&state=1030869207010783232"
botToken = config_ini['setting']['DISCORD_BOT_TOKEN']
APIKEY = config_ini['setting']['APIKEY']


@app.route('/auth')
def callback():
  try:
    app.logger.debug('get')
    guildid = request.args.get("state")
    authorization_code = request.args.get("code")
    if guildid == None or authorization_code == None:
      return jsonify({'Error': 'Bad Request'}), 400

    user_ip = request.remote_addr
    conn = sqlite3.connect(dbname, isolation_level=None)
    cur = conn.cursor()

    black_ip = [
      blacklist_data
      for blacklist_data in cur.execute(f"SELECT * FROM blacklist")
      if blacklist_data[1] == user_ip
    ]
    if black_ip:
      return render_template('BLACKLIST.html', title='Black Listed.'), 403

    ip_check = requests.get(
      f'https://proxycheck.io/v2/{user_ip}?key={APIKEY}?vpn=1&asn=1')
    if ip_check.json()[user_ip]['proxy'] == "yes":
      return render_template('VPN.html', title='VPN Detected.'), 403

    request_postdata = {
      'client_id': client_id,
      'client_secret': client_secret,
      'grant_type': 'authorization_code',
      'code': authorization_code,
      'redirect_uri': callback_url
    }

    res = requests.post('https://discord.com/api/oauth2/token',
                        data=request_postdata)
    if res.status_code == 200:
      access_token = res.json()['access_token']
      refresh_token = res.json()['refresh_token']
    else:
      return render_template('NG.html', title='Verify Failed.')

    header = {"Authorization": "Bearer " + access_token}
    res = requests.get('https://discordapp.com/api/users/@me', headers=header)
    if res.status_code == 200:
      icon_url = f"https://cdn.discordapp.com/avatars/{res.json()['id']}/{res.json()['avatar']}.webp?size=128"
      userid = res.json()['id']
    else:
      return render_template('NG.html', title='Verify Failed.')

    server_info = [
      server_info for server_info in cur.execute(
        f"SELECT * FROM server_info WHERE serverid = {guildid}")
    ]

    json_data = {'access_token': f'{access_token}'}

    headers = {
      "Authorization": f"Bot {botToken}",
      'Content-Type': 'application/json'
    }

    requests.put(
      f'https://discordapp.com/api/guilds/{guildid}/members/{userid}/roles/{server_info[0][1]}',
      headers=headers,
      json=json_data)
    cur.execute(
      "REPLACE INTO users(userid, access_token, refresh_token, ipaddress) VALUES(?, ?, ?, ?)",
      [userid, access_token, refresh_token, user_ip])
    conn.close()

    return render_template('OK.html', title='Complete', todos=icon_url)
  except Exception as e:
    print(traceback.format_exc())


if __name__ == "__main__":
  app.run(host='0.0.0.0')
