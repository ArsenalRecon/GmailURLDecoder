import re
import mmap
import argparse
import json
from collections import OrderedDict
from base64 import b64decode
from datetime import datetime


def main(args):
    all_urls = False
    info_list_obj = []

    # Define regex patterns
    pattern_common = r"(?:https\:\/\/mail\.google\.com\/mail\/u)(?:\/(?P<user_no>[0-9]+))+(?:\/(?P<search_flag>\#search))?(?(search_flag)(?:\/(?P<search_string>.[^\/\?\s]{1,100}))|(?:\/(?P<folder>\#[a-z]+)))(?:\/(?P<subfolder>[a-z]{1,10}))?"
    pattern_leg = r"(?:\/(?P<legacy_view_token>[0-9a-fA-F]{15,16}))?(?:\?compose\=(?:new|(?P<legacy_compose_token>[0-9a-fA-F]{15,16}(?:\%2C[0-9a-fA-F]{15,16})*)))?"
    pattern_new = r"(?:\/(?P<new_view_token>[b-df-hj-np-tv-zB-DF-HJ-NP-TV-Z]{32,}))?(?:\?compose\=(?:new|(?P<new_compose_token>[b-df-hj-np-tv-zB-DF-HJ-NP-TV-Z]{32,})))?"

    # Create pattern according to params
    if args.legacy:
        pattern = '(' + pattern_common + pattern_leg + ')'
    
    elif args.new:
        pattern = '(' + pattern_common + pattern_new + ')'
    
    else:
        all_urls = True
        pattern = '(' + pattern_common + pattern_leg + pattern_new + ')'
    
    # Find matches and build output
    if args.text:
        p = re.compile(pattern)

        with open(args.input, 'r') as input_f:
            line = input_f.readline()
            line_no = 1

            while line:
                result = p.match(line.replace('\n', '').replace('\r', ''))

                if result:
                    info_obj = build_info_output(result, args, all_urls)
                    info_obj["line"] = str(line_no)
                    info_obj.move_to_end("line", last=False)

                    info_list_obj.append(info_obj)
                    
                    if args.verbose:
                        print(json.dumps(info_obj, indent=4) + "\n")

                line = input_f.readline()
                line_no += 1

    elif args.raw:
        pattern = bytes(pattern, 'ascii')
        p = re.compile(pattern)

        with open(args.input, 'rb') as input_f:

            with mmap.mmap(input_f.fileno(), 0, access = mmap.ACCESS_READ) as mm:

                for result in p.finditer(mm):
                    info_obj = build_info_output(result, args, all_urls)
                    info_obj["offset"] = str(hex(result.start()))
                    info_obj.move_to_end("offset", last=False)

                    info_list_obj.append(info_obj)

                    if args.verbose:
                        print(json.dumps(info_obj, indent=4) + "\n")

    # Write output file
    with open(args.output, 'w') as output_f:

        if args.compact:
            json_info = json.dumps(info_list_obj)
            
        else:
            json_info = json.dumps(info_list_obj, indent=4)

        output_f.write(json_info)


def build_info_output(result, args, all_urls):
    url = result.group(0)
    if args.raw: url = clean_bytes_string(url)

    info_obj = OrderedDict()

    for group_title in result.groupdict().keys():
        group_info = result.group(group_title)

        if group_info: # Process only non-emtpy fields

            if args.raw: group_info = clean_bytes_string(group_info)

            if (args.legacy or all_urls) and (group_title == "legacy_compose_token"):

                if args.raw:
                    corrected_group_info = correct_legacy_compose_token(group_info)
                    url.replace(group_info, corrected_group_info)
                    group_info = corrected_group_info
                
                info_obj[group_title] = group_info
                comp = group_info.split("%2C")

                if len(comp) > 1: # When more than one mail was being composed at the same time

                    for i in range(len(comp)):
                        ts = get_timestamp(int(comp[i], 16)) # Convert hexstring to int
                        info_obj["timestamp" + str(i+1) + '_' + group_title] = str(ts)

                else:
                    ts = get_timestamp(int(group_info, 16))
                    info_obj["timestamp_" + group_title] = str(ts)

            elif (args.legacy or all_urls) and (group_title == "legacy_view_token"):

                if args.raw and (not result.group("legacy_compose_token")):
                    corrected_group_info = correct_legacy_view_token(group_info)
                    url.replace(group_info, corrected_group_info)
                    group_info = corrected_group_info
                
                info_obj[group_title] = group_info

                ts = get_timestamp(int(group_info, 16))
                info_obj["timestamp_" + group_title] = str(ts)

            elif (args.new or all_urls) and (group_title in ["new_view_token", "new_compose_token"]):

                if group_title == "new_compose_token":

                    if args.raw:
                        corrected_group_info = correct_new_token(group_info)
                        url = url.replace(group_info, corrected_group_info)
                        group_info = corrected_group_info
                    
                elif group_title == "new_view_token":

                    if args.raw and (not result.group("new_compose_token")):
                        corrected_group_info = correct_new_token(group_info)
                        url = url.replace(group_info, corrected_group_info)
                        group_info = corrected_group_info

                info_obj[group_title] = group_info

                decoded_token = decode(group_info)
                info_obj["dec_" + group_title] = decoded_token
                
                new_timestamp_prefixes = ["thread-f:", "msg-f:"]

                for prefix in new_timestamp_prefixes:

                    if prefix in decoded_token:
                        off = decoded_token.index(prefix) + len(prefix)

                        # 19 is the number of digits of the timestamp as int.
                        # A 18 digit timestamp cannot appear as  that is back to year 2000.
                        # Gmail was released on 2004
                        stripped = int(decoded_token[off:off+19]) 
                        ts = get_timestamp(stripped)
                        info_obj["timestamp_" + group_title + '_' + prefix] = str(ts)

            else:
                info_obj[group_title] = group_info

    info_obj["url"] = url
    info_obj.move_to_end("url", last=False)

    return info_obj


