#!/usr/bin/env python
""" sync iOS style notes with Gmail """

import sys
import imaplib
import json
import email
import re


def usage(err=""):
    r = 0
    if err:
        r = 1
        print "Error: " + err
        print

    print """\
usage:
 notesync.py <credentials> [note1] ... [noteN]

about:
 sync iOS style notes with Gmail

options:
 credentials   json file with username and password
 note          list of note titles to sync
"""

    sys.exit(r)    


def mail_to_text(mail):
    text = ''.join([line.strip('=') for line in mail.split('\r\n')])

    # escape character: ^
    # secondary escape: ~
    text = text.replace('^', '^~')

    text = text.replace(' &nbsp;', '  ')
    text = text.replace('<br>', '^m^n')

    text_old = ''
    while text != text_old:
        text_old = text
        text = re.sub('<div>(.*?)</div>', '^m\\1', text)
        text = text.replace('^n^m', '^n')
        text = text.replace('^m^m', '^m')

    text = text.replace('^n', '\n')
    text = text.replace('^m', '\n')
    text = text.replace('^~', '^')

    return text

def text_to_mail(text):
    def mail_lines(text):
        start = 0
        while 0 <= start and start < len(text):
            end = start + 76
            if end > len(text):
                end = len(text)
            if text[end-1] == ' ':
                end += 1
            yield text[start:end] + '=\r\n'
            start = end

    text = text.replace('^', '^~')
    text = text.replace('  ', ' &nbsp;')
    text_old = ''
    while text != text_old:
        text_old = text
        text = text.replace('\n\n', '^n\n')
    text = text.replace('\n', '^m')
    text = text + '^o'

    text_old = ''
    while text != text_old:
        text_old = text
        text = re.sub('\^m(.*?)(\^[mno])', '<div>\\1</div>\\2', text)
    text = text.replace('^n', '<br>')
    text = text.replace('^o', '')

    text = text.replace('^~', '^')

    mail = ''
    for line in mail_lines(text):
        mail += line

    return mail


if __name__ == '__main__':
    if len(sys.argv) <= 1:
        usage()

    credentials_filename = sys.argv[1]
    notes = sys.argv[2:]

    with open(sys.argv[1]) as f:
        credentials = json.load(f)

    # http://yuji.wordpress.com/2011/06/22/python-imaplib-imap-example-with-gmail/
    mail = imaplib.IMAP4_SSL('imap.gmail.com')
    mail.login(credentials['username'], credentials['password'])
    
    if not '(\HasNoChildren) "/" "Notes"' in mail.list()[1]:
        print "Notes folder not found"
        sys.exit(1)

    mail.select('Notes')
    result, data = mail.uid('search', None, 'ALL') # search and return uids

    mail_uids = data[0].split()

    for mail_uid in mail_uids:
        result, data = mail.uid('fetch', mail_uid, '(RFC822)') # fetch the email body (RFC822) for the given ID
        mail_data = data[0][1]

        mail_message = email.message_from_string(mail_data)

        if mail_message['Subject'] in notes and \
                mail_message['X-Uniform-Type-Identifier'] == 'com.apple.mail-note':
            print mail_message['Subject']
            print mail_message['X-Universally-Unique-Identifier']
            print mail_message['X-Uniform-Type-Identifier']
            print mail_message['Message-Id']
            print mail_message['X-Mail-Created-Date']

            assert mail_message.get_content_maintype() == 'text', 'unhandled content maintype'

            mail_payload = mail_message.get_payload()

            print mail_payload
            print '===================='
            print mail_to_text(mail_payload)
            print '********************'
            print text_to_mail(mail_to_text(mail_payload))
            print '^^^^^^^^^^^^^^^^^^^^'
            print mail_to_text(text_to_mail(mail_to_text(mail_payload)))
            print '#####################'

    mail.close()
