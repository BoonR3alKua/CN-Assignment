from torrent import *

while True:
    create_Torrent_full()
    answer = input("Do you want to create another torrent (y/n)?\n")
    if (answer.lower() == 'n'):
        break
    elif (answer.lower() == 'y'):
        continue
    else:
        print("Invalid answer, please try again.")
        continue
