from textextraction.extractors import text_extractor
import re
import csv

PHONE_RE = re.compile(
    r"""(?P<area_code>\(?\d{3}\)?[\s\-\(\)]*)"""
    r"""(?P<first_three>\d{3}[\-\s\(\)]*)"""
    r"""(?P<last_four>\d{4}[\-\s]*)""", re.IGNORECASE)
ZIPCODE_RE = re.compile(r'(\d{5})(?=MD)')
EMAIL_RE = re.compile(r'([a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z-.]+)')
DATE_RE = re.compile(r'(\d{2}/\d{2}/\d{4})')
TITLE_RE = re.compile(r'^(VICE-PRESIDENT|PRESIDENT|SECRETARY|TREASURER|OTHERS)')
CITIES = ['UPPER MARLBORO', 'CHELTENHAM', 'DISTRICT HEIGHT', 'CLINTON', 'BRANDYWINE', 'CROFTON', 'TEMPLE HILLS', 'WALDORF', 'VIENNA', 'ACCOKEEK', 'LA PLATA', 'FORT WASHINGTON', 'SUITLAND', 'OXON HILL', 'HYATTSVILLE', 'LAUREL', 'BOWIE', 'LANHAM', 'COLUMBIA', 'BLADENSBURG', 'GREENBELT', 'COLLEGE PARK', 'GLENN DALE', 'BELTSVILLE', 'BRENTWOOD', 'MOUNT RAINIER', 'ELLICOTT CITY', 'LAUREL', 'OAKTON']
ORG_TYPE = ['CITIZEN', 'HOMEOWNERS', 'OTHER', 'CIVIC', 'HOME OWNERS', 'CONDOMINIUM', 'ENVIRONMENT', 'BUSINESS', 'HISTORIC']


def get_phone_number(line):
    match = PHONE_RE.search(line)
    if match:
        area_code = "".join(ch for ch in match.group("area_code")
                            if ch.isdigit())
        first_three = "".join(ch for ch in match.group("first_three")
                              if ch.isdigit())
        last_four = "".join(ch for ch in match.group("last_four")
                            if ch.isdigit())
        number = "-".join([area_code, first_three, last_four])
        return number


def get_zip_code(line):
    match = ZIPCODE_RE.search(line)
    if match:
        return match.group(0)


def get_email(line):
    match = EMAIL_RE.search(line)
    if match:
        return match.group(0).lstrip('1234567890').title()


def get_date(line):
    match = DATE_RE.search(line)
    if match:
        return match.group(0)


def get_first_digit_index(line):
    for idx, char in enumerate(line):
        if char.isdigit():
            return idx


def has_title(line):
    match = TITLE_RE.search(line)
    if match:
        return True


def get_title_and_name(line):
    title, name = None, None
    line = line.replace('VICE PRESIDENT', 'VICE-PRESIDENT')
    if has_title(line):
        split_index = get_first_digit_index(line)
        title_name_line = line[:split_index].strip().split(' ')[:4]
        if '@' in title_name_line[-1]:
            title_name_line.pop()
        title = ' '.join(title_name_line[:1]).title()
        name = ' '.join(title_name_line[1:]).title()
    return title, name


def get_city_and_city_index(line):
    idx = -1
    for city in CITIES:
        idx = line.find(city)
        if idx > -1:
            return city, idx
    return None, None


def has_no_phone_or_email(line):
    phone_match = PHONE_RE.search(line)
    if phone_match:
        return False
    email_match = EMAIL_RE.search(line)
    if email_match:
        return False
    return True


def get_address_and_city(line):
    start_idx = get_first_digit_index(line)
    city, end_idx = get_city_and_city_index(line)
    if start_idx and end_idx:
        address = line[start_idx:end_idx]
        if has_no_phone_or_email(address):
            return address.title(), city.title()
    return None, None


def clean_org_line(line):
    start_idx = line.find('Council District:')
    if start_idx > -1:
        line = line[start_idx + 17:].strip()
    return line.strip()


def get_org_name_and_type(line):
    stop_idx = -1
    for org_type in ORG_TYPE:
        stop_idx = line.find(org_type)
        if stop_idx > -1:
            org_name = line[:stop_idx].strip()
            return org_name.title(), org_type.title()
    return None, None


def get_org(line):
    line = clean_org_line(line)
    org_name, org_type = get_org_name_and_type(line)
    if org_type and has_no_phone_or_email(org_name):
        return org_name, org_type
    return None, None


def get_new_district(line, current_district):
    if 'Council District' in line:
        return line[:2]
    return current_district


def skip_line(line):
    if line == '9/14/2016':
        return True
    elif line == 'THE MARYLAND_NATIONAL CAPITAL PARK AND PLANNING COMMISSION':
        return True
    elif line == "PRINCE GEORGE'S COUNTY PLANNING DEPARTMENT":
        return True
    elif line == 'REGISTERED ASSOCIATIONS (by Council District)':
        return True
    elif line == 'Address: Ext.Telephone:City:Planning':
        return True
    elif line == 'Area:':
        return True
    elif line == 'State: Email:Organization Name: Zip:Type: Date:':
        return True

def extract_contact_info(line):
    contact_dict = dict()
    contact_dict['phone_number'] = get_phone_number(line)
    contact_dict['zip_code'] = get_zip_code(line)
    contact_dict['email'] = get_email(line)
    contact_dict['date'] = get_date(line)
    contact_dict['title'], contact_dict['name'] = get_title_and_name(line)
    contact_dict['address'], contact_dict['city'] = get_address_and_city(line)
    return contact_dict


def extract_people_and_orgs(file_data):
    people, orgs = list(), list()
    org_buffer = ''
    current_district = ''
    current_org = ''
    for line in file_data:
        contact_dict = dict()
        line = line.strip()
        if not skip_line(line):
            current_district = get_new_district(line, current_district)
            contact_dict['district'] = current_district
            contact_dict['org'] = current_org
            contact_dict.update(extract_contact_info(line))
            # Deal with orgs
            if not contact_dict['title']:
                org_buffer += " " + line
            if 'Contact Information:' in line:
                current_org, org_type = get_org(org_buffer)
                contact_dict['org_type'] = org_type
                contact_dict.update(extract_contact_info(org_buffer))
                orgs.append(contact_dict)
                org_buffer = ''
            elif contact_dict['name']:
                people.append(contact_dict)
    return people, orgs


def export_data(file_name, data):
    with open(file_name, 'w') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=data[0].keys())
        writer.writeheader()
        for datum in data:
            writer.writerow(datum)


def run(file_path):
    with open(file_path) as file_data:
        people, orgs = extract_people_and_orgs(file_data)
    export_data('contacts_export.csv', people)
    export_data('orgs_export.csv', orgs)


if __name__ == '__main__':
    #doc_path = 'civics.pdf'
    #text_extractor(doc_path=doc_path, force_convert=False)
    run('civics.txt')