def clean_bytes_string(s):
    return str(s)[2:-1] # Remove (b') prefix and (') suffix


def get_timestamp(n):
    # n / nanoseconds / ArnausNumber = n / (nanoseconds * ArnausNumber)
    #
    # nanoseconds                   -> 1000000000
    # ArnausNumber                  -> 1.048576
    # nanoseconds * ArnausNumber    -> 1048576000
    return datetime.utcfromtimestamp(n / 1048576000.) # UTC


# ---
# Heuristics to correct tokens when running against raw data
# ---

def correct_legacy_compose_token(token):
    splitted = token.split("%2C")

    if (splitted[-1][0] != '1') and len(splitted[-1]) == 16:
        splitted[-1] = splitted[-1][:15]
        token = "%2C".join(splitted)

    return token


def correct_legacy_view_token(token):
    if (token[0] != '1') and len(token) == 16:
        token = token[:15]

    return token


def correct_new_token(token):
    correction_bound = len(token) - 32 # Because 32 is the min length of any new_token
    correct_n = 0

    while (not decode(token)) and (correct_n <= correction_bound):
        token = token[:-1]
        correct_n += 1
    
    return token

# ---

# ---
# Implementation of tokens' decoding 
# ---

def decode(token):
    charset_full = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/"
    charset_reduced = "BCDFGHJKLMNPQRSTVWXZbcdfghjklmnpqrstvwxz"
    thread_pre = "thread-"

    try:
        out_str = transform(token, charset_reduced, charset_full)
        padding = '=' * (-len(out_str) % 4)
        result = b64decode(out_str + padding).decode("utf-8")

        if (result.find(thread_pre) == -1):
            result = thread_pre + result
        return result

    except:
        return False


def transform(token, charset_in, charset_out):
    size_str = len(token)

    size_in = len(charset_in)
    size_out = len(charset_out)

    alph_map = {}
    for i in range(size_in):
        alph_map[charset_in[i]] = i
    
    in_str_idx = []
    for i in reversed(range(size_str)):
        chr = token[i]
        idx = alph_map[chr]
        in_str_idx.append(idx)

    out_str_idx = []
    for i in reversed(range(len(in_str_idx))):
        offset = 0

        for j in range(len(out_str_idx)):
            idx =  size_in * out_str_idx[j] + offset

            if (idx >= size_out):
                rest = idx % size_out
                offset = (idx - rest) // size_out
                idx = rest
            
            else:
                offset = 0
            
            out_str_idx[j] = idx
        
        while (offset):
            rest = offset % size_out
            out_str_idx.append(rest)
            offset = (offset - rest) // size_out
        
        offset = in_str_idx[i]

        j = 0
        while (offset):

            if (j >= len(out_str_idx)):
                out_str_idx.append(0)
            
            idx = out_str_idx[j] + offset

            if (idx >= size_out):
                rest = idx % size_out
                offset = (idx - rest) // size_out
                idx = rest

            else:
                offset = 0
            
            out_str_idx[j] = idx
            j+=1

    out_buff = []
    for i in reversed(range(len(out_str_idx))):
        idx = out_str_idx[i]
        out_buff.append(charset_out[idx])
    
    out_str = "".join(out_buff)

    return out_str

# ---

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Extract and decode information from Gmail URLs")
    
    input_format = parser.add_mutually_exclusive_group(required=True)
    input_format.add_argument('-t', '--text', action='store_true', help='set input as a plain text file with an URL per line')
    input_format.add_argument('-r', '--raw', action='store_true', help='set input as a raw data file')

    url_pattern = parser.add_mutually_exclusive_group()
    url_pattern.add_argument('-n', '--new', action='store_true', help='only look for new URLs')
    url_pattern.add_argument('-l', '--legacy', action='store_true', help='only look for legacy URLs')

    io_group = parser.add_argument_group("required arguments")
    io_group.add_argument('-i', '--input', type=str, metavar='PATH', required=True, help='path of the input file')
    io_group.add_argument('-o', '--output', type=str, metavar='PATH', required=True, help='path of the output file')

    parser.add_argument('-v', '--verbose', action='store_true', help='print the results as they are found')
    parser.add_argument('-c', '--compact', action='store_true', help='write compact output')

    args = parser.parse_args()

    main(args)