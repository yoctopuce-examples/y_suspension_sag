import argparse
import sys

from yoctopuce.yocto_api import *
from yoctopuce.yocto_rangefinder import *


class Parameters:
    def __init__(self, travel, max_val):
        self.travel = int(travel)
        self.max_val = int(max_val)
        self.sag = 0

    def update(self, new_val):
        # update max value in case the application what started
        # with the suspension compressed
        if new_val > self.max_val:
            self.max_val = new_val
        mm_sag = self.max_val - new_val
        sag = mm_sag * 100 // self.travel
        if sag != self.sag:
            self.sag = sag
        msg = "SAG = %d%% (%dmm)" % (self.sag, mm_sag)
        print(msg, end="\r")


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
