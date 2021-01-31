pan.py tool allows you to read & analyse XML files of Persönlicher Arbeitszeit-Nachweis (PAN)
Created by Dr. Schirrow, the original tool is the default solution at the municipality of the Hanse- und Universitätsstadt Rostock.

# PAN


* stores config in XML file at `%HOMEPATH%\pan.xml`
* stores working times in a custom XML fileformat following with german keywords (no XSD)

# Setup

# Usage

Start the tool like `python3 pan.py`.
You can set the configuration file, or month file like:
* `python3 pan.py check --xmlmonth ./pan/pan_R62ad001_1-2021.xml`