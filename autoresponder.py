#!/usr/bin/python3
#	autoresponder - Dovecot/Sieve autoresponder script
#	Copyright (C) 2019-2019 Johannes Bauer
#
#	This file is part of autoresponder.
#
#	autoresponder is free software; you can redistribute it and/or modify
#	it under the terms of the GNU General Public License as published by
#	the Free Software Foundation; this program is ONLY licensed under
#	version 3 of the License, later versions are explicitly excluded.
#
#	autoresponder is distributed in the hope that it will be useful,
#	but WITHOUT ANY WARRANTY; without even the implied warranty of
#	MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#	GNU General Public License for more details.
#
#	You should have received a copy of the GNU General Public License
#	along with this program.  If not, see <https://www.gnu.org/licenses/>.
#
#	Johannes Bauer <JohannesBauer@gmx.de>

import sqlite3
import sys
import os
import contextlib
import time
import smtplib
import email.mime.text
import email.utils

config = {
	"db": os.path.realpath(os.getenv("HOME") + "/.mail/autoresponder.sqlite3"),
}

with contextlib.suppress(FileExistsError):
	os.makedirs(os.path.dirname(config["db"]))
db = sqlite3.connect(config["db"])
cursor = db.cursor()

with contextlib.suppress(sqlite3.OperationalError):
	cursor.execute("""CREATE TABLE mails (
		id integer PRIMARY KEY,
		identifier varchar NOT NULL UNIQUE,
		responder_mta varchar NOT NULL,
		responder_from varchar NOT NULL,
		subject varchar NOT NULL,
		text varchar NOT NULL,
		holdoff_secs integer DEFAULT 86400
	);""")
	db.commit()

with contextlib.suppress(sqlite3.IntegrityError):
	cursor.execute("""INSERT INTO mails (identifier, responder_mta, responder_from, subject, text, holdoff_secs) VALUES ('test', '127.0.0.1', 'bounce@invalid', 'Test Subject', 'Test Text', 10);""")
	db.commit()

with contextlib.suppress(sqlite3.OperationalError):
	cursor.execute("""CREATE TABLE holdoff (
		id integer PRIMARY KEY,
		identifier varchar NOT NULL,
		destination varchar NOT NULL,
		holdoff_until_time_t float NOT NULL,
		UNIQUE (identifier, destination)
	);""")
	db.commit()

with contextlib.suppress(sqlite3.OperationalError):
	cursor.execute("""CREATE TABLE log (
		id integer PRIMARY KEY,
		identifier varchar NOT NULL,
		destination varchar NOT NULL,
		timestamp_time_t float NOT NULL
	);""")
	db.commit()

identifier = sys.stdin.read()
identifier = identifier.rstrip("\r\n")

result = cursor.execute("SELECT responder_mta, responder_from, subject, text, holdoff_secs FROM mails WHERE identifier = ?;", (identifier, )).fetchone()
if result is None:
	print("Identifier '%s' was not found in mail database: %s" % (identifier, config["db"]), file = sys.stderr)
	sys.exit(1)
(responder_mta, responder_from, subject, text, holdoff_secs) = result

sender = os.getenv("SENDER")
if sender is None:
	print("SENDER environment variable not set", file = sys.stderr)
	sys.exit(1)


result = cursor.execute("SELECT holdoff_until_time_t FROM holdoff WHERE identifier = ? AND destination = ?;", (identifier, sender)).fetchone()
if result is None:
	holdoff_until = 0
else:
	holdoff_until = result[0]

now = time.time()
if holdoff_until >= now:
	# Holding off
	print("Holdoff in effect for %s for another %.0f seconds." % (sender, holdoff_until - now))
	sys.exit(0)

cursor.execute("INSERT INTO log (identifier, destination, timestamp_time_t) VALUES (?, ?, ?);", (identifier, sender, now))
try:
	cursor.execute("INSERT INTO holdoff (identifier, destination, holdoff_until_time_t) VALUES (?, ?, ?);", (identifier, sender, now + holdoff_secs))
except sqlite3.IntegrityError:
	cursor.execute("UPDATE holdoff SET holdoff_until_time_t = ? WHERE identifier = ? AND destination = ?;", (now + holdoff_secs, identifier, sender))
db.commit()


with smtplib.SMTP(responder_mta) as smtp:
	mail = email.mime.text.MIMEText(text)
	mail["Subject"] = subject
	mail["From"] = responder_from
	mail["To"] = sender
	mail["Date"] = email.utils.formatdate()
	message = mail.as_string()
	smtp.sendmail(responder_from, sender, message)

sys.exit(0)
