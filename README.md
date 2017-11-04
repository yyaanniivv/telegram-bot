# Magnet2Torrent Telegram Bot
### Doing:
Telegram bot which accepts magnet links and turns them into a `.torrent` files locally.

### Using:
* [Telepot](https://github.com/nickoala/telepot), the python telegram client library.


### Naive deploy
```
wget -O /tmp/master.zip https://github.com/yanivmichaelis/telegram-bot/archive/master.zip
unzip /tmp/master.zip -d ~/dev/
#cd ~/dev/telegram-bot-master

```
sudo pip3 install virtualenv
cd ~/dev
virtualenv telegram-bot-master
source bin/activate
pip install -r requirements.txt
```

Before the first time:
 * create local .env file
 * instal venv.

Running the bot:
```
(tmux new -s bot or screen)
cd ~/dev/telegram-bot-master;
source bin/activate
python bot.py
(detatch session)

Run torrent client wathcing that directory.
```


