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

        # for _ in range(1, 2):
        #     bot.levelFarmBattle("psychic", 2, 1)
        bot.startPokemonHunt("overworld1", legends_only=True, limit=2, catch_poke=2, attack_no=1)

        # for region_no in range(6, 9):
        #     bot.defeatAllGyms(region_no)
        # bot.defeatGymsWithCodes([681, 781, 881])
    except Exception as e:
        print(format_exc())

    beep()

if __name__ == "__main__":
    main()
