# sag_meter

Simple teste code to compute suspenssion SAG from a Yocto-RangeFinder
Read full article on our web site: https://www.yoctopuce.com/EN/article/regler-ses-suspensions-avec-un-yocto-rangefinder


## Installation:
This code require the Yoctopuce python library, which can be installed with pip
``pip install yoctopuce``

You also need to install the tkinter package
``pip install tkinter``

## Usage

````
Usage: sag_meter.py [-h] [-g] [-v] [-r URL] [-s TARGET] travel
Compute suspension sag from Yocto-RangeFinder

positional arguments:
  travel               suspension travel in mm

options:
  -h, --help           show this help message and exit
  -g, --gui            show GUI
  -v, --verbose
  -r, --remote URL     Remote YoctoHub or VirtualHub
  -s, --serial TARGET  serial number (or logical name) of the Yocto-Range finder to use
````