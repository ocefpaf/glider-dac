#!/usr/bin/env python

import time
from threading import Timer, RLock
import os.path
import os
import argparse
import logging
import smtplib
from email.mime.text import MIMEText

from watchdog.events import FileSystemEventHandler, DirCreatedEvent
from watchdog.observers import Observer


logging.basicConfig(level=logging.INFO,
                    format='[%(asctime)s | %(levelname)s]  %(message)s')
logger = logging.getLogger(__name__)

EMAIL_TEXT = """
A new Glider Mission (%s) has been created. Please assign it a WMO ID and place it
in the directory inside of a file named "wmoid.txt".
"""
EMAIL_HOST     = os.environ.get('MAIL_SERVER')
EMAIL_PORT     = os.environ.get('MAIL_PORT')
EMAIL_USERNAME = os.environ.get('MAIL_USERNAME')
EMAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
EMAIL_FROM     = os.environ.get('MAIL_DEFAULT_SENDER')
EMAIL_TO       = [os.environ.get('MAIL_DEFAULT_TO')]
EMAIL_CC       = os.environ.get('MAIL_DEFAULT_LIST', None)

class HandleMission(FileSystemEventHandler):
    def __init__(self, base, timeout):
        self.waiting  = {}
        self.waitlock = RLock()

        self.base     = base
        self.timeout  = timeout

    def on_created(self, event):
        if isinstance(event, DirCreatedEvent):

            if self.base not in event.src_path:
                # wat?
                return

            rel_path = os.path.relpath(event.src_path, self.base)

            # we only care about this path if it's under a user dir
            # user/upload/mission-name
            path_parts = rel_path.split(os.sep)

            if len(path_parts) != 3:
                return

            logger.info("New mission directory: %s", rel_path)

            t = Timer(self.timeout, self.no_wmoid, args=[path_parts])
            t.start()
            try:
                self.waitlock.acquire()
                self.waiting[rel_path] = t
            finally:
                self.waitlock.release()
        else:
            rel_path = os.path.relpath(event.src_path, self.base)
            dirname = os.path.dirname(rel_path)

            # should resemble user/upload/mission-name/wmo-file
            path_parts = rel_path.split(os.sep)
            if len(path_parts) != 4:
                return

            # only looking for wmoid.txt named files
            if path_parts[-1] != "wmoid.txt":
                return

            try:
                self.waitlock.acquire()
                if dirname in self.waiting:
                    logger.info("wmoid.txt registered for %s, cancelling email", rel_path)
                    self.waiting[dirname].cancel()
                    del self.waiting[dirname]
            finally:
                self.waitlock.release()

    def no_wmoid(self, path_parts):
        logger.info("Send email for %s", path_parts)

        msg            = MIMEText(EMAIL_TEXT % path_parts[-1])
        msg['Subject'] = "New Glider Mission - %s" % path_parts[-1]
        msg['From']    = EMAIL_FROM
        msg['To']      = ",".join(EMAIL_TO)

        mail_recips = EMAIL_TO
        if EMAIL_CC is not None:
            mail_recips.append(EMAIL_CC)
            msg['CC'] = EMAIL_CC

        s = smtplib.SMTP(EMAIL_HOST, EMAIL_PORT)
        s.starttls()
        s.login(EMAIL_USERNAME, EMAIL_PASSWORD)
        try:
            s.sendmail(EMAIL_FROM, mail_recips, msg.as_string())
        finally:
            s.quit()

def main(handler):
    observer = Observer()
    observer.schedule(handler, path=handler.base, recursive=True)
    observer.start()

    logger.info("Watching user directories in %s", handler.base)

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()

    observer.join()

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--timeout',
                        action='store',
                        default=60,
                        type=int,
                        help="Timeout to wait before sending email (default: 60)")
    parser.add_argument('basedir',
                        default=os.environ.get('DATA_ROOT', '.'),
                        nargs='?')

    args = parser.parse_args()

    base = os.path.realpath(args.basedir)
    main(HandleMission(base, args.timeout))
