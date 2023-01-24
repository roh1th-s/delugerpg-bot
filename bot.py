from dotenv import load_dotenv
from os import getenv
from traceback import format_exc
from delugebot import DelugeBot

load_dotenv()

def beep():
    from winsound import Beep
    Beep(600, 1000 * 5)

def main():
    try:
        bot = DelugeBot(getenv("PHPSESSID"), getenv("PASSWORD"), getenv("NICKNAME"))
        # bot = DelugeBot(getenv("PHPSESSID"), getenv("PASSWORD"))
        bot.levelFarmBattle("fire", 6, 3)
        # bot.startPokemonHunt("overworld5", legends_only=True)

        # for region_no in range(6, 9):
        #     bot.defeatAllGyms(region_no)
        # bot.defeatGymsWithCodes([681, 781, 881])
    except Exception as e:
        print(format_exc())

    beep()

if __name__ == "__main__":
    main()
