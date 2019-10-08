import urllib
import boto3
from google.cloud import vision
import os
import re
import string
import json
# -*- coding: utf-8 -*-

print('Loading function')

# Configure environment for google cloud vision
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "client_secrets.json"

# Access s3 buckets using boto3
S3 = boto3.resource("s3")

# Create a ImageAnnotatorClient
VisionAPIClient = vision.ImageAnnotatorClient()


# lambda_handler function is called when lambda function is triggered
def lambda_handler(event, context):

    # Gets bucket name and file name from the event
    bucket = event['Records'][0]['s3']['bucket']['name']
    key = urllib.unquote_plus(event['Records'][0]['s3']['object']['key'].encode('utf8'))

    # Gets the object and content of uploaded image
    obj = S3.Object(bucket_name=bucket, key=key, )
    content = obj.get()['Body'].read()
    
    # Gets lead id from path letsmd-web/lead/27455/file_name
    lead_id = key.split('/')[1]
    
    # Sends image content to vision ans stores text-related response in text
    image = vision.types.Image(content=content)
    response = VisionAPIClient.document_text_detection(image=image)
    
    # SAMPLE RESPONSE:
    # {
    #   "responses": [
    #     {
    #       "textAnnotations": [
    #         {
    #           "locale": "en",
    #           "description": "All text\n",
    #           "boundingPoly": {
    #             "vertices": [
    #               {
    #                 "x": 14,
    #                 "y": 11
    #               },
    #               {
    #                 "x": 279,
    #                 "y": 11
    #               },
    #               {
    #                 "x": 279,
    #                 "y": 37
    #               },
    #               {
    #                 "x": 14,
    #                 "y": 37
    #               }
    #             ]
    #           }
    #         },
    #       ],
    #       "fullTextAnnotation": {
    #         "pages": [
    #           {
    #             "property": {
    #               "detectedLanguages": [
    #                 {
    #                   "languageCode": "en"
    #                 }
    #               ]
    #             },
    #             "width": 281,
    #             "height": 44,
    #             "blocks": [
    #               {
    #                 "property": {
    #                   "detectedLanguages": [
    #                     {
    #                       "languageCode": "en"
    #                     }
    #                   ]
    #                 },
    #                 "boundingBox": {
    #                   "vertices": [
    #                     {
    #                       "x": 14, "y": 11
    #                     },
    #                     {
    #                       "x": 279, "y": 11
    #                     },
    #                     {
    #                       "x": 279, "y": 37
    #                     },
    #                     {
    #                       "x": 14, "y": 37
    #                     }
    #                   ]
    #                 },
    #                 "paragraphs": [
    #                   {
    #                     "property": {
    #                       "detectedLanguages": [
    #                         {
    #                           "languageCode": "en"
    #                         }
    #                       ]
    #                     },
    #                     "boundingBox": {
    #                       "vertices": [
    #                         {
    #                           "x": 14, "y": 11
    #                         },
    #                         {
    #                           "x": 279, "y": 11
    #                         },
    #                         {
    #                           "x": 279, "y": 37
    #                         },
    #                         {
    #                           "x": 14, "y": 37
    #                         }
    #                       ]
    #                     },
    #                     "words": [
    #                       {
    #                         "property": {
    #                           "detectedLanguages": [
    #                             {
    #                               "languageCode": "en"
    #                             }
    #                           ]
    #                         },
    #                         "boundingBox": {
    #                           "vertices": [
    #                             {
    #                               "x": 14, "y": 11
    #                             },
    #                             {
    #                               "x": 23, "y": 11
    #                             },
    #                             {
    #                               "x": 23, "y": 37
    #                             },
    #                             {
    #                               "x": 14, "y": 37
    #                             }
    #                           ]
    #                         },
    #                         "symbols": [
    #                           {
    #                             "property": {
    #                               "detectedLanguages": [
    #                                 {
    #                                   "languageCode": "en"
    #                                 }
    #                               ],
    #                               "detectedBreak": {
    #                                 "type": "SPACE"
    #                               }
    #                             },
    #                             "boundingBox": {
    #                               "vertices": [
    #                                 {
    #                                   "x": 14, "y": 11
    #                                 },
    #                                 {
    #                                   "x": 23, "y": 11
    #                                 },
    #                                 {
    #                                   "x": 23, "y": 37
    #                                 },
    #                                 {
    #                                   "x": 14, "y": 37
    #                                 }
    #                               ]
    #                             },
    #                             "text": "A"
    #                           }
    #                         ]
    #                       },
    #                     ]
    #                   }
    #                 ],
    #                 "blockType": "TEXT"
    #               }
    #             ]
    #           }
    #         ],
    #         "text": "All Text\n"
    #       }
    #     }
    #   ]
    # }
        
    document = response.full_text_annotation

    # to identify and compare the break object (e.g. SPACE and LINE_BREAK) obtained in API response
    breaks = vision.enums.TextAnnotation.DetectedBreak.BreakType

    # generic counter
    c = 0

    # List of lines extracted
    lines = []

    # List of corresponding confidence scores of lines
    confidence = []

    # Initialising list of lines
    lines.append('')

    # Initialising list of confidence scores
    confidence.append(2)

    # Loop through all symbols returned and store them in lines list alongwith
    # corresponding confidence scores in confidence list
    for page in document.pages:
        for block in page.blocks:
            for paragraph in block.paragraphs:
                for word in paragraph.words:
                    for symbol in word.symbols:
                        lines[c] = lines[c] + symbol.text
                        if re.match(r'^[a-zA-Z]+\Z', symbol.text) or symbol.text.isdigit():
                            confidence[c] = min(confidence[c], symbol.confidence)
                        if symbol.property.detected_break.type == breaks.LINE_BREAK or \
                                symbol.property.detected_break.type == breaks.EOL_SURE_SPACE:
                            c += 1
                            lines.append('')
                            confidence.append(2)
                        elif symbol.property.detected_break.type == breaks.SPACE or \
                                symbol.property.detected_break.type == breaks.SURE_SPACE:
                            lines[c] = lines[c] + ' '

    # Total number of lines
    linecount = len(lines)

    # Initialising all variables
    aadhar_name = ''  # Name on Aadhar card
    pan_name = ''  # Name on PAN card
    pan_fname = ''  # Father's name on PAN card
    aadhar_dob = ''  # Date of Birth on Aadhar card
    pan_dob = ''  # Date of Birth on PAN card
    gender = ''  # Gender on Aadhar card
    aadhar_no = ''  # Aadhar no.
    pan_no = ''  # PAN no.
    address = ''  # Address as on back side of Aadhar card
    address_1 = ''  # Line 1 of address
    address_2 = ''  # Line 2 of address
    doc_type = ''  # PAN/ Aadhar or their combination
    pincode = 0  # Pincode as in address on back side of aadhar card
    aadhar_name_confidence = 2  # Corresponding confidence score
    pan_name_confidence = 2  # Corresponding confidence score
    pan_fname_confidence = 2  # Corresponding confidence score
    aadhar_dob_confidence = 2  # Corresponding confidence score
    pan_dob_confidence = 2  # Corresponding confidence score
    gender_confidence = 2  # Corresponding confidence score
    aadhar_no_confidence = 2  # Corresponding confidence score
    pan_no_confidence = 2  # Corresponding confidence score
    address_confidence = 2  # Corresponding confidence score
    pincode_confidence = 2  # Corresponding confidence score
    raw = ''  # To store all lines
    checktext = ''  # Generic string variable to store surrounding lines

    # To verify aadhar number using verhoeff algorithm
    verhoeff_table_d = (
        (0, 1, 2, 3, 4, 5, 6, 7, 8, 9),
        (1, 2, 3, 4, 0, 6, 7, 8, 9, 5),
        (2, 3, 4, 0, 1, 7, 8, 9, 5, 6),
        (3, 4, 0, 1, 2, 8, 9, 5, 6, 7),
        (4, 0, 1, 2, 3, 9, 5, 6, 7, 8),
        (5, 9, 8, 7, 6, 0, 4, 3, 2, 1),
        (6, 5, 9, 8, 7, 1, 0, 4, 3, 2),
        (7, 6, 5, 9, 8, 2, 1, 0, 4, 3),
        (8, 7, 6, 5, 9, 3, 2, 1, 0, 4),
        (9, 8, 7, 6, 5, 4, 3, 2, 1, 0))
    verhoeff_table_p = (
        (0, 1, 2, 3, 4, 5, 6, 7, 8, 9),
        (1, 5, 7, 6, 2, 8, 3, 0, 9, 4),
        (5, 8, 0, 3, 7, 9, 6, 1, 4, 2),
        (8, 9, 1, 6, 0, 4, 3, 5, 2, 7),
        (9, 4, 5, 3, 1, 2, 6, 8, 7, 0),
        (4, 2, 8, 6, 5, 7, 3, 9, 0, 1),
        (2, 7, 9, 3, 8, 0, 6, 4, 1, 5),
        (7, 0, 4, 6, 9, 1, 3, 2, 5, 8))
    verhoeff_table_inv = (0, 4, 3, 2, 1, 5, 6, 7, 8, 9)

    # Loop through all lines to check for all required fields like aadhar no. , date of birth, address and so on
    for index, line in enumerate(lines):

        # To store all lines for exporting later as raw output
        raw = raw + line + "\n"

        # Total number of characters in line
        length = len(line)

        # Name and date of birth in Aadhar card
        # Looks for DOB or Year of Birth
        # Name is present in the preceding line
        # Date of birth in same or next line
        if "DOB:" in line or \
                "D0B:" in line or \
                "DOB " in line or \
                "DOB :" in line or \
                "Year of Birth:" in line or \
                "Year of Birth " in line:
            checktext = lines[index - 1]
            if all(x.isalpha() or x.isspace() for x in checktext) and \
                    len(checktext) > 3 and \
                    checktext[0].isupper() and \
                    "Address" not in checktext:
                aadhar_name = checktext
                aadhar_name_confidence = confidence[index - 1]

            checktext = lines[index + 1]
            clength = len(checktext)

            # Checking if last 10 characters of text are in format XX/XX/XXXX or XX-XX-XXXX in same line
            # where X represents a digit
            if length >= 10 and \
                    line[length - 10].isdigit() and \
                    line[length - 9].isdigit() and \
                    (line[length - 8] == '/' or line[length - 8] == '-') and \
                    line[length - 7].isdigit() and \
                    line[length - 6].isdigit() and \
                    (line[length - 5] == '/' or line[length - 6] == '-') and \
                    line[length - 4].isdigit() and \
                    line[length - 3].isdigit() and \
                    line[length - 2].isdigit() and \
                    line[length - 1].isdigit():
                line = line[:length - 8] + '/' + line[length - 7:length - 5] + '/' + line[length - 4:length]
                aadhar_dob = line[-10:]
                aadhar_dob_confidence = confidence[index]

            # Checking if last 10 characters of text are in format XX/XX/XXXX or XX-XX-XXXX in next line
            # where X represents a digit
            elif clength >= 10 and \
                    checktext[clength - 10].isdigit() and \
                    checktext[clength - 9].isdigit() and \
                    (checktext[clength - 8] == '/' or checktext[clength - 8] == '-') and \
                    checktext[clength - 7].isdigit() and \
                    checktext[clength - 6].isdigit() and \
                    (checktext[clength - 5] == '/' or checktext[clength - 6] == '-') and \
                    checktext[clength - 4].isdigit() and \
                    checktext[clength - 3].isdigit() and \
                    checktext[clength - 2].isdigit() and \
                    checktext[clength - 1].isdigit():
                checktext = checktext[:clength - 8] + '/' + checktext[clength - 7:clength - 5] + '/' + checktext[
                                                                                                       length - 4:clength]
                aadhar_dob = checktext[-10:]
                aadhar_dob_confidence = confidence[index + 1]

        # Aadhar number
        # Checking if line consists of 12 digits only
        checktext = line.replace(" ", "")
        if len(checktext) == 12 and checktext.isdigit():

            # Verifying using Verhoeff algorithm
            verhoeffc = 0
            for i, item in enumerate(reversed(str(checktext))):
                verhoeffc = verhoeff_table_d[verhoeffc][verhoeff_table_p[i % 8][int(item)]]
            if verhoeffc == 0:
                aadhar_no = checktext
                aadhar_no_confidence = confidence[index]

        # Gender
        # Checking if line ends with word 'male' or 'female'
        if line.endswith("male") or line.endswith("Male") or line.endswith("MALE"):
            if line.endswith("female") or line.endswith("Female") or line.endswith("FEMALE"):
                gender = "F"
            else:
                gender = "M"
            gender_confidence = confidence[index]

        # Name and father's name from PAN card
        # They are in capital letters and between text 'INCOME TAX DEPARTMENT' and date of birth
        if "INCOME TAX DEPARTMENT" in line:
            c = index + 1
            while c < linecount:
                checktext = lines[c]
                length1 = len(checktext)
                if all(x.isalpha() or x.isspace() for x in checktext) and \
                        len(checktext) > 3 and \
                        checktext.isupper() and \
                        not ("DEPARTMENT" in checktext or \
                             "TAX" in checktext or \
                             "GOVT" in checktext or \
                             "INDIA" in checktext or \
                             "CAMERA" in checktext or \
                             "AADHAR" in checktext or \
                             "IDENTITY" in checktext or \
                             "INFORMATION" in checktext):
                    if pan_name == '':
                        pan_name = checktext
                        pan_name_confidence = confidence[c]
                    elif pan_fname == '':
                        pan_fname = checktext
                        pan_fname_confidence = confidence[c]

                # Date of birth
                # Checking if last 10 characters of text are in format XX/XX/XXXX or XX-XX-XXXX in next line
                # where X represents a digit
                if length1 >= 10:
                    if checktext[length1 - 10].isdigit() and \
                            checktext[length1 - 9].isdigit() and \
                            (checktext[length1 - 8] == '/' or checktext[length1 - 8] == '-') and \
                            checktext[length1 - 7].isdigit() and \
                            checktext[length1 - 6].isdigit() and \
                            (checktext[length1 - 5] == '/' or checktext[length1 - 6] == '-') and \
                            checktext[length1 - 4].isdigit() and \
                            checktext[length1 - 3].isdigit() and \
                            checktext[length1 - 2].isdigit() and \
                            checktext[length1 - 1].isdigit():
                        checktext = checktext[:length1 - 8] + '/' + checktext[
                                                                    length1 - 7:length1 - 5] + '/' + checktext[
                                                                                                     length1 - 4:length1]
                        pan_dob = checktext[-10:]
                        pan_dob_confidence = confidence[c]
                        break
                c += 1

        if pan_dob == '':
            pan_name = ''
            pan_fname = ''
            pan_name_confidence = 2
            pan_fname_confidence = 2


        # PAN number
        # if line contains exactly 10 characters in the format XXXPXDDDDX
        # where X represents a character and D represents a digit
        if len(line) == 10:
            if line[0].isupper() and \
                    line[1].isupper() and \
                    line[2].isupper() and \
                    line[3] == 'P' and \
                    line[4].isupper() and \
                    line[5].isdigit() and \
                    line[6].isdigit() and \
                    line[7].isdigit() and \
                    line[8].isdigit() and \
                    line[9].isupper():
                pan_no = line
                pan_no_confidence = confidence[index]

        # Address
        # if word 'address' in line, address will be text following it
        # or in the lines following that line
        # till pincode (a set of six digits) is reached

        # To remove Hindi or other language characters, each characters will be compared against following character set
        ascii = set(string.printable)

        if "Address" in line:
            c = index

            # address_second_part stores string after first pincode and before second pin code
            address_second_part = ''

            while c < linecount:

                # largest_string stores largest string of characters excluding other language characters in a line
                largest_string = ''
                compare_string = ''
                for character in lines[c]:
                    if character in ascii:
                        compare_string = compare_string + character
                    elif len(largest_string) < len(compare_string):
                        largest_string = compare_string
                        compare_string = ''
                    else:
                        compare_string = ''

                if len(largest_string) < len(compare_string):
                    largest_string = compare_string

                # Removes special characters and spaces in the beginning of largest_string
                if largest_string.startswith(',') or largest_string.startswith(' '):
                    largest_string = largest_string[1:]
                if largest_string.startswith(',') or largest_string.startswith(' '):
                    largest_string = largest_string[1:]

                # If largest_string of a line contains english characters, add it to address or address_second_part
                if re.search('[a-zA-Z]', largest_string):
                    if pincode == 0:
                        if not address.endswith(' '):
                            address = address + ' '
                        address = address + largest_string
                    else:
                        if not address_second_part.endswith(' '):
                            address_second_part = address_second_part + ' '
                        address_second_part = address_second_part + largest_string

                # Check for pincode in line
                numbers = re.findall('\d+', lines[c])
                numbers = list(map(int, numbers))
                numbers.append(1)
                if 1000000 > max(numbers) > 99999:
                    if pincode > 0:
                        if str(pincode) in address:

                            # Remove pincode from address
                            address1 = address.replace(str(pincode), '')

                            # Remove special characters at the end of address
                            if address1.endswith(' ') or address1.endswith('-') or address1.endswith(','):
                                address1 = address1[:-1]
                            if address1.endswith(' ') or address1.endswith('-') or address1.endswith(','):
                                address1 = address1[:-1]
                            address = address1

                        address = address + address_second_part
                        break
                    else:
                        pincode = max(numbers)
                        pincode_confidence = confidence[c]
                c += 1

            # Remove pincode from address
            address1 = address.replace(str(pincode), '')

            # Remove special characters at the end of address
            if address1.endswith(' ') or address1.endswith('-') or address1.endswith(','):
                address1 = address1[:-1]
            if address1.endswith(' ') or address1.endswith('-') or address1.endswith(','):
                address1 = address1[:-1]

            # Remove address word and special characters in the beginning from address
            address = address1.replace('Address :', '').replace('Address:', '').replace('Address', '')
            if address.startswith(' ') or address.startswith('-') or address.startswith(',') or address.startswith('.'):
                address = address[1:]
            if address.startswith(' ') or address.startswith('-') or address.startswith(',') or address.startswith('.'):
                address = address[1:]
            if address.startswith(' ') or address.startswith('-') or address.startswith(',') or address.startswith('.'):
                address = address[1:]
            if address.startswith(' ') or address.startswith('-') or address.startswith(',') or address.startswith('.'):
                address = address[1:]

    # Split address from middle
    splitstring = address.replace(',', ' ').split(' ')
    address_1 = address[:len(' '.join(splitstring[:len(splitstring) // 2]))]
    address_2 = address[len(' '.join(splitstring[:len(splitstring) // 2])):]

    # Remove space and/ or comma from beginning of second line of address
    if address_2.startswith(' ') or address_2.startswith(','):
        address_2 = address_2[1:]
    if address_2.startswith(' ') or address_2.startswith(','):
        address_2 = address_2[1:]

    # Check document type by checking for pan number, gender and address
    if pan_no != '' and pan_fname != '':
        if gender != '' and aadhar_no != '':
            if address != '':
                doc_type = "P-AF-AB"
            else:
                doc_type = "P-AF"
        elif address != '':
            doc_type = "P-AB"
        else:
            doc_type = "P"
    elif gender != '' and aadhar_no != '':
        if address != '':
            doc_type = "AF-AB"
        else:
            doc_type = "AF"
    elif address != '':
        doc_type = 'AB'
    else:
        doc_type = 'UF'

    if pan_no_confidence == 2:
        pan_no_confidence = 0

    if aadhar_no_confidence == 2:
        pan_name_confidence = 0

    if aadhar_name_confidence == 2:
        aadhar_name_confidence = 0

    if pan_fname_confidence == 2:
        pan_fname_confidence = 0

    if pan_name_confidence == 2:
        pan_name_confidence = 0

    if pan_dob_confidence == 2:
        pan_dob_confidence = 0

    if aadhar_dob_confidence == 2:
        aadhar_dob_confidence = 0

    if address_confidence == 2:
        address_confidence = 0

    if gender_confidence == 2:
        gender_confidence = 0
    
    if pincode_confidence == 2:
        pincode_confidence = 0
        
    content = {}
    content['status'] = 'true'
    content['data'] = {}
    content['data']['number'] = {}
    content['data']['number']['aadhar'] = aadhar_no
    content['data']['number']['aadhar_confidence'] = round(aadhar_no_confidence,2)
    content['data']['number']['pan'] = pan_no
    content['data']['number']['pan_confidence'] = round(pan_no_confidence,2)
    content['data']['name'] = {}
    content['data']['name']['aadhar'] = aadhar_name
    content['data']['name']['aadhar_confidence'] = round(aadhar_name_confidence,2)
    content['data']['name']['pan'] = pan_name
    content['data']['name']['pan_confidence'] = round(pan_name_confidence,2)
    content['data']['name']['pan_father_name'] = pan_fname
    content['data']['name']['pan_father_name_confidence'] = round(pan_fname_confidence,2)
    content['data']['dob'] = {}
    content['data']['dob']['aadhar'] = aadhar_dob
    content['data']['dob']['aadhar_confidence'] = round(aadhar_dob_confidence,2)
    content['data']['dob']['pan'] = pan_dob
    content['data']['dob']['pan_confidence'] = round(pan_dob_confidence,2)
    content['data']['address'] = {}
    content['data']['address']['aadhar'] = {}
    content['data']['address']['aadhar']['line_1'] = address_1
    content['data']['address']['aadhar']['line_2'] = address_2
    content['data']['address']['aadhar']['address_confidence'] = round(address_confidence,2)
    content['data']['address']['aadhar']['pincode'] = pincode
    content['data']['address']['aadhar']['pincode_confidence'] = round(pincode_confidence,2)
    content['data']['address']['aadhar']['raw'] = address
    content['data']['gender'] = {}
    content['data']['gender']['aadhar'] = gender
    content['data']['gender']['aadhar_confidence'] = round(gender_confidence,2)
    content['data']['type'] = doc_type
    content['data']['lead_id'] = lead_id
    content['data']['raw_string'] = raw
    content['data']['remarks'] = {}
    
    #json_data = json.dumps(content)
    
    # extracts name from uploaded file and saves text file with same name with .txt extension
    #file_name = key.split('.')[0] + ".json"
    #S3.Bucket(bucket).put_object(Key=file_name, Body=json_data)
    r = requests.post(url = 'http://api.dev.letsmd.com/v1/documents-callback', auth=('dev', 'hfPA6g8zjA') ,json = content)
    print(r.text)
    
    
