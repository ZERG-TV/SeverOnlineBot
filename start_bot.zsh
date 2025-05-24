#!/bin/zsh
source /home/t/my_bot/myenv/bin/activate  # Укажите путь к вашему виртуальному окружению
nohup python /home/t/my_bot/SeverOnlineBot.py > /home/t/my_bot/bot.log 2>&1 &
