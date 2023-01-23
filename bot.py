from dotenv import load_dotenv
from os import getenv
from traceback import format_exc
from delugebot import DelugeBot

load_dotenv()


def main():
    try:
        bot = DelugeBot(getenv("PHPSESSID"))
        bot.levelFarmBattle("electric")

        # print(bot.http.getMapHashes("overworld1"))
    except Exception as e:
        print(format_exc())


if __name__ == "__main__":
    main()
