## Gmail URL Decoder

Gmail URL Decoder is an Open Source Python tool that can be used against plaintext or arbitrary raw data files in order to find, extract, and decode information from Gmail URLs related to both the new and legacy Gmail interfaces.

## Usage
Run with python3 (properly tested on 3.6.7 version):
```
usage: GmailURLDecoder.py [-h] (-t | -r) [-n | -l] -i PATH -o PATH [-v] [-c]

Extract and decode information from Gmail URLs

optional arguments:
  -h, --help            show this help message and exit
  -t, --text            set input as a plain text file with an URL per line
  -r, --raw             set input as a raw data file
  -n, --new             only look for new URLs
  -l, --legacy          only look for legacy URLs
  -v, --verbose         print the results as they are found
  -c, --compact         write compact output

required arguments:
  -i PATH, --input PATH
                        path of the input file
  -o PATH, --output PATH
                        path of the output file
```

### Plaintext input vs Raw data input
You can run the program against to different types of input:
- plaintext file cointaining an URL per line (extracted beforehand)
- raw data file

The former is recommended in case you have access to non-corrupted files storing URLs in a known way that can be extracted easily (mainly history files) as it will make the search faster (due to the ability to load into RAM a line each time when dealing with plaintext files) and less prone to parsing inaccuracy (due to some heuristics that have to bee applied into raw data file parsing to properly separate URLs' data from other adjacent data).

### Legacy vs New URL format
By default, the program will look for URLs from both legacy and new gmail interface. In case you are totally convinced that you won't find any URL from the old (or new) format, you can look only for one of those specific patterns to save a little time when running it against huge files.

### Output
The output file generated consists of json formatted data that can be easily consumed by any other application or programming language.

You can use the compact '-c' argument for the data to be written without any indentation (that might be useful if you will only consume the json output with another applicaion/language and not human reading it directly.

Moreover, if you want to print in terminal results as they are being found, you can use the verbose '-v' argument


## Examples
Run the program against a raw data file
```
python3 GmailURLDecoder.py -r -i /path/to/input/raw.dat -o /path/to/output/rawdata_results.json
```
Run the program against a plaintext file in verbose mode
```
python3 GmailURLDecoder.py -t -i /path/to/input/plain.txt -o /path/to/output/plaintext_results.json -v
```
Run the program against a raw data file looking only for legacy URLs with compact output
```
python3 GmailURLDecoder.py -r -l -i /path/to/input/raw.dat -o /path/to/output/rawdata_results.json -c
```
Run the program against a plaintext file looking only for new URLs in verbose mode and with compact output
```
python3 GmailURLDecoder.py -t -n -i /path/to/input/plain.txt -o /path/to/output/plaintext_results.json -v -c
```

## Contributions
Contributions and improvements to the code are welcomed.

## License
Distributed under the MIT License. See License.md for details.

## More Information

To learn more about Arsenal’s digital forensics software and training, please visit https://ArsenalRecon.com and follow us on Twitter @ArsenalRecon (https://twitter.com/ArsenalRecon).

To learn more about Arsenal’s digital forensics consulting services, please visit https://ArsenalExperts.com and follow us on Twitter @ArsenalArmed (https://twitter.com/ArsenalArmed).
