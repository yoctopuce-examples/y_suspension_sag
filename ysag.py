import argparse
import sys

from yoctopuce.yocto_api import *
from yoctopuce.yocto_rangefinder import *


class Parameters:
    def __init__(self, travel, max_val):
        self.travel = int(travel)
        self.max_val = int(max_val)
        self.last_val = int(max_val)
        self.sag = 0

    def update(self, new_val):
        # update max value in case the application what started
        # with the suspension compressed
        self.last_val = new_val
        if new_val > self.max_val:
            self.max_val = new_val
        mm_sag = self.max_val - new_val
        sag = mm_sag * 100 // self.travel
        if sag != self.sag:
            self.sag = sag
            print("SAG = %d%% (%dmm = %d-%d)" % (self.sag, mm_sag, self.max_val, self.last_val), end='')


def valueCallback(rf, value):
    p = rf.get_userData()
    p.update(int(value))


def showSag(target, stroke, verbose):
    errmsg = YRefParam()
    if YAPI.RegisterHub("usb", errmsg) != YAPI.SUCCESS:
        sys.exit("Unable to access USB port: " + errmsg.value)

    if target == 'first':
        # retrieve any Range finder
        rf = YRangeFinder.FirstRangeFinder()
        if rf is None:
            sys.exit('No Yocto-RangeFinder')
    else:
        rf = YRangeFinder.FindRangeFinder(target + '.rangeFinder1')
        if not rf.isOnline():
            sys.exit('Yocto-Rangefinder %s is not connected' % target)
    rf.set_rangeFinderMode(YRangeFinder.RANGEFINDERMODE_HIGH_ACCURACY)
    parameters = Parameters(stroke, rf.get_currentValue())
    rf.set_userData(parameters)
    rf.registerValueCallback(valueCallback)
    while rf.isOnline():
        YAPI.Sleep(1000)
    sys.exit("Yocto-Rangefinder %s is offline" % rf.get_serialNumber())


def mettre_a_jour(fenetre, label_heure):
    now = datetime.now()
    heure_str = now.strftime("%H:%M:%S")
    secondes_str = str(int(now.timestamp()))

    label_heure.config(text=f"🕐 Heure : {heure_str}")
    label_secondes.config(text=f"⏱ Secondes (epoch) : {secondes_str}")

    # Rappel automatique toutes les 1000 ms (1 seconde)
    fenetre.after(1000, mettre_a_jour)


def setupWindow():
    # Création de la fenêtre principale
    fenetre = tk.Tk()
    fenetre.title("Horloge en temps réel")
    fenetre.geometry("400x150")
    fenetre.resizable(False, False)
    fenetre.configure(bg="#1e1e2e")

    # Label affichant l'heure formatée
    label_heure = tk.Label(
        fenetre,
        text="",
        font=("Courier New", 18, "bold"),
        fg="#cdd6f4",
        bg="#1e1e2e",
        pady=10,
    )
    label_heure.pack()

    # Label affichant les secondes epoch
    label_secondes = tk.Label(
        fenetre,
        text="",
        font=("Courier New", 13),
        fg="#a6e3a1",
        bg="#1e1e2e",
        pady=5,
    )
    label_secondes.pack(fenetre, label_heure)

    mettre_a_jour()

    fenetre.mainloop()


def main():
    """ Main function, deals with arguments and launch program"""
    parser = argparse.ArgumentParser(description='Compute suspension sag from Yocto-RangeFinder', )
    parser.add_argument('-v', '--verbose', dest='verbose', action='store_true')
    parser.add_argument('-s', '--serial', dest='target', action='store',
                        help='serial number (or logical name) of the Yocto-Range finder to use', default="first")
    parser.add_argument('travel', help='suspension travel in mm')
    args = parser.parse_args()
    print(args)
    showSag(args.target, args.travel, args.verbose)


if __name__ == '__main__':
    main()
